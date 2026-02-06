"""
Bounding Box Creator Tool - Creates bounding boxes from centroid and dimensions.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import zipfile

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
    QRadioButton, QCheckBox, QFileDialog, QMessageBox, QButtonGroup
)

import geopandas as gpd
from shapely.geometry import box
from pyproj import CRS

from swissarmyknifegis.tools.base_tool import BaseTool
from swissarmyknifegis.core.cities import get_major_cities, populate_city_combo
from swissarmyknifegis.core.coord_utils import (
    calculate_utm_epsg, validate_utm_epsg, wgs84_to_utm, utm_to_wgs84, transform_coordinates
)
from swissarmyknifegis.core.geo_export_utils import export_geodataframe_multi


class BoundingBoxCreatorTool(BaseTool):
    """
    Tool for creating bounding boxes based on centroid coordinates and dimensions.
    
    Features:
    - Input centroid in Lon/Lat (WGS84) or UTM coordinates
    - Specify width and height in meters or kilometers
    - Export to KML, Shapefile, and/or GeoJSON formats
    """
    
    def __init__(self, parent=None):
        # Debounce timer for preview updates (prevents excessive computation)
        # Must be created BEFORE super().__init__() since setup_ui() triggers preview
        self._preview_debounce_timer = QTimer()
        self._preview_debounce_timer.setSingleShot(True)
        self._preview_debounce_timer.setInterval(300)  # 300ms delay
        self._preview_debounce_timer.timeout.connect(self._do_update_preview)
        
        super().__init__(parent)
        
    def get_tool_name(self) -> str:
        """Return the display name for this tool."""
        return "BBox - Centroid"
        
    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)
        
        # Coordinate System Selection Group
        coord_sys_group = QGroupBox("Coordinate System")
        coord_sys_layout = QVBoxLayout(coord_sys_group)
        
        self.coord_sys_button_group = QButtonGroup(self)
        self.lonlat_radio = QRadioButton("Longitude/Latitude (WGS84)")
        self.utm_radio = QRadioButton("UTM Coordinates")
        self.lonlat_radio.setChecked(True)
        
        self.coord_sys_button_group.addButton(self.lonlat_radio)
        self.coord_sys_button_group.addButton(self.utm_radio)
        
        coord_sys_layout.addWidget(self.lonlat_radio)
        coord_sys_layout.addWidget(self.utm_radio)
        
        main_layout.addWidget(coord_sys_group)
        
        # Centroid Input Group
        centroid_group = QGroupBox("Centroid Coordinates")
        centroid_layout = QFormLayout(centroid_group)
        
        # City selector dropdown
        self.city_combo = QComboBox()
        self.city_combo.setMinimumWidth(300)
        self._populate_city_dropdown()
        self.city_combo.currentIndexChanged.connect(self._on_city_selected)
        centroid_layout.addRow("Quick Location:", self.city_combo)
        
        # Bounding box name input
        self.bbox_name_input = QLineEdit()
        self.bbox_name_input.setText("Bounding Box")
        self.bbox_name_input.setPlaceholderText("Enter bounding box name")
        self.bbox_name_input.setMinimumWidth(300)
        centroid_layout.addRow("Bounding Box Name:", self.bbox_name_input)
        
        # X coordinate (Longitude or UTM Easting)
        self.x_coord_input = QDoubleSpinBox()
        self.x_coord_input.setDecimals(6)
        self.x_coord_input.setRange(-180.0, 180.0)
        self.x_coord_input.setValue(0.0)
        self.x_coord_input.setMinimumWidth(200)
        self.x_label = QLabel("Longitude:")
        centroid_layout.addRow(self.x_label, self.x_coord_input)
        
        # Y coordinate (Latitude or UTM Northing)
        self.y_coord_input = QDoubleSpinBox()
        self.y_coord_input.setDecimals(6)
        self.y_coord_input.setRange(-90.0, 90.0)
        self.y_coord_input.setValue(0.0)
        self.y_coord_input.setMinimumWidth(200)
        self.y_label = QLabel("Latitude:")
        centroid_layout.addRow(self.y_label, self.y_coord_input)
        
        # UTM Zone (only for UTM input)
        self.utm_zone_input = QLineEdit()
        self.utm_zone_input.setPlaceholderText("e.g., 32633 for UTM Zone 33N")
        self.utm_zone_input.setValidator(QIntValidator(1000, 32799))  # Valid EPSG range
        self.utm_zone_input.setEnabled(False)
        self.utm_zone_input.setToolTip(
            "This control is only available in UTM coordinate mode.\n"
            "Switch to 'UTM Coordinates' above to enable it."
        )
        self.utm_zone_label = QLabel("EPSG Code:")
        centroid_layout.addRow(self.utm_zone_label, self.utm_zone_input)
        
        # UTM rounding option (only for UTM input)
        self.utm_rounding_combo = QComboBox()
        self.utm_rounding_combo.addItem("No rounding", None)
        self.utm_rounding_combo.addItem("Round to nearest 10 m", 10)
        self.utm_rounding_combo.addItem("Round to nearest 100 m", 100)
        self.utm_rounding_combo.addItem("Round to nearest 1,000 m", 1000)
        self.utm_rounding_combo.addItem("Round to nearest 10,000 m", 10000)
        self.utm_rounding_combo.setEnabled(False)
        self.utm_rounding_combo.setToolTip(
            "This control is only available in UTM coordinate mode.\n"
            "Switch to 'UTM Coordinates' above to enable it."
        )
        self.utm_rounding_combo.currentIndexChanged.connect(self._on_utm_rounding_changed)
        self.utm_rounding_label = QLabel("Round Centroid:")
        centroid_layout.addRow(self.utm_rounding_label, self.utm_rounding_combo)
        
        main_layout.addWidget(centroid_group)
        
        # Dimensions Group
        dimensions_group = QGroupBox("Bounding Box Dimensions")
        dimensions_layout = QFormLayout(dimensions_group)
        
        # Width input
        width_layout = QHBoxLayout()
        self.width_input = QDoubleSpinBox()
        self.width_input.setDecimals(3)
        self.width_input.setRange(0.001, 10000000.0)
        self.width_input.setValue(1000.0)
        self.width_input.setMinimumWidth(150)
        width_layout.addWidget(self.width_input)
        
        # Unit selector (shared for width and height)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["meters", "kilometers"])
        self.unit_combo.setMinimumWidth(100)
        width_layout.addWidget(self.unit_combo)
        
        dimensions_layout.addRow("Width:", width_layout)
        
        # Height input
        height_layout = QHBoxLayout()
        self.height_input = QDoubleSpinBox()
        self.height_input.setDecimals(3)
        self.height_input.setRange(0.001, 10000000.0)
        self.height_input.setValue(1000.0)
        self.height_input.setMinimumWidth(150)
        height_layout.addWidget(self.height_input)
        
        # Unit label (same as width)
        unit_label = QLabel("(same unit as width)")
        height_layout.addWidget(unit_label)
        
        dimensions_layout.addRow("Height:", height_layout)
        
        main_layout.addWidget(dimensions_group)
        
        # Bounding Box Preview Group
        self.preview_group = QGroupBox("Bounding Box Preview")
        preview_layout = QFormLayout(self.preview_group)
        
        # Create read-only line edits for extents with dynamic labels
        self.west_label = QLabel("West (Min X):")
        self.west_preview = QLineEdit()
        self.west_preview.setReadOnly(True)
        self.west_preview.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        preview_layout.addRow(self.west_label, self.west_preview)
        
        self.east_label = QLabel("East (Max X):")
        self.east_preview = QLineEdit()
        self.east_preview.setReadOnly(True)
        self.east_preview.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        preview_layout.addRow(self.east_label, self.east_preview)
        
        self.south_label = QLabel("South (Min Y):")
        self.south_preview = QLineEdit()
        self.south_preview.setReadOnly(True)
        self.south_preview.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        preview_layout.addRow(self.south_label, self.south_preview)
        
        self.north_label = QLabel("North (Max Y):")
        self.north_preview = QLineEdit()
        self.north_preview.setReadOnly(True)
        self.north_preview.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        preview_layout.addRow(self.north_label, self.north_preview)
        
        # Area and perimeter fields
        self.area_preview = QLineEdit()
        self.area_preview.setReadOnly(True)
        self.area_preview.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        preview_layout.addRow("Area (m²):", self.area_preview)
        
        self.perimeter_preview = QLineEdit()
        self.perimeter_preview.setReadOnly(True)
        self.perimeter_preview.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        preview_layout.addRow("Perimeter (m):", self.perimeter_preview)
        
        main_layout.addWidget(self.preview_group)
        
        # Output Settings Group
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout(output_group)
        
        # File path selection
        path_layout = QHBoxLayout()
        path_label = QLabel("Output Path Prefix:")
        output_layout.addWidget(path_label)
        
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("Select output path and filename prefix...")
        path_layout.addWidget(self.output_path_input)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_output)
        path_layout.addWidget(self.browse_button)
        
        output_layout.addLayout(path_layout)
        
        # Export format checkboxes
        format_label = QLabel("Export Formats:")
        output_layout.addWidget(format_label)
        
        # First row of format checkboxes
        format_layout = QHBoxLayout()
        self.kml_checkbox = QCheckBox("KML")
        self.kml_checkbox.setChecked(True)
        self.shapefile_checkbox = QCheckBox("Shapefile")
        self.shapefile_checkbox.setChecked(True)
        self.geojson_checkbox = QCheckBox("GeoJSON")
        self.geojson_checkbox.setChecked(True)
        self.txt_checkbox = QCheckBox("Text File")
        self.txt_checkbox.setChecked(True)
        
        format_layout.addWidget(self.kml_checkbox)
        format_layout.addWidget(self.shapefile_checkbox)
        format_layout.addWidget(self.geojson_checkbox)
        format_layout.addWidget(self.txt_checkbox)
        format_layout.addStretch()
        
        output_layout.addLayout(format_layout)
        
        # Second row of format checkboxes
        format_layout2 = QHBoxLayout()
        self.kmz_checkbox = QCheckBox("KMZ")
        self.kmz_checkbox.setChecked(False)
        self.geopackage_checkbox = QCheckBox("GeoPackage")
        self.geopackage_checkbox.setChecked(False)
        self.gml_checkbox = QCheckBox("GML")
        self.gml_checkbox.setChecked(False)
        self.tab_checkbox = QCheckBox("MapInfo TAB")
        self.tab_checkbox.setChecked(False)
        
        format_layout2.addWidget(self.kmz_checkbox)
        format_layout2.addWidget(self.geopackage_checkbox)
        format_layout2.addWidget(self.gml_checkbox)
        format_layout2.addWidget(self.tab_checkbox)
        format_layout2.addStretch()
        
        output_layout.addLayout(format_layout2)
        
        # UTM rectification option
        self.keep_utm_checkbox = QCheckBox("Keep UTM projection (where possible)")
        self.keep_utm_checkbox.setChecked(True)
        self.keep_utm_checkbox.setToolTip(
            "When checked, exports Shapefile, GeoJSON, GeoPackage, GML, and MapInfo TAB in UTM projection.\n"
            "KML and KMZ always use WGS84. When unchecked, all formats use WGS84."
        )
        output_layout.addWidget(self.keep_utm_checkbox)
        
        main_layout.addWidget(output_group)
        
        # Create Button
        self.create_button = QPushButton("Create Bounding Box")
        self.create_button.setMinimumHeight(40)
        self.create_button.clicked.connect(self._on_create_bbox)
        main_layout.addWidget(self.create_button)
        
        # Connect radio buttons to update labels and ranges
        self.lonlat_radio.toggled.connect(self._on_coord_system_changed)
        
        # Connect all inputs to update preview
        self.x_coord_input.valueChanged.connect(self._update_bbox_preview)
        self.y_coord_input.valueChanged.connect(self._update_bbox_preview)
        self.width_input.valueChanged.connect(self._update_bbox_preview)
        self.height_input.valueChanged.connect(self._update_bbox_preview)
        self.unit_combo.currentIndexChanged.connect(self._update_bbox_preview)
        self.utm_zone_input.textChanged.connect(self._update_bbox_preview)
        self.lonlat_radio.toggled.connect(self._update_bbox_preview)
        
        # Initial preview update
        self._update_bbox_preview()
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
    def _populate_city_dropdown(self):
        """Populate the city dropdown with major cities."""
        populate_city_combo(self.city_combo, "-- Manual Entry --")
    
    def _on_utm_rounding_changed(self, index: int):
        """Handle UTM rounding selection change."""
        rounding_value = self.utm_rounding_combo.currentData()
        
        if rounding_value is None or not self.utm_radio.isChecked():
            # No rounding or not in UTM mode
            return
        
        # Get current values
        current_x = self.x_coord_input.value()
        current_y = self.y_coord_input.value()
        
        # Round to nearest value
        rounded_x = round(current_x / rounding_value) * rounding_value
        rounded_y = round(current_y / rounding_value) * rounding_value
        
        # Set rounded values
        self.x_coord_input.setValue(rounded_x)
        self.y_coord_input.setValue(rounded_y)
        
    def _on_city_selected(self, index: int):
        """Handle city selection from dropdown."""
        coords = self.city_combo.currentData()
        
        if coords is None:
            # User selected a separator or "Manual Entry"
            if self.city_combo.currentText() == "-- Manual Entry --":
                self.bbox_name_input.setText("Bounding Box")
            return
        
        # Update bounding box name to city name
        city_name = self.city_combo.currentText()
        self.bbox_name_input.setText(city_name)
        
        lon, lat = coords
        
        # Update coordinates based on current mode
        if self.lonlat_radio.isChecked():
            # Lon/Lat mode - set values directly
            self.x_coord_input.setValue(lon)
            self.y_coord_input.setValue(lat)
        else:
            # UTM mode - convert from lon/lat to UTM
            # Check if EPSG code is valid
            if not self.utm_zone_input.text().strip():
                # No EPSG code, calculate it from the city coordinates
                utm_epsg = calculate_utm_epsg(lon, lat)
                self.utm_zone_input.setText(str(utm_epsg))
            else:
                # Use existing EPSG code
                try:
                    utm_epsg = int(self.utm_zone_input.text())
                except ValueError:
                    # Invalid EPSG, calculate from coordinates
                    utm_epsg = calculate_utm_epsg(lon, lat)
                    self.utm_zone_input.setText(str(utm_epsg))
            
            # Transform from WGS84 to UTM
            utm_x, utm_y = transform_coordinates(lon, lat, "EPSG:4326", f"EPSG:{utm_epsg}")
            
            # Set the UTM coordinates
            self.x_coord_input.setValue(utm_x)
            self.y_coord_input.setValue(utm_y)
    
    def _update_bbox_preview(self):
        """Schedule a debounced preview update to avoid excessive computations."""
        # Restart the timer - this debounces rapid changes (e.g., typing EPSG codes)
        self._preview_debounce_timer.stop()
        self._preview_debounce_timer.start()
    
    def _do_update_preview(self):
        """Actually update the bounding box extent preview (called after debounce delay)."""
        try:
            # Get dimensions in meters
            width_m = self._get_dimension_in_meters(self.width_input.value())
            height_m = self._get_dimension_in_meters(self.height_input.value())
            
            # Check which coordinate system mode we're in
            if self.lonlat_radio.isChecked():
                # Lon/Lat mode - show WGS84 extents
                self.preview_group.setTitle("Bounding Box Preview (WGS84)")
                self.west_label.setText("West (Min Lon):")
                self.east_label.setText("East (Max Lon):")
                self.south_label.setText("South (Min Lat):")
                self.north_label.setText("North (Max Lat):")
                
                # Get UTM coordinates for calculation
                utm_x, utm_y, utm_epsg = self._get_utm_coordinates()
                
                # Calculate UTM bounding box extents
                minx_utm = utm_x - width_m / 2.0
                maxx_utm = utm_x + width_m / 2.0
                miny_utm = utm_y - height_m / 2.0
                maxy_utm = utm_y + height_m / 2.0
                
                # Transform corners to WGS84
                # Transform all four corners
                sw_lon, sw_lat = transform_coordinates(minx_utm, miny_utm, f"EPSG:{utm_epsg}", "EPSG:4326")
                se_lon, se_lat = transform_coordinates(maxx_utm, miny_utm, f"EPSG:{utm_epsg}", "EPSG:4326")
                nw_lon, nw_lat = transform_coordinates(minx_utm, maxy_utm, f"EPSG:{utm_epsg}", "EPSG:4326")
                ne_lon, ne_lat = transform_coordinates(maxx_utm, maxy_utm, f"EPSG:{utm_epsg}", "EPSG:4326")
                
                # Get min/max from corners (in case of distortion)
                west = min(sw_lon, se_lon, nw_lon, ne_lon)
                east = max(sw_lon, se_lon, nw_lon, ne_lon)
                south = min(sw_lat, se_lat, nw_lat, ne_lat)
                north = max(sw_lat, se_lat, nw_lat, ne_lat)
                
                # Update preview fields with degrees
                self.west_preview.setText(f"{west:.6f}°")
                self.east_preview.setText(f"{east:.6f}°")
                self.south_preview.setText(f"{south:.6f}°")
                self.north_preview.setText(f"{north:.6f}°")
                
                # Calculate and display area and perimeter
                area = width_m * height_m
                perimeter = 2 * (width_m + height_m)
                self.area_preview.setText(f"{area:.2f} m² ({area/1e6:.4f} km²)")
                self.perimeter_preview.setText(f"{perimeter:.2f} m ({perimeter/1e3:.4f} km)")
                
            else:
                # UTM mode - show UTM extents
                # Validate EPSG code first
                if not self.utm_zone_input.text().strip():
                    self._clear_preview()
                    return
                try:
                    epsg_code = int(self.utm_zone_input.text())
                    is_valid, _ = validate_utm_epsg(epsg_code)
                    if not is_valid:
                        self._clear_preview()
                        return
                except ValueError:
                    self._clear_preview()
                    return
                
                self.preview_group.setTitle(f"Bounding Box Preview (UTM EPSG:{epsg_code})")
                self.west_label.setText("West (Min Easting):")
                self.east_label.setText("East (Max Easting):")
                self.south_label.setText("South (Min Northing):")
                self.north_label.setText("North (Max Northing):")
                
                # Get UTM coordinates
                utm_x, utm_y, utm_epsg = self._get_utm_coordinates()
                
                # Calculate UTM bounding box extents
                minx_utm = utm_x - width_m / 2.0
                maxx_utm = utm_x + width_m / 2.0
                miny_utm = utm_y - height_m / 2.0
                maxy_utm = utm_y + height_m / 2.0
                
                # Update preview fields with meters
                self.west_preview.setText(f"{minx_utm:.2f} m")
                self.east_preview.setText(f"{maxx_utm:.2f} m")
                self.south_preview.setText(f"{miny_utm:.2f} m")
                self.north_preview.setText(f"{maxy_utm:.2f} m")
                
                # Calculate and display area and perimeter
                area = width_m * height_m
                perimeter = 2 * (width_m + height_m)
                self.area_preview.setText(f"{area:.2f} m² ({area/1e6:.4f} km²)")
                self.perimeter_preview.setText(f"{perimeter:.2f} m ({perimeter/1e3:.4f} km)")
            
        except Exception as e:
            # If calculation fails, clear preview and log error
            self._clear_preview()
            # Log error for debugging without interrupting user experience
            logging.debug(f"Preview calculation error: {e}")
    
    def _clear_preview(self):
        """Clear the bounding box preview fields."""
        self.west_preview.setText("--")
        self.east_preview.setText("--")
        self.south_preview.setText("--")
        self.north_preview.setText("--")
    
    def _on_coord_system_changed(self, checked: bool):
        """Handle coordinate system radio button changes."""
        if self.lonlat_radio.isChecked():
            # Switching to Lon/Lat mode - try to convert from UTM
            # Get current UTM values
            current_x = self.x_coord_input.value()
            current_y = self.y_coord_input.value()
            
            # Update UI
            self.x_label.setText("Longitude:")
            self.y_label.setText("Latitude:")
            self.x_coord_input.setRange(-180.0, 180.0)
            self.y_coord_input.setRange(-90.0, 90.0)
            self.utm_zone_input.setEnabled(False)
            self.utm_zone_label.setEnabled(False)
            self.utm_rounding_combo.setEnabled(False)
            self.utm_rounding_label.setEnabled(False)
            
            # Try to convert UTM to Lon/Lat
            if self.utm_zone_input.text().strip():
                try:
                    utm_epsg = int(self.utm_zone_input.text())
                    is_valid, _ = validate_utm_epsg(utm_epsg)
                    if is_valid:
                        # Valid UTM EPSG code, convert coordinates
                        lon, lat = utm_to_wgs84(current_x, current_y, utm_epsg)
                        self.x_coord_input.setValue(lon)
                        self.y_coord_input.setValue(lat)
                        return
                except (ValueError, Exception):
                    pass
            
            # If conversion failed, set defaults
            self.x_coord_input.setValue(0.0)
            self.y_coord_input.setValue(0.0)
            
        else:
            # Switching to UTM mode - convert from Lon/Lat
            # Get current Lon/Lat values
            current_lon = self.x_coord_input.value()
            current_lat = self.y_coord_input.value()
            
            # Update UI
            self.x_label.setText("Easting (m):")
            self.y_label.setText("Northing (m):")
            self.x_coord_input.setRange(0.0, 1000000.0)
            self.y_coord_input.setRange(0.0, 10000000.0)
            self.utm_zone_input.setEnabled(True)
            self.utm_zone_label.setEnabled(True)
            self.utm_rounding_combo.setEnabled(True)
            self.utm_rounding_label.setEnabled(True)
            
            # Convert Lon/Lat to UTM
            try:
                # Calculate UTM EPSG from coordinates
                utm_epsg = calculate_utm_epsg(current_lon, current_lat)
                
                # Set EPSG code
                self.utm_zone_input.setText(str(utm_epsg))
                
                # Transform coordinates
                utm_x, utm_y = transform_coordinates(
                    current_lon, current_lat, "EPSG:4326", f"EPSG:{utm_epsg}"
                )
                
                self.x_coord_input.setValue(utm_x)
                self.y_coord_input.setValue(utm_y)
                
            except Exception:
                # If conversion failed, set defaults
                self.x_coord_input.setValue(500000.0)
                self.y_coord_input.setValue(5000000.0)
            
    def _on_browse_output(self):
        """Handle Browse button click for output path selection."""
        last_path = self._get_last_path("paths/bbox_creator/output_file")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output Path and Filename Prefix",
            last_path,
            "All Files (*)"
        )
        
        if file_path:
            # Save the directory for next time
            self._save_last_path("paths/bbox_creator/output_file", file_path)
            # Remove any extension if provided
            file_path = Path(file_path).with_suffix('')
            self.output_path_input.setText(str(file_path))
            
    def _on_create_bbox(self):
        """Handle Create Bounding Box button click."""
        try:
            # Validate inputs
            if not self.validate_inputs():
                return
                
            # Get coordinates and convert to UTM if needed
            utm_x, utm_y, utm_epsg = self._get_utm_coordinates()
            
            # Get dimensions in meters
            width_m = self._get_dimension_in_meters(self.width_input.value())
            height_m = self._get_dimension_in_meters(self.height_input.value())
            
            # Calculate bounding box extents
            minx = utm_x - width_m / 2.0
            maxx = utm_x + width_m / 2.0
            miny = utm_y - height_m / 2.0
            maxy = utm_y + height_m / 2.0
            
            # Create bounding box geometry
            bbox_geom = box(minx, miny, maxx, maxy)
            
            # Get bounding box name from input
            bbox_name = self.bbox_name_input.text().strip() or "Bounding Box"
            
            # Create GeoDataFrame with UTM CRS
            gdf = gpd.GeoDataFrame(
                {'name': [bbox_name], 'geometry': [bbox_geom]},
                crs=f"EPSG:{utm_epsg}"
            )
            
            # Determine if we should convert to WGS84 for non-KML formats
            use_wgs84 = not self.keep_utm_checkbox.isChecked()
            
            # Convert to WGS84 if requested
            if use_wgs84:
                gdf_export = gdf.to_crs("EPSG:4326")
                crs_info = "WGS84"
            else:
                gdf_export = gdf
                crs_info = f"UTM EPSG:{utm_epsg}"
            
            # Export to selected formats
            output_prefix = Path(self.output_path_input.text())
            
            # Build format dictionary for export utility
            export_formats = {
                'shp': self.shapefile_checkbox.isChecked(),
                'geojson': self.geojson_checkbox.isChecked(),
                'kml': self.kml_checkbox.isChecked(),
                'kmz': self.kmz_checkbox.isChecked(),
                'gpkg': self.geopackage_checkbox.isChecked(),
                'gml': self.gml_checkbox.isChecked(),
                'tab': self.tab_checkbox.isChecked()
            }
            
            # Export to GIS formats using utility
            exported_files = export_geodataframe_multi(
                gdf, output_prefix, export_formats,
                layer_name=bbox_name,
                keep_utm=self.keep_utm_checkbox.isChecked()
            )
            
            # Text file export (not handled by geo_export_utils)
            if self.txt_checkbox.isChecked():
                # Export comprehensive text file with all parameters
                txt_path = output_prefix.with_suffix('.txt')
                
                # Get original input coordinates
                input_x = self.x_coord_input.value()
                input_y = self.y_coord_input.value()
                
                # Convert WGS84 back from UTM if needed for display
                if self.lonlat_radio.isChecked():
                    wgs84_lon, wgs84_lat = input_x, input_y
                else:
                    # Convert UTM to WGS84
                    wgs84_lon, wgs84_lat = utm_to_wgs84(input_x, input_y, utm_epsg)
                
                # Get WGS84 bbox extents if converted
                gdf_wgs84_bounds = gdf.to_crs("EPSG:4326")
                wgs84_bounds = gdf_wgs84_bounds.total_bounds
                
                # Get dimension values
                width_val = self.width_input.value()
                height_val = self.height_input.value()
                unit_text = self.unit_combo.currentText()
                
                # Calculate area and perimeter
                area_sqm = width_m * height_m
                perimeter_m = 2 * (width_m + height_m)
                
                # Get configuration details
                location = self.city_combo.currentText() if self.city_combo.currentIndex() > 0 else "Manual Entry"
                rounding = self.utm_rounding_combo.currentData()
                rounding_text = "None" if rounding is None else f"{rounding} meters"
                
                # Build text content
                txt_content = []
                txt_content.append("========================================")
                txt_content.append("   BOUNDING BOX PARAMETERS")
                txt_content.append("========================================")
                txt_content.append("")
                
                # Centroid section
                txt_content.append("--- CENTROID COORDINATES ---")
                txt_content.append("")
                txt_content.append("WGS84 (EPSG:4326):")
                txt_content.append(f"  Longitude: {wgs84_lon:.6f}°")
                txt_content.append(f"  Latitude:  {wgs84_lat:.6f}°")
                txt_content.append("")
                txt_content.append(f"UTM (EPSG:{utm_epsg}):")
                txt_content.append(f"  Easting:  {utm_x:.2f} m")
                txt_content.append(f"  Northing: {utm_y:.2f} m")
                txt_content.append("")
                
                # Bounding box extents section
                txt_content.append("--- BOUNDING BOX EXTENTS ---")
                txt_content.append("")
                txt_content.append(f"UTM (EPSG:{utm_epsg}):")
                txt_content.append(f"  Min X (West):  {minx:.2f} m")
                txt_content.append(f"  Max X (East):  {maxx:.2f} m")
                txt_content.append(f"  Min Y (South): {miny:.2f} m")
                txt_content.append(f"  Max Y (North): {maxy:.2f} m")
                txt_content.append("")
                txt_content.append("WGS84 (EPSG:4326):")
                txt_content.append(f"  Min Lon (West):  {wgs84_bounds[0]:.6f}°")
                txt_content.append(f"  Max Lon (East):  {wgs84_bounds[2]:.6f}°")
                txt_content.append(f"  Min Lat (South): {wgs84_bounds[1]:.6f}°")
                txt_content.append(f"  Max Lat (North): {wgs84_bounds[3]:.6f}°")
                txt_content.append("")
                
                # Dimensions section
                txt_content.append("--- DIMENSIONS ---")
                txt_content.append("")
                txt_content.append(f"Width:  {width_val:.2f} {unit_text} ({width_m:.2f} m)")
                txt_content.append(f"Height: {height_val:.2f} {unit_text} ({height_m:.2f} m)")
                txt_content.append(f"Area:   {area_sqm:.2f} m² ({area_sqm/1e6:.4f} km²)")
                txt_content.append(f"Perimeter: {perimeter_m:.2f} m ({perimeter_m/1e3:.4f} km)")
                txt_content.append("")
                
                # CRS information section
                txt_content.append("--- COORDINATE REFERENCE SYSTEM ---")
                txt_content.append("")
                txt_content.append(f"Input CRS:  {'WGS84 (EPSG:4326)' if self.lonlat_radio.isChecked() else f'UTM (EPSG:{utm_epsg})'}")
                txt_content.append(f"Output CRS: {crs_info}")
                txt_content.append(f"UTM Zone:   EPSG:{utm_epsg}")
                txt_content.append("")
                
                # Configuration section
                txt_content.append("--- CONFIGURATION ---")
                txt_content.append("")
                txt_content.append(f"Location/City:       {location}")
                txt_content.append(f"UTM Rounding:        {rounding_text}")
                txt_content.append(f"Keep UTM Projection: {'Yes' if self.keep_utm_checkbox.isChecked() else 'No'}")
                txt_content.append("")
                txt_content.append("========================================")
                
                # Write to file
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(txt_content))
                
                exported_files.append(str(txt_path))
                
            # Show success message
            files_list = "\n".join(exported_files)
            QMessageBox.information(
                self,
                "Success",
                f"Bounding box created successfully!\n\n"
                f"Coordinate System: {crs_info}\n\n"
                f"Exported files:\n{files_list}"
            )
            
            # Update status bar
            self._update_status(f"Created bounding box: {len(exported_files)} file(s) exported")
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create bounding box:\n{str(e)}"
            )
            
    def _get_utm_coordinates(self) -> Tuple[float, float, int]:
        """
        Get UTM coordinates from input, converting if necessary.
        
        Returns:
            Tuple of (utm_x, utm_y, epsg_code)
        """
        if self.lonlat_radio.isChecked():
            # Convert lon/lat to UTM
            lon = self.x_coord_input.value()
            lat = self.y_coord_input.value()
            
            # Calculate UTM EPSG and transform coordinates
            utm_x, utm_y, utm_epsg = wgs84_to_utm(lon, lat)
            
            return utm_x, utm_y, utm_epsg
            
        else:
            # Already in UTM
            utm_x = self.x_coord_input.value()
            utm_y = self.y_coord_input.value()
            utm_epsg = int(self.utm_zone_input.text())
            
            return utm_x, utm_y, utm_epsg
            
    def _get_dimension_in_meters(self, value: float) -> float:
        """Convert dimension value to meters based on selected unit."""
        if self.unit_combo.currentText() == "kilometers":
            return value * 1000.0
        return value
        
    def validate_inputs(self) -> bool:
        """Validate user inputs before creating bounding box."""
        # Check if at least one export format is selected
        if not (self.kml_checkbox.isChecked() or 
                self.shapefile_checkbox.isChecked() or 
                self.geojson_checkbox.isChecked() or
                self.txt_checkbox.isChecked() or
                self.kmz_checkbox.isChecked() or
                self.geopackage_checkbox.isChecked() or
                self.gml_checkbox.isChecked() or
                self.tab_checkbox.isChecked()):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select at least one export format."
            )
            return False
            
        # Check if output path is specified
        if not self.output_path_input.text().strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please specify an output path prefix."
            )
            return False
            
        # Validate UTM EPSG code if in UTM mode
        if self.utm_radio.isChecked():
            try:
                epsg_code = int(self.utm_zone_input.text())
                is_valid, error_msg = validate_utm_epsg(epsg_code)
                if not is_valid:
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        error_msg
                    )
                    return False
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please enter a valid EPSG code (numeric value)."
                )
                return False
                
        # Check dimensions are positive
        if self.width_input.value() <= 0 or self.height_input.value() <= 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Width and height must be greater than zero."
            )
            return False
            
        return True
        
    def reset(self):
        """Reset the tool to its initial state."""
        self.city_combo.setCurrentIndex(0)  # Reset to "Manual Entry"
        self.bbox_name_input.setText("Bounding Box")
        self.lonlat_radio.setChecked(True)
        self.x_coord_input.setValue(0.0)
        self.y_coord_input.setValue(0.0)
        self.width_input.setValue(1000.0)
        self.height_input.setValue(1000.0)
        self.unit_combo.setCurrentIndex(0)
        self.output_path_input.clear()
        self.utm_zone_input.clear()
        self.kml_checkbox.setChecked(True)
        self.shapefile_checkbox.setChecked(True)
        self.geojson_checkbox.setChecked(True)
        self.txt_checkbox.setChecked(True)
        self.kmz_checkbox.setChecked(False)
        self.geopackage_checkbox.setChecked(False)
        self.gml_checkbox.setChecked(False)
        self.tab_checkbox.setChecked(False)
        self.keep_utm_checkbox.setChecked(True)
