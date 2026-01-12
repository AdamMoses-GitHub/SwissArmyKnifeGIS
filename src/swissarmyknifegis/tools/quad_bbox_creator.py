"""
4-Point Bounding Box Creator Tool
Creates a bounding box by specifying four arbitrary corner points.
"""

from pathlib import Path
from typing import Optional, Tuple
import zipfile
import json
import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QRadioButton, 
    QCheckBox, QFileDialog, QMessageBox, QButtonGroup,
    QTextEdit, QComboBox
)
from PySide6.QtGui import QIntValidator

import geopandas as gpd
from shapely.geometry import Polygon, mapping
from pyproj import CRS
from osgeo import gdal

from swissarmyknifegis.tools.base_tool import BaseTool
from swissarmyknifegis.core.cities import get_major_cities, populate_city_combo
from swissarmyknifegis.core.coord_utils import (
    calculate_utm_epsg, validate_utm_epsg, wgs84_to_utm, utm_to_wgs84, transform_coordinates
)
from swissarmyknifegis.core.geo_export_utils import export_geodataframe_multi


class QuadBBoxCreatorTool(BaseTool):
    """Tool for creating bounding boxes from four arbitrary corner points."""
    
    # Default offset for city-based bounding boxes (approximately 0.1 degrees = ~11 km)
    DEFAULT_CITY_BBOX_OFFSET_DEGREES = 0.1
    
    def __init__(self, parent=None):
        self.cities = get_major_cities()
        
        # Debounce timer for preview updates (prevents excessive computation)
        # Must be created BEFORE super().__init__() since setup_ui() triggers preview
        self._preview_debounce_timer = QTimer()
        self._preview_debounce_timer.setSingleShot(True)
        self._preview_debounce_timer.setInterval(300)  # 300ms delay
        self._preview_debounce_timer.timeout.connect(self._do_update_preview)
        
        super().__init__(parent)
        
    def get_tool_name(self) -> str:
        return "BBox - Points"
    
    def setup_ui(self):
        """Set up the user interface for the 4-point bounding box creator."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Coordinate System Selection
        coord_system_group = QGroupBox("Coordinate System")
        coord_system_layout = QVBoxLayout()
        
        self.coord_system_group = QButtonGroup(self)
        self.lonlat_radio = QRadioButton("Lon/Lat (WGS84)")
        self.utm_radio = QRadioButton("UTM Coordinates")
        self.lonlat_radio.setChecked(True)
        
        self.coord_system_group.addButton(self.lonlat_radio)
        self.coord_system_group.addButton(self.utm_radio)
        
        coord_system_layout.addWidget(self.lonlat_radio)
        coord_system_layout.addWidget(self.utm_radio)
        coord_system_group.setLayout(coord_system_layout)
        main_layout.addWidget(coord_system_group)
        
        # UTM Zone input (shown when UTM is selected)
        self.utm_zone_group = QGroupBox("UTM Zone")
        utm_zone_layout = QFormLayout()
        
        self.utm_epsg_input = QLineEdit()
        self.utm_epsg_input.setPlaceholderText("e.g., 32632 for UTM Zone 32N")
        self.utm_epsg_input.setValidator(QIntValidator(32601, 32760))
        utm_zone_layout.addRow("EPSG Code:", self.utm_epsg_input)
        
        # UTM rounding option (only for UTM input)
        self.utm_rounding_combo = QComboBox()
        self.utm_rounding_combo.addItem("No rounding", None)
        self.utm_rounding_combo.addItem("Round to nearest 10 m", 10)
        self.utm_rounding_combo.addItem("Round to nearest 100 m", 100)
        self.utm_rounding_combo.addItem("Round to nearest 1,000 m", 1000)
        self.utm_rounding_combo.addItem("Round to nearest 10,000 m", 10000)
        self.utm_rounding_combo.setEnabled(False)
        self.utm_rounding_combo.currentIndexChanged.connect(self._on_utm_rounding_changed)
        self.utm_rounding_label = QLabel("Round Boundaries:")
        utm_zone_layout.addRow(self.utm_rounding_label, self.utm_rounding_combo)
        
        self.utm_zone_group.setLayout(utm_zone_layout)
        self.utm_zone_group.setVisible(False)
        main_layout.addWidget(self.utm_zone_group)
        
        # Quick location selector
        location_group = QGroupBox("Quick Location (Optional)")
        location_layout = QFormLayout()
        
        self.location_combo = QComboBox()
        populate_city_combo(self.location_combo, "-- Select City --")
        
        location_layout.addRow("Location:", self.location_combo)
        
        # Bbox name input
        self.bbox_name_input = QLineEdit()
        self.bbox_name_input.setText("BBox")
        self.bbox_name_input.setPlaceholderText("Enter bounding box name")
        location_layout.addRow("Bounding Box Name:", self.bbox_name_input)
        
        location_group.setLayout(location_layout)
        main_layout.addWidget(location_group)
        
        # Boundary Inputs
        bounds_group = QGroupBox("Bounding Box Boundaries")
        bounds_layout = QFormLayout()
        
        self.north_input = QLineEdit()
        self.north_input.setPlaceholderText("Maximum latitude / Y coordinate")
        bounds_layout.addRow("North:", self.north_input)
        
        self.south_input = QLineEdit()
        self.south_input.setPlaceholderText("Minimum latitude / Y coordinate")
        bounds_layout.addRow("South:", self.south_input)
        
        self.east_input = QLineEdit()
        self.east_input.setPlaceholderText("Maximum longitude / X coordinate")
        bounds_layout.addRow("East:", self.east_input)
        
        self.west_input = QLineEdit()
        self.west_input.setPlaceholderText("Minimum longitude / X coordinate")
        bounds_layout.addRow("West:", self.west_input)
        
        bounds_group.setLayout(bounds_layout)
        main_layout.addWidget(bounds_group)
        
        # Preview Section
        preview_group = QGroupBox("Preview")
        preview_layout = QFormLayout()
        
        self.preview_centroid_x = QLineEdit()
        self.preview_centroid_x.setReadOnly(True)
        self.preview_centroid_x.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        self.preview_centroid_y = QLineEdit()
        self.preview_centroid_y.setReadOnly(True)
        self.preview_centroid_y.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        self.preview_width = QLineEdit()
        self.preview_width.setReadOnly(True)
        self.preview_width.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        self.preview_height = QLineEdit()
        self.preview_height.setReadOnly(True)
        self.preview_height.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        self.preview_area = QLineEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        self.preview_perimeter = QLineEdit()
        self.preview_perimeter.setReadOnly(True)
        self.preview_perimeter.setStyleSheet("QLineEdit { background-color: #f0f0f0; }")
        
        preview_layout.addRow("Centroid X (m):", self.preview_centroid_x)
        preview_layout.addRow("Centroid Y (m):", self.preview_centroid_y)
        preview_layout.addRow("Width (m):", self.preview_width)
        preview_layout.addRow("Height (m):", self.preview_height)
        preview_layout.addRow("Area (m²):", self.preview_area)
        preview_layout.addRow("Perimeter (m):", self.preview_perimeter)
        
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)
        
        # Output Settings
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()
        
        # Output path
        path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Output path prefix (without extension)")
        last_path = self._get_last_path("paths/bbox_creator/output_file")
        if last_path:
            self.output_path.setText(str(last_path))
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output)
        
        path_layout.addWidget(self.output_path)
        path_layout.addWidget(browse_button)
        output_layout.addLayout(path_layout)
        
        # Export format checkboxes
        formats_label = QLabel("Export Formats:")
        output_layout.addWidget(formats_label)
        
        format_layout = QHBoxLayout()
        self.format_kml = QCheckBox("KML")
        self.format_shp = QCheckBox("Shapefile")
        self.format_geojson = QCheckBox("GeoJSON")
        self.format_txt = QCheckBox("Text File")
        
        self.format_kml.setChecked(True)
        self.format_shp.setChecked(True)
        self.format_geojson.setChecked(True)
        self.format_txt.setChecked(True)
        
        format_layout.addWidget(self.format_kml)
        format_layout.addWidget(self.format_shp)
        format_layout.addWidget(self.format_geojson)
        format_layout.addWidget(self.format_txt)
        output_layout.addLayout(format_layout)
        
        format_layout2 = QHBoxLayout()
        self.format_kmz = QCheckBox("KMZ")
        self.format_gpkg = QCheckBox("GeoPackage")
        self.format_gml = QCheckBox("GML")
        self.format_tab = QCheckBox("MapInfo TAB")
        
        format_layout2.addWidget(self.format_kmz)
        format_layout2.addWidget(self.format_gpkg)
        format_layout2.addWidget(self.format_gml)
        format_layout2.addWidget(self.format_tab)
        output_layout.addLayout(format_layout2)
        
        # Keep UTM projection option
        self.keep_utm = QCheckBox("Keep UTM projection (where possible)")
        self.keep_utm.setChecked(True)
        self.keep_utm.setToolTip(
            "When checked, exports Shapefile, GeoJSON, GeoPackage, GML, and MapInfo TAB in UTM projection.\n"
            "KML and KMZ always use WGS84. When unchecked, all formats use WGS84."
        )
        output_layout.addWidget(self.keep_utm)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # Create Bounding Box Button
        self.create_button = QPushButton("Create Bounding Box")
        self.create_button.setMinimumHeight(40)
        self.create_button.clicked.connect(self._create_bbox)
        main_layout.addWidget(self.create_button)
        
        # Stretch to push everything to the top
        main_layout.addStretch()
        
        # Connect signals
        self.lonlat_radio.toggled.connect(self._on_coord_system_changed)
        self.utm_radio.toggled.connect(self._on_coord_system_changed)
        self.location_combo.currentIndexChanged.connect(self._on_location_selected)
        
        # Connect all boundary inputs to update preview
        self.north_input.textChanged.connect(self._update_preview)
        self.south_input.textChanged.connect(self._update_preview)
        self.east_input.textChanged.connect(self._update_preview)
        self.west_input.textChanged.connect(self._update_preview)
        
        self.utm_epsg_input.textChanged.connect(self._update_preview)
        
    def _on_coord_system_changed(self):
        """Handle coordinate system radio button changes and convert existing coordinates."""
        self.utm_zone_group.setVisible(self.utm_radio.isChecked())
        
        # Try to convert existing boundary values when switching modes
        boundaries = self._parse_boundaries()
        if boundaries:
            north, south, east, west = boundaries
            
            if self.utm_radio.isChecked():
                # Switching to UTM mode - convert from Lon/Lat
                try:
                    # Determine UTM zone from center of bbox
                    center_lon = (east + west) / 2
                    center_lat = (north + south) / 2
                    utm_epsg_code = calculate_utm_epsg(center_lon, center_lat)
                    
                    epsg_code = f"EPSG:{utm_epsg_code}"
                    self.utm_epsg_input.setText(str(utm_epsg_code))
                    
                    # Transform corners to UTM
                    nw_x, nw_y = transform_coordinates(west, north, "EPSG:4326", epsg_code)
                    ne_x, ne_y = transform_coordinates(east, north, "EPSG:4326", epsg_code)
                    se_x, se_y = transform_coordinates(east, south, "EPSG:4326", epsg_code)
                    sw_x, sw_y = transform_coordinates(west, south, "EPSG:4326", epsg_code)
                    
                    # Display boundaries in UTM
                    self.north_input.setText(f"{max(nw_y, ne_y):.2f}")
                    self.south_input.setText(f"{min(se_y, sw_y):.2f}")
                    self.east_input.setText(f"{max(ne_x, se_x):.2f}")
                    self.west_input.setText(f"{min(nw_x, sw_x):.2f}")
                except Exception as e:
                    # If conversion fails, skip it but still update preview
                    logging.debug(f"Coordinate conversion failed when switching to UTM mode: {e}")
                    pass
            else:
                # Switching to Lon/Lat mode - convert from UTM
                epsg_text = self.utm_epsg_input.text().strip()
                if epsg_text:
                    try:
                        epsg_code = f"EPSG:{epsg_text}"
                        
                        # Transform corners from UTM to Lon/Lat
                        nw_lon, nw_lat = transform_coordinates(west, north, epsg_code, "EPSG:4326")
                        ne_lon, ne_lat = transform_coordinates(east, north, epsg_code, "EPSG:4326")
                        se_lon, se_lat = transform_coordinates(east, south, epsg_code, "EPSG:4326")
                        sw_lon, sw_lat = transform_coordinates(west, south, epsg_code, "EPSG:4326")
                        
                        # Display boundaries in Lon/Lat
                        self.north_input.setText(f"{max(nw_lat, ne_lat):.6f}")
                        self.south_input.setText(f"{min(se_lat, sw_lat):.6f}")
                        self.east_input.setText(f"{max(ne_lon, se_lon):.6f}")
                        self.west_input.setText(f"{min(nw_lon, sw_lon):.6f}")
                    except Exception as e:
                        # If conversion fails, clear EPSG and don't convert coordinates
                        logging.debug(f"Coordinate conversion failed when switching to Lon/Lat mode: {e}")
                        self.utm_epsg_input.clear()
        
        # Update UTM rounding combo state based on current mode
        self.utm_rounding_combo.setEnabled(self.utm_radio.isChecked())
        
        self._update_preview()
    
    def _on_utm_rounding_changed(self, index: int):
        """Handle UTM boundary rounding selection change."""
        rounding_value = self.utm_rounding_combo.currentData()
        
        if rounding_value is None or not self.utm_radio.isChecked():
            # No rounding or not in UTM mode
            return
        
        # Get current values
        boundaries = self._parse_boundaries()
        if not boundaries:
            return
        
        north, south, east, west = boundaries
        
        # Round to nearest value
        north = round(north / rounding_value) * rounding_value
        south = round(south / rounding_value) * rounding_value
        east = round(east / rounding_value) * rounding_value
        west = round(west / rounding_value) * rounding_value
        
        # Update values
        self.north_input.setText(f"{north:.2f}")
        self.south_input.setText(f"{south:.2f}")
        self.east_input.setText(f"{east:.2f}")
        self.west_input.setText(f"{west:.2f}")
    
    def _on_location_selected(self, index: int):
        """Handle city selection from dropdown."""
        coords = self.location_combo.currentData()
        
        if coords is None:  # "-- Select City --" or separator
            return
        
        # Update bbox name with city name
        city_name = self.location_combo.currentText()
        self.bbox_name_input.setText(city_name)
        
        lon, lat = coords
        
        # Create a bounding box around the city
        offset = self.DEFAULT_CITY_BBOX_OFFSET_DEGREES
        north = lat + offset
        south = lat - offset
        east = lon + offset
        west = lon - offset
        
        if self.lonlat_radio.isChecked():
            # Direct Lon/Lat input
            self.north_input.setText(f"{north:.6f}")
            self.south_input.setText(f"{south:.6f}")
            self.east_input.setText(f"{east:.6f}")
            self.west_input.setText(f"{west:.6f}")
        else:
            # Convert to UTM first
            utm_epsg_code = calculate_utm_epsg(lon, lat)
            epsg_code = f"EPSG:{utm_epsg_code}"
            
            self.utm_epsg_input.setText(str(utm_epsg_code))
            
            # Transform corners to UTM
            nw_x, nw_y = transform_coordinates(west, north, "EPSG:4326", epsg_code)
            ne_x, ne_y = transform_coordinates(east, north, "EPSG:4326", epsg_code)
            se_x, se_y = transform_coordinates(east, south, "EPSG:4326", epsg_code)
            sw_x, sw_y = transform_coordinates(west, south, "EPSG:4326", epsg_code)
            
            # Display boundaries in UTM
            self.north_input.setText(f"{max(nw_y, ne_y):.2f}")
            self.south_input.setText(f"{min(se_y, sw_y):.2f}")
            self.east_input.setText(f"{max(ne_x, se_x):.2f}")
            self.west_input.setText(f"{min(nw_x, sw_x):.2f}")
    
    def _format_bbox_text_report(self, bbox_name: str, north: float, south: float, 
                                  east: float, west: float, utm_epsg: str, 
                                  polygon, gdf, input_mode: str) -> str:
        """Format comprehensive text report for bounding box parameters.
        
        Args:
            bbox_name: Name of the bounding box
            north, south, east, west: Input boundary values
            utm_epsg: UTM EPSG code (e.g., 'EPSG:32633')
            polygon: Shapely polygon geometry in UTM
            gdf: GeoDataFrame containing the bbox geometry
            input_mode: Description of input coordinate system
            
        Returns:
            Formatted text content as a string
        """
        minx, miny, maxx, maxy = polygon.bounds
        area = polygon.area
        perimeter = polygon.length
        
        # Get WGS84 bounds for display
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        wgs84_bounds = gdf_wgs84.total_bounds
        wgs84_poly = gdf_wgs84.geometry.iloc[0]
        
        # Build text content in comprehensive format
        txt_content = []
        txt_content.append("========================================")
        txt_content.append("   BOUNDING BOX PARAMETERS")
        txt_content.append("========================================")
        txt_content.append("")
        
        # Input boundaries section
        txt_content.append("--- INPUT BOUNDARIES ---")
        txt_content.append("")
        txt_content.append(f"North: {north}")
        txt_content.append(f"South: {south}")
        txt_content.append(f"East: {east}")
        txt_content.append(f"West: {west}")
        txt_content.append("")
        
        # Bounding box extents section
        txt_content.append("--- BOUNDING BOX EXTENTS ---")
        txt_content.append("")
        txt_content.append(f"UTM ({utm_epsg}):")
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
        
        # Size and geometry section
        txt_content.append("--- SIZE AND GEOMETRY ---")
        txt_content.append("")
        txt_content.append(f"Area:       {area:.2f} m² ({area/1e6:.4f} km²)")
        txt_content.append(f"Perimeter:  {perimeter:.2f} m ({perimeter/1e3:.4f} km)")
        txt_content.append("")
        
        # CRS information section
        txt_content.append("--- COORDINATE REFERENCE SYSTEM ---")
        txt_content.append("")
        txt_content.append(f"Input CRS:  {input_mode}")
        txt_content.append(f"Output CRS: {('UTM ' + utm_epsg) if self.keep_utm.isChecked() else 'WGS84 (EPSG:4326)'}")
        txt_content.append(f"UTM Zone:   {utm_epsg}")
        txt_content.append("")
        
        # Configuration section
        txt_content.append("--- CONFIGURATION ---")
        txt_content.append("")
        txt_content.append(f"Bounding Box Name: {bbox_name}")
        txt_content.append(f"Input Method:      Point boundaries")
        txt_content.append(f"Keep UTM Projection: {'Yes' if self.keep_utm.isChecked() else 'No'}")
        txt_content.append("")
        
        # Corner points section
        txt_content.append("--- CORNER POINTS (WGS84) ---")
        txt_content.append("")
        coords_wgs84 = list(wgs84_poly.exterior.coords)[:-1]  # Remove duplicate last point
        for i, (lon, lat) in enumerate(coords_wgs84, 1):
            txt_content.append(f"  Point {i}: ({lon:.6f}, {lat:.6f})")
        txt_content.append("")
        txt_content.append("========================================")
        
        return '\n'.join(txt_content)
    
    def _browse_output(self):
        """Open file dialog to select output path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output Path",
            str(self._get_last_path("paths/bbox_creator/output_file") or Path.home()),
            "All Files (*)"
        )
        
        if file_path:
            # Remove any extension
            file_path = Path(file_path).with_suffix("")
            self.output_path.setText(str(file_path))
            self._save_last_path("paths/bbox_creator/output_file", str(file_path))
    
    def _parse_boundaries(self) -> Optional[tuple]:
        """Parse and validate boundary inputs.
        
        Returns:
            Tuple of (north, south, east, west) or None if invalid
        """
        try:
            north_text = self.north_input.text().strip()
            south_text = self.south_input.text().strip()
            east_text = self.east_input.text().strip()
            west_text = self.west_input.text().strip()
            
            if not all([north_text, south_text, east_text, west_text]):
                return None
            
            north = float(north_text)
            south = float(south_text)
            east = float(east_text)
            west = float(west_text)
            
            return (north, south, east, west)
        except ValueError:
            return None
    
    def _boundaries_to_utm(self, north: float, south: float, east: float, west: float) -> Tuple[list, str]:
        """
        Convert boundary coordinates to UTM and return corner points.
        Returns (utm_corner_coords, epsg_code)
        """
        if self.utm_radio.isChecked():
            # Already in UTM
            epsg_code = self.utm_epsg_input.text().strip()
            if not epsg_code:
                return [], ""
            # Create corners: NW, NE, SE, SW
            corners = [
                (west, north),
                (east, north),
                (east, south),
                (west, south)
            ]
            return corners, f"EPSG:{epsg_code}"
        
        # Convert from lon/lat to UTM
        # Use center point to determine UTM zone
        center_lon = (east + west) / 2
        center_lat = (north + south) / 2
        utm_epsg_num = calculate_utm_epsg(center_lon, center_lat)
        epsg_code = f"EPSG:{utm_epsg_num}"
        
        # Transform corner coordinates
        # Create corners: NW, NE, SE, SW (clockwise from top-left)
        corners = [
            transform_coordinates(west, north, "EPSG:4326", epsg_code),
            transform_coordinates(east, north, "EPSG:4326", epsg_code),
            transform_coordinates(east, south, "EPSG:4326", epsg_code),
            transform_coordinates(west, south, "EPSG:4326", epsg_code)
        ]
        
        return corners, epsg_code
    
    def _update_preview(self):
        """Schedule a debounced preview update to avoid excessive computations."""
        # Restart the timer - this debounces rapid changes (e.g., typing EPSG codes)
        self._preview_debounce_timer.stop()
        self._preview_debounce_timer.start()
    
    def _do_update_preview(self):
        """Actually update the preview fields based on current inputs (called after debounce delay)."""
        boundaries = self._parse_boundaries()
        
        if not boundaries:
            # Clear preview
            self.preview_centroid_x.clear()
            self.preview_centroid_y.clear()
            self.preview_width.clear()
            self.preview_height.clear()
            self.preview_area.clear()
            self.preview_perimeter.clear()
            return
        
        try:
            north, south, east, west = boundaries
            
            # Validate boundaries
            if north <= south:
                self.preview_area.setText("North must be > South")
                return
            if east <= west:
                self.preview_area.setText("East must be > West")
                return
            
            # Convert to UTM for calculations
            utm_corners, epsg_code = self._boundaries_to_utm(north, south, east, west)
            
            if not epsg_code or not utm_corners:
                return
            
            # Create polygon
            polygon = Polygon(utm_corners)
            
            if not polygon.is_valid:
                self.preview_area.setText("Invalid polygon!")
                return
            
            # Get bounds
            minx, miny, maxx, maxy = polygon.bounds
            
            # Calculate centroid, dimensions, area and perimeter
            centroid_x = (minx + maxx) / 2
            centroid_y = (miny + maxy) / 2
            width = maxx - minx
            height = maxy - miny
            area = polygon.area
            perimeter = polygon.length
            
            # Update preview fields
            self.preview_centroid_x.setText(f"{centroid_x:.2f}")
            self.preview_centroid_y.setText(f"{centroid_y:.2f}")
            self.preview_width.setText(f"{width:.2f}")
            self.preview_height.setText(f"{height:.2f}")
            self.preview_area.setText(f"{area:.2f}")
            self.preview_perimeter.setText(f"{perimeter:.2f}")
            
        except Exception as e:
            # Clear preview on error and log for debugging
            logging.debug(f"Preview update failed: {e}")
            self.preview_area.setText("Preview unavailable")
            self.preview_perimeter.clear()
    
    def validate_inputs(self) -> bool:
        """Validate all inputs before creating the bounding box."""
        # Check if output path is provided
        if not self.output_path.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please specify an output path.")
            return False
        
        # Check if at least one format is selected
        if not any([
            self.format_kml.isChecked(),
            self.format_shp.isChecked(),
            self.format_geojson.isChecked(),
            self.format_txt.isChecked(),
            self.format_kmz.isChecked(),
            self.format_gpkg.isChecked(),
            self.format_gml.isChecked(),
            self.format_tab.isChecked()
        ]):
            QMessageBox.warning(self, "Validation Error", "Please select at least one export format.")
            return False
        
        # Check if all boundaries are provided
        boundaries = self._parse_boundaries()
        if not boundaries:
            QMessageBox.warning(self, "Validation Error", "Please provide all 4 boundaries (North, South, East, West) with valid numeric values.")
            return False
        
        north, south, east, west = boundaries
        
        # Validate boundary relationships
        if north <= south:
            QMessageBox.warning(self, "Validation Error", "North boundary must be greater than South boundary.")
            return False
        
        if east <= west:
            QMessageBox.warning(self, "Validation Error", "East boundary must be greater than West boundary.")
            return False
        
        # Check UTM EPSG if in UTM mode
        if self.utm_radio.isChecked():
            epsg_text = self.utm_epsg_input.text().strip()
            if not epsg_text:
                QMessageBox.warning(self, "Validation Error", "Please provide a UTM zone EPSG code.")
                return False
            
            try:
                epsg_int = int(epsg_text)
                is_valid, error_msg = validate_utm_epsg(epsg_int)
                if not is_valid:
                    QMessageBox.warning(self, "Validation Error", error_msg)
                    return False
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Invalid UTM EPSG code.")
                return False
        
        # Validate polygon
        try:
            utm_corners, epsg_code = self._boundaries_to_utm(north, south, east, west)
            if not epsg_code or not utm_corners:
                QMessageBox.warning(self, "Validation Error", "Failed to determine coordinate system.")
                return False
            
            polygon = Polygon(utm_corners)
            
            if not polygon.is_valid:
                QMessageBox.warning(
                    self, 
                    "Invalid Polygon", 
                    "The boundaries do not form a valid polygon."
                )
                return False
            
        except Exception as e:
            QMessageBox.warning(self, "Validation Error", f"Error validating bounding box: {str(e)}")
            return False
        
        return True
    
    def _create_bbox(self):
        """Create the bounding box and export to selected formats."""
        # Configure GDAL
        gdal.UseExceptions()
        
        if not self.validate_inputs():
            return
        
        try:
            # Parse boundaries
            boundaries = self._parse_boundaries()
            if not boundaries:
                QMessageBox.warning(self, "Validation Error", "Please enter valid boundary values.")
                return
            north, south, east, west = boundaries
            utm_corners, utm_epsg = self._boundaries_to_utm(north, south, east, west)
            if not utm_corners or not utm_epsg:
                QMessageBox.warning(self, "Validation Error", "Failed to convert coordinates to UTM. Please check your EPSG code.")
                return
            
            # Create polygon
            polygon = Polygon(utm_corners)
            
            # Get bbox name from input
            bbox_name = self.bbox_name_input.text().strip() or "BBox"
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(
                {"geometry": [polygon], "name": [bbox_name]},
                crs=utm_epsg
            )
            
            # Get output path
            output_prefix = Path(self.output_path.text().strip())
            output_prefix.parent.mkdir(parents=True, exist_ok=True)
            
            # Save last path
            self._save_last_path("paths/bbox_creator/output_file", str(output_prefix))
            
            # Prepare output message
            results = []
            
            # Build format dictionary for export utility
            export_formats = {
                'geojson': self.format_geojson.isChecked(),
                'shp': self.format_shp.isChecked(),
                'gpkg': self.format_gpkg.isChecked(),
                'gml': self.format_gml.isChecked(),
                'tab': self.format_tab.isChecked(),
                'kml': self.format_kml.isChecked(),
                'kmz': self.format_kmz.isChecked()
            }
            
            # Export to GIS formats using utility
            try:
                exported_files = export_geodataframe_multi(
                    gdf, output_prefix, export_formats,
                    layer_name=bbox_name,
                    keep_utm=self.keep_utm.isChecked()
                )
                results = [f"{Path(f).suffix.upper()[1:]}: {f}" for f in exported_files]
            except Exception as e:
                raise Exception(f"Export failed: {str(e)}") from e
            
            # Text file with details
            if self.format_txt.isChecked():
                txt_path = output_prefix.with_suffix(".txt")
                
                # Get input mode description
                input_mode = 'WGS84 (EPSG:4326)' if self.lonlat_radio.isChecked() else f'UTM ({utm_epsg})'
                
                # Generate formatted text content
                txt_content = self._format_bbox_text_report(
                    bbox_name, north, south, east, west, 
                    utm_epsg, polygon, gdf, input_mode
                )
                
                # Write to file
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(txt_content)
                
                results.append(f"Text: {txt_path}")
            
            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Bounding box created successfully!\n\n{len(results)} file(s) exported."
            )
            
            self._update_status(f"Bounding box created: {len(results)} format(s) exported")
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create bounding box:\n{str(e)}"
            )
            main_window = self.window()
            if isinstance(main_window, QMainWindow) and main_window.statusBar():
                main_window.statusBar().showMessage("Error creating bounding box", 5000)
