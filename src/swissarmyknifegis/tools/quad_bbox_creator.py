"""
4-Point Bounding Box Creator Tool
Creates a bounding box by specifying four arbitrary corner points.
"""

from pathlib import Path
from typing import Optional, Tuple
import zipfile
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QRadioButton, 
    QCheckBox, QFileDialog, QMessageBox, QButtonGroup,
    QTextEdit, QComboBox
)
from PySide6.QtGui import QIntValidator

import geopandas as gpd
from shapely.geometry import Polygon, mapping
from pyproj import Transformer, CRS
from osgeo import gdal

from swissarmyknifegis.tools.base_tool import BaseTool
from swissarmyknifegis.core.cities import get_major_cities


class QuadBBoxCreatorTool(BaseTool):
    """Tool for creating bounding boxes from four arbitrary corner points."""
    
    def __init__(self):
        self.cities = get_major_cities()
        super().__init__()
        
    def get_tool_name(self) -> str:
        return "BBox - Points"
    
    def setup_ui(self):
        """Set up the user interface for the 4-point bounding box creator."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("Create Bounding Box from Boundaries")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        main_layout.addWidget(title)
        
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
        self.utm_epsg_input.setValidator(QIntValidator(32601, 32660))
        utm_zone_layout.addRow("EPSG Code:", self.utm_epsg_input)
        
        self.utm_zone_group.setLayout(utm_zone_layout)
        self.utm_zone_group.setVisible(False)
        main_layout.addWidget(self.utm_zone_group)
        
        # Quick location selector
        location_group = QGroupBox("Quick Location (Optional)")
        location_layout = QFormLayout()
        
        self.location_combo = QComboBox()
        self.location_combo.addItem("-- Select City --", None)
        
        # Add US cities
        for city_name, coords in self.cities.items():
            if ", USA" in city_name:
                self.location_combo.addItem(city_name, coords)
        
        # Add international cities
        for city_name, coords in self.cities.items():
            if ", USA" not in city_name:
                self.location_combo.addItem(city_name, coords)
        
        location_layout.addRow("Location:", self.location_combo)
        
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
        
        # Output Settings
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()
        
        # Output path
        path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Output path prefix (without extension)")
        last_path = self._get_last_path("output_file")
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
        self.format_txt = QCheckBox("Text")
        
        self.format_kml.setChecked(True)
        self.format_geojson.setChecked(True)
        
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
        self.keep_utm = QCheckBox("Keep UTM projection (default: convert to WGS84)")
        output_layout.addWidget(self.keep_utm)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # Preview Section
        preview_group = QGroupBox("Preview")
        preview_layout = QFormLayout()
        
        self.preview_minx = QLineEdit()
        self.preview_minx.setReadOnly(True)
        self.preview_miny = QLineEdit()
        self.preview_miny.setReadOnly(True)
        self.preview_maxx = QLineEdit()
        self.preview_maxx.setReadOnly(True)
        self.preview_maxy = QLineEdit()
        self.preview_maxy.setReadOnly(True)
        self.preview_area = QLineEdit()
        self.preview_area.setReadOnly(True)
        self.preview_perimeter = QLineEdit()
        self.preview_perimeter.setReadOnly(True)
        
        preview_layout.addRow("Min X:", self.preview_minx)
        preview_layout.addRow("Min Y:", self.preview_miny)
        preview_layout.addRow("Max X:", self.preview_maxx)
        preview_layout.addRow("Max Y:", self.preview_maxy)
        preview_layout.addRow("Area (m²):", self.preview_area)
        preview_layout.addRow("Perimeter (m):", self.preview_perimeter)
        
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)
        
        # Create Bounding Box Button
        self.create_button = QPushButton("Create Bounding Box")
        self.create_button.setMinimumHeight(40)
        self.create_button.clicked.connect(self._create_bbox)
        main_layout.addWidget(self.create_button)
        
        # Results Display
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
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
        """Handle coordinate system radio button changes."""
        self.utm_zone_group.setVisible(self.utm_radio.isChecked())
        self._update_preview()
    
    def _on_location_selected(self, index: int):
        """Handle city selection from dropdown."""
        coords = self.location_combo.currentData()
        
        if coords is None:  # "-- Select City --" or separator
            return
        
        lon, lat = coords
        
        # Create a bounding box around the city (approximately 0.1 degrees = ~11 km)
        offset = 0.1
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
            utm_zone = int((lon + 180) / 6) + 1
            if lat >= 0:
                epsg_code = f"EPSG:{32600 + utm_zone}"
            else:
                epsg_code = f"EPSG:{32700 + utm_zone}"
            
            self.utm_epsg_input.setText(str(32600 + utm_zone) if lat >= 0 else str(32700 + utm_zone))
            
            # Transform corners to UTM
            transformer = Transformer.from_crs("EPSG:4326", epsg_code, always_xy=True)
            nw_x, nw_y = transformer.transform(west, north)
            ne_x, ne_y = transformer.transform(east, north)
            se_x, se_y = transformer.transform(east, south)
            sw_x, sw_y = transformer.transform(west, south)
            
            # Display boundaries in UTM
            self.north_input.setText(f"{max(nw_y, ne_y):.2f}")
            self.south_input.setText(f"{min(se_y, sw_y):.2f}")
            self.east_input.setText(f"{max(ne_x, se_x):.2f}")
            self.west_input.setText(f"{min(nw_x, sw_x):.2f}")
    
    def _browse_output(self):
        """Open file dialog to select output path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output Path",
            str(self._get_last_path("output_file") or Path.home()),
            "All Files (*)"
        )
        
        if file_path:
            # Remove any extension
            file_path = Path(file_path).with_suffix("")
            self.output_path.setText(str(file_path))
            self._save_last_path("output_file", file_path)
    
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
                return None, None
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
        utm_zone = int((center_lon + 180) / 6) + 1
        
        # Determine hemisphere
        if center_lat >= 0:
            epsg_code = f"EPSG:{32600 + utm_zone}"
        else:
            epsg_code = f"EPSG:{32700 + utm_zone}"
        
        # Transform corner coordinates
        transformer = Transformer.from_crs("EPSG:4326", epsg_code, always_xy=True)
        
        # Create corners: NW, NE, SE, SW (clockwise from top-left)
        corners = [
            transformer.transform(west, north),
            transformer.transform(east, north),
            transformer.transform(east, south),
            transformer.transform(west, south)
        ]
        
        return corners, epsg_code
    
    def _update_preview(self):
        """Update the preview fields based on current inputs."""
        boundaries = self._parse_boundaries()
        
        if not boundaries:
            # Clear preview
            self.preview_minx.clear()
            self.preview_miny.clear()
            self.preview_maxx.clear()
            self.preview_maxy.clear()
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
            
            # Calculate area and perimeter
            area = polygon.area
            perimeter = polygon.length
            
            # Update preview fields
            self.preview_minx.setText(f"{minx:.2f}")
            self.preview_miny.setText(f"{miny:.2f}")
            self.preview_maxx.setText(f"{maxx:.2f}")
            self.preview_maxy.setText(f"{maxy:.2f}")
            self.preview_area.setText(f"{area:.2f}")
            self.preview_perimeter.setText(f"{perimeter:.2f}")
            
        except Exception:
            # Silently fail for preview updates
            pass
    
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
                if epsg_int < 32601 or epsg_int > 32760:
                    QMessageBox.warning(self, "Validation Error", "UTM EPSG code must be between 32601 and 32760.")
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
            north, south, east, west = boundaries
            utm_corners, utm_epsg = self._boundaries_to_utm(north, south, east, west)
            
            # Create polygon
            polygon = Polygon(utm_corners)
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(
                {"geometry": [polygon], "name": ["BBox"]},
                crs=utm_epsg
            )
            
            # Get output path
            output_prefix = Path(self.output_path.text().strip())
            output_prefix.parent.mkdir(parents=True, exist_ok=True)
            
            # Save last path
            self._save_last_path("output_file", output_prefix)
            
            # Prepare output message
            results = []
            
            # Export to selected formats
            if self.format_geojson.isChecked():
                geojson_path = output_prefix.with_suffix(".geojson")
                if self.keep_utm.isChecked():
                    gdf.to_file(geojson_path, driver="GeoJSON")
                else:
                    gdf.to_crs("EPSG:4326").to_file(geojson_path, driver="GeoJSON")
                results.append(f"GeoJSON: {geojson_path}")
            
            if self.format_shp.isChecked():
                shp_path = output_prefix.with_suffix(".shp")
                if self.keep_utm.isChecked():
                    gdf.to_file(shp_path, driver="ESRI Shapefile")
                else:
                    gdf.to_crs("EPSG:4326").to_file(shp_path, driver="ESRI Shapefile")
                results.append(f"Shapefile: {shp_path}")
            
            if self.format_gpkg.isChecked():
                gpkg_path = output_prefix.with_suffix(".gpkg")
                if self.keep_utm.isChecked():
                    gdf.to_file(gpkg_path, driver="GPKG", layer="bbox")
                else:
                    gdf.to_crs("EPSG:4326").to_file(gpkg_path, driver="GPKG", layer="bbox")
                results.append(f"GeoPackage: {gpkg_path}")
            
            if self.format_gml.isChecked():
                gml_path = output_prefix.with_suffix(".gml")
                if self.keep_utm.isChecked():
                    gdf.to_file(gml_path, driver="GML")
                else:
                    gdf.to_crs("EPSG:4326").to_file(gml_path, driver="GML")
                results.append(f"GML: {gml_path}")
            
            if self.format_tab.isChecked():
                tab_path = output_prefix.with_suffix(".tab")
                if self.keep_utm.isChecked():
                    gdf.to_file(tab_path, driver="MapInfo File")
                else:
                    gdf.to_crs("EPSG:4326").to_file(tab_path, driver="MapInfo File")
                results.append(f"MapInfo TAB: {tab_path}")
            
            # KML/KMZ require WGS84
            if self.format_kml.isChecked() or self.format_kmz.isChecked():
                gdf_wgs84 = gdf.to_crs("EPSG:4326")
                
                if self.format_kml.isChecked():
                    kml_path = output_prefix.with_suffix(".kml")
                    gdf_wgs84.to_file(kml_path, driver="KML")
                    results.append(f"KML: {kml_path}")
                
                if self.format_kmz.isChecked():
                    # Create KMZ by zipping KML
                    kml_temp_path = output_prefix.with_suffix(".temp.kml")
                    kmz_path = output_prefix.with_suffix(".kmz")
                    
                    gdf_wgs84.to_file(kml_temp_path, driver="KML")
                    
                    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
                        kmz.write(kml_temp_path, "doc.kml")
                    
                    kml_temp_path.unlink()
                    results.append(f"KMZ: {kmz_path}")
            
            # Text file with details
            if self.format_txt.isChecked():
                txt_path = output_prefix.with_suffix(".txt")
                
                minx, miny, maxx, maxy = polygon.bounds
                area = polygon.area
                perimeter = polygon.length
                
                with open(txt_path, 'w') as f:
                    f.write("Bounding Box Details\n")
                    f.write("=" * 50 + "\n\n")
                    
                    f.write("Boundaries:\n")
                    f.write(f"  North: {north}\n")
                    f.write(f"  South: {south}\n")
                    f.write(f"  East: {east}\n")
                    f.write(f"  West: {west}\n")
                    
                    f.write(f"\nCoordinate System: {utm_epsg}\n")
                    f.write(f"\nBounding Box Extents (UTM):\n")
                    f.write(f"  Min X: {minx:.2f}\n")
                    f.write(f"  Min Y: {miny:.2f}\n")
                    f.write(f"  Max X: {maxx:.2f}\n")
                    f.write(f"  Max Y: {maxy:.2f}\n")
                    f.write(f"\nArea: {area:.2f} m²\n")
                    f.write(f"Perimeter: {perimeter:.2f} m\n")
                    
                    # If converted to WGS84, add those coordinates
                    if not self.keep_utm.isChecked():
                        gdf_wgs84 = gdf.to_crs("EPSG:4326")
                        poly_wgs84 = gdf_wgs84.geometry.iloc[0]
                        coords_wgs84 = list(poly_wgs84.exterior.coords)[:-1]  # Remove duplicate last point
                        
                        f.write("\nCorner Points (WGS84):\n")
                        for i, (lon, lat) in enumerate(coords_wgs84, 1):
                            f.write(f"  Point {i}: ({lon:.6f}, {lat:.6f})\n")
                
                results.append(f"Text: {txt_path}")
            
            # Display results
            self.results_text.setPlainText("\n".join(results))
            
            QMessageBox.information(
                self,
                "Success",
                f"Bounding box created successfully!\n\n{len(results)} file(s) exported."
            )
            
            if self.window().statusBar():
                self.window().statusBar().showMessage(
                    f"Bounding box created: {len(results)} format(s) exported",
                    5000
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create bounding box:\n{str(e)}"
            )
            if self.window().statusBar():
                self.window().statusBar().showMessage("Error creating bounding box", 5000)
