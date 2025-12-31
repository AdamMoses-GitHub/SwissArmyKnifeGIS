"""
Coordinate System Converter Tool

Batch reproject GIS files (vector and raster) between different coordinate reference systems (CRS).
"""

import os
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QTextEdit,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt

from pyproj import CRS
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

from .base_tool import BaseTool


class CoordinateConverterTool(BaseTool):
    """Tool for batch reprojecting GIS files between coordinate reference systems."""
    
    # Common CRS presets
    COMMON_CRS = {
        "WGS84 (EPSG:4326)": "EPSG:4326",
        "WGS84 / Pseudo-Mercator (EPSG:3857)": "EPSG:3857",
        "UTM Zone 32N (EPSG:32632)": "EPSG:32632",
        "UTM Zone 33N (EPSG:32633)": "EPSG:32633",
        "UTM Zone 31N (EPSG:32631)": "EPSG:32631",
        "UTM Zone 30N (EPSG:32630)": "EPSG:32630",
        "UTM Zone 1N (EPSG:32601)": "EPSG:32601",
        "UTM Zone 10N (EPSG:32610)": "EPSG:32610",
        "UTM Zone 15N (EPSG:32615)": "EPSG:32615",
        "UTM Zone 18N (EPSG:32618)": "EPSG:32618",
        "NAD83 (EPSG:4269)": "EPSG:4269",
        "OSGB 1936 / British National Grid (EPSG:27700)": "EPSG:27700",
        "ETRS89 (EPSG:4258)": "EPSG:4258",
    }
    
    def __init__(self):
        # Data storage must be initialized BEFORE calling super().__init__()
        # because super().__init__() calls setup_ui() which uses self.loaded_files
        self.loaded_files: List[Dict[str, Any]] = []
        
        # UI Components
        self.files_table = None
        self.output_crs_combo = None
        self.output_crs_epsg = None
        self.output_dir_path = None
        self.results_display = None
        
        super().__init__()
        
    def get_tool_name(self) -> str:
        """Return the display name for this tool."""
        return "CRS Converter"
    
    def setup_ui(self):
        """Set up the user interface for the coordinate converter tool."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # === File Selection ===
        files_group = QGroupBox("GIS Files")
        files_layout = QVBoxLayout()
        
        # Buttons for file management
        file_buttons_layout = QHBoxLayout()
        
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._add_files)
        add_files_btn.setMinimumHeight(40)
        file_buttons_layout.addWidget(add_files_btn)
        
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self._remove_selected_files)
        remove_files_btn.setMinimumHeight(40)
        file_buttons_layout.addWidget(remove_files_btn)
        
        clear_files_btn = QPushButton("Clear All")
        clear_files_btn.clicked.connect(self._clear_all_files)
        clear_files_btn.setMinimumHeight(40)
        file_buttons_layout.addWidget(clear_files_btn)
        
        files_layout.addLayout(file_buttons_layout)
        
        # Files table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["Filename", "Type", "Current CRS", "Features/Size", "Path"])
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setMinimumHeight(200)
        files_layout.addWidget(self.files_table)
        
        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)
        
        # === Output CRS Selection ===
        crs_group = QGroupBox("Output Coordinate Reference System")
        crs_layout = QVBoxLayout()
        
        crs_form_layout = QFormLayout()
        
        # Output CRS combo
        crs_combo_layout = QHBoxLayout()
        self.output_crs_combo = QComboBox()
        self.output_crs_combo.setMinimumWidth(350)
        self.output_crs_combo.currentTextChanged.connect(self._on_output_crs_changed)
        crs_combo_layout.addWidget(self.output_crs_combo)
        
        self.output_crs_info = QPushButton("Info")
        self.output_crs_info.setMaximumWidth(60)
        self.output_crs_info.clicked.connect(self._show_output_crs_info)
        crs_combo_layout.addWidget(self.output_crs_info)
        
        crs_form_layout.addRow("Select CRS:", crs_combo_layout)
        
        # Custom EPSG input
        self.output_crs_epsg = QLineEdit()
        self.output_crs_epsg.setPlaceholderText("Or enter custom EPSG code (e.g., 4326)")
        self.output_crs_epsg.setMinimumWidth(350)
        self.output_crs_epsg.textChanged.connect(self._on_output_epsg_changed)
        crs_form_layout.addRow("Custom EPSG:", self.output_crs_epsg)
        
        crs_layout.addLayout(crs_form_layout)
        crs_group.setLayout(crs_layout)
        main_layout.addWidget(crs_group)
        
        # === Output Directory ===
        output_group = QGroupBox("Output Directory")
        output_layout = QFormLayout()
        
        output_dir_layout = QHBoxLayout()
        self.output_dir_path = QLineEdit()
        self.output_dir_path.setPlaceholderText("Select output directory for reprojected files...")
        self.output_dir_path.setMinimumWidth(350)
        
        browse_output_btn = QPushButton("Browse...")
        browse_output_btn.clicked.connect(self._browse_output_directory)
        
        output_dir_layout.addWidget(self.output_dir_path)
        output_dir_layout.addWidget(browse_output_btn)
        output_layout.addRow("Output Folder:", output_dir_layout)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # === Reproject Controls ===
        reproject_layout = QHBoxLayout()
        
        self.reproject_btn = QPushButton("Reproject All Files")
        self.reproject_btn.setMinimumHeight(40)
        self.reproject_btn.clicked.connect(self._reproject_all_files)
        
        reproject_layout.addWidget(self.reproject_btn)
        main_layout.addLayout(reproject_layout)
        
        # === Results Display ===
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setMinimumHeight(150)
        results_layout.addWidget(self.results_display)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        main_layout.addStretch()
        
        # Initialize CRS combo with common presets
        self._populate_crs_combo()
    
    def _populate_crs_combo(self):
        """Populate the CRS combo box with common presets and loaded file CRS."""
        self.output_crs_combo.blockSignals(True)
        self.output_crs_combo.clear()
        
        # Add common presets
        self.output_crs_combo.addItem("--- Common CRS ---", None)
        for name, epsg in self.COMMON_CRS.items():
            self.output_crs_combo.addItem(name, epsg)
        
        # Add CRS from loaded files
        unique_crs = set()
        for file_info in self.loaded_files:
            if file_info.get('crs'):
                unique_crs.add(file_info['crs'])
        
        if unique_crs:
            self.output_crs_combo.addItem("--- From Loaded Files ---", None)
            for crs_str in sorted(unique_crs):
                try:
                    crs = CRS.from_string(crs_str)
                    display_name = f"{crs.name} ({crs_str})"
                    self.output_crs_combo.addItem(display_name, crs_str)
                except:
                    self.output_crs_combo.addItem(crs_str, crs_str)
        
        # Set default to first common CRS
        self.output_crs_combo.setCurrentIndex(1)
        self.output_crs_combo.blockSignals(False)
    
    def _setup_file_input(self):
        """Set up UI for file reprojection."""
        form_layout = QFormLayout()
        
        # Input file
        input_file_layout = QHBoxLayout()
        self.input_file_path = QLineEdit()
        self.input_file_path.setPlaceholderText("Select input file...")
        self.input_file_path.setMinimumWidth(300)
        
        browse_input_btn = QPushButton("Browse...")
        browse_input_btn.clicked.connect(self._browse_input_file)
        
        input_file_layout.addWidget(self.input_file_path)
        input_file_layout.addWidget(browse_input_btn)
        form_layout.addRow("Input File:", input_file_layout)
        
    
    def _add_files(self):
        """Add GIS files to the conversion list."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select GIS Files",
            "",
            "All Supported (*.shp *.geojson *.json *.gpkg *.kml *.gml *.tif *.tiff *.img);;Vector (*.shp *.geojson *.json *.gpkg *.kml *.gml);;Raster (*.tif *.tiff *.img);;All Files (*.*)"
        )
        
        if not file_paths:
            return
        
        self.results_display.clear()
        
        for file_path in file_paths:
            # Check if already loaded
            if any(f['path'] == file_path for f in self.loaded_files):
                self.results_display.append(f"Skipped (already loaded): {os.path.basename(file_path)}")
                continue
            
            # Try to load file info
            file_info = self._get_file_info(file_path)
            if file_info:
                self.loaded_files.append(file_info)
                self.results_display.append(f"Added: {file_info['filename']}")
            else:
                self.results_display.append(f"Failed to load: {os.path.basename(file_path)}")
        
        self._update_table()
        self._populate_crs_combo()  # Update CRS combo with new file CRS
    
    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a GIS file."""
        try:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()
            
            # Try as vector first
            if ext in ['.shp', '.geojson', '.json', '.gpkg', '.kml', '.gml']:
                try:
                    gdf = gpd.read_file(file_path)
                    crs_str = str(gdf.crs) if gdf.crs else "No CRS"
                    
                    return {
                        'filename': filename,
                        'path': file_path,
                        'type': 'Vector',
                        'crs': crs_str,
                        'details': f"{len(gdf)} features",
                        'geometry_type': gdf.geometry.type.unique()[0] if len(gdf) > 0 else "Unknown"
                    }
                except Exception as e:
                    pass
            
            # Try as raster
            if ext in ['.tif', '.tiff', '.img', '.jpg', '.png']:
                try:
                    with rasterio.open(file_path) as src:
                        crs_str = str(src.crs) if src.crs else "No CRS"
                        
                        return {
                            'filename': filename,
                            'path': file_path,
                            'type': 'Raster',
                            'crs': crs_str,
                            'details': f"{src.width}x{src.height}, {src.count} bands",
                            'width': src.width,
                            'height': src.height,
                            'bands': src.count
                        }
                except Exception as e:
                    pass
            
            return None
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read file:\n{file_path}\n\n{str(e)}")
            return None
    
    def _update_table(self):
        """Update the files table with loaded files."""
        self.files_table.setRowCount(len(self.loaded_files))
        
        for i, file_info in enumerate(self.loaded_files):
            # Filename
            self.files_table.setItem(i, 0, QTableWidgetItem(file_info['filename']))
            
            # Type
            self.files_table.setItem(i, 1, QTableWidgetItem(file_info['type']))
            
            # CRS
            crs_item = QTableWidgetItem(file_info['crs'])
            if file_info['crs'] == "No CRS":
                crs_item.setForeground(Qt.GlobalColor.red)
            self.files_table.setItem(i, 2, crs_item)
            
            # Details
            self.files_table.setItem(i, 3, QTableWidgetItem(file_info['details']))
            
            # Path
            self.files_table.setItem(i, 4, QTableWidgetItem(file_info['path']))
    
    def _remove_selected_files(self):
        """Remove selected files from the list."""
        selected_rows = sorted(set(index.row() for index in self.files_table.selectedIndexes()), reverse=True)
        
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select files to remove.")
            return
        
        for row in selected_rows:
            del self.loaded_files[row]
        
        self._update_table()
        self._populate_crs_combo()
        self.results_display.append(f"Removed {len(selected_rows)} file(s)")
    
    def _clear_all_files(self):
        """Clear all files from the list."""
        if not self.loaded_files:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Are you sure you want to clear all files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.loaded_files.clear()
            self._update_table()
            self._populate_crs_combo()
            self.results_display.clear()
            self.results_display.append("All files cleared")
    
    def _on_output_crs_changed(self, text):
        """Handle output CRS combo box change."""
        if text and text.startswith("---"):
            return  # Skip separator items
        
        epsg_code = self.output_crs_combo.currentData()
        if epsg_code and not self.output_crs_epsg.hasFocus():
            self.output_crs_epsg.blockSignals(True)
            self.output_crs_epsg.setText(epsg_code)
            self.output_crs_epsg.blockSignals(False)
    
    def _on_output_epsg_changed(self, text):
        """Handle output EPSG text change."""
        if text and self.output_crs_epsg.hasFocus():
            # User is manually entering EPSG, clear combo selection context
            self.output_crs_combo.blockSignals(True)
            self.output_crs_combo.setCurrentIndex(-1)
            self.output_crs_combo.blockSignals(False)
    
    def _show_output_crs_info(self):
        """Show information about the output CRS."""
        crs_string = self.output_crs_epsg.text().strip()
        if not crs_string:
            QMessageBox.warning(self, "No CRS", "Please select or enter a CRS first.")
            return
        
        try:
            crs = CRS.from_string(crs_string)
            info = f"Name: {crs.name}\n\n"
            info += f"Type: {crs.type_name}\n\n"
            info += f"Authority: {crs.to_authority()}\n\n"
            info += f"Scope: {crs.scope or 'N/A'}\n\n"
            info += f"Area of Use: {crs.area_of_use.name if crs.area_of_use else 'N/A'}\n\n"
            info += f"WKT:\n{crs.to_wkt(pretty=True)}"
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Output CRS Information")
            msg.setText(info)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid CRS: {str(e)}")
    
    def _browse_output_directory(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        
        if dir_path:
            self.output_dir_path.setText(dir_path)
    
    def _get_output_crs(self) -> Optional[CRS]:
        """Get the output CRS object."""
        crs_string = self.output_crs_epsg.text().strip()
        if not crs_string:
            QMessageBox.warning(self, "Missing CRS", "Please select or enter an output CRS.")
            return None
        
        try:
            return CRS.from_string(crs_string)
        except Exception as e:
            QMessageBox.critical(self, "Invalid CRS", f"Invalid output CRS: {str(e)}")
            return None
    
    
    def _reproject_all_files(self):
        """Reproject all loaded files to the output CRS."""
        if not self.loaded_files:
            QMessageBox.warning(self, "No Files", "Please add files to reproject.")
            return
        
        output_crs = self._get_output_crs()
        if not output_crs:
            return
        
        output_dir = self.output_dir_path.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create output directory:\n{str(e)}")
                return
        
        self.results_display.clear()
        self.results_display.append(f"Reprojecting {len(self.loaded_files)} file(s) to {output_crs.name}...")
        self.results_display.append("=" * 60)
        
        success_count = 0
        error_count = 0
        
        for file_info in self.loaded_files:
            try:
                output_path = os.path.join(output_dir, file_info['filename'])
                
                if file_info['type'] == 'Vector':
                    self._reproject_vector(file_info, output_crs, output_path)
                else:  # Raster
                    self._reproject_raster(file_info, output_crs, output_path)
                
                self.results_display.append(f"✓ {file_info['filename']}")
                success_count += 1
                
            except Exception as e:
                self.results_display.append(f"✗ {file_info['filename']}: {str(e)}")
                error_count += 1
        
        self.results_display.append("=" * 60)
        self.results_display.append(f"Complete: {success_count} succeeded, {error_count} failed")
        
        if success_count > 0:
            QMessageBox.information(
                self,
                "Reprojection Complete",
                f"Successfully reprojected {success_count} file(s) to:\n{output_dir}"
            )
    
    def _reproject_vector(self, file_info: Dict[str, Any], output_crs: CRS, output_path: str):
        """Reproject a vector file."""
        gdf = gpd.read_file(file_info['path'])
        
        # Set CRS if missing
        if gdf.crs is None:
            raise Exception("No CRS defined - cannot reproject")
        
        # Reproject
        gdf_reprojected = gdf.to_crs(output_crs)
        
        # Determine driver from extension
        ext = os.path.splitext(output_path)[1].lower()
        driver_map = {
            '.shp': 'ESRI Shapefile',
            '.geojson': 'GeoJSON',
            '.json': 'GeoJSON',
            '.gpkg': 'GPKG',
            '.kml': 'KML',
            '.gml': 'GML'
        }
        driver = driver_map.get(ext, 'ESRI Shapefile')
        
        # Save
        gdf_reprojected.to_file(output_path, driver=driver)
    
    def _reproject_raster(self, file_info: Dict[str, Any], output_crs: CRS, output_path: str):
        """Reproject a raster file."""
        with rasterio.open(file_info['path']) as src:
            if src.crs is None:
                raise Exception("No CRS defined - cannot reproject")
            
            # Calculate transform and dimensions for output
            transform, width, height = calculate_default_transform(
                src.crs, output_crs, src.width, src.height, *src.bounds
            )
            
            # Update metadata
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': output_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            
            # Create output file
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=output_crs,
                        resampling=Resampling.bilinear
                    )
    
    def validate_inputs(self) -> bool:
        """Validate user inputs."""
        return len(self.loaded_files) > 0 and self._get_output_crs() is not None
