"""
GIS Cropper Tool - Analyze and crop GIS files by bounding box.
"""

from pathlib import Path
from typing import List, Dict, Optional
import traceback

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QListWidget, QTextEdit, QSplitter
)

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping
import numpy as np

from swissarmyknifegis.tools.base_tool import BaseTool


class GISCropperTool(BaseTool):
    """
    Tool for analyzing and cropping GIS files by a bounding box.
    
    Features:
    - Select multiple vector or raster GIS files
    - Select a bounding box file
    - Analyze spatial relationship (inside, partial, outside)
    - Crop all files by the bounding box
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gis_files = []
        self.bbox_file = None
        self.bbox_geometry = None
        self.analysis_results = {}
        
    def get_tool_name(self) -> str:
        """Return the display name for this tool."""
        return "GIS Cropper"
        
    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)
        
        # GIS Files Selection Group
        gis_files_group = QGroupBox("GIS Files to Process")
        gis_files_layout = QVBoxLayout(gis_files_group)
        
        # List widget to show selected files
        self.gis_files_list = QListWidget()
        self.gis_files_list.setMinimumHeight(150)
        gis_files_layout.addWidget(self.gis_files_list)
        
        # Buttons for file management
        gis_buttons_layout = QHBoxLayout()
        
        self.add_files_button = QPushButton("Add Files...")
        self.add_files_button.clicked.connect(self._on_add_gis_files)
        gis_buttons_layout.addWidget(self.add_files_button)
        
        self.remove_files_button = QPushButton("Remove Selected")
        self.remove_files_button.clicked.connect(self._on_remove_gis_files)
        gis_buttons_layout.addWidget(self.remove_files_button)
        
        self.clear_files_button = QPushButton("Clear All")
        self.clear_files_button.clicked.connect(self._on_clear_gis_files)
        gis_buttons_layout.addWidget(self.clear_files_button)
        
        gis_buttons_layout.addStretch()
        gis_files_layout.addLayout(gis_buttons_layout)
        
        main_layout.addWidget(gis_files_group)
        
        # Bounding Box Selection Group
        bbox_group = QGroupBox("Bounding Box File")
        bbox_layout = QVBoxLayout(bbox_group)
        
        bbox_select_layout = QHBoxLayout()
        
        self.bbox_path_input = QLineEdit()
        self.bbox_path_input.setPlaceholderText("Select a bounding box file...")
        self.bbox_path_input.setReadOnly(True)
        bbox_select_layout.addWidget(self.bbox_path_input)
        
        self.browse_bbox_button = QPushButton("Browse...")
        self.browse_bbox_button.clicked.connect(self._on_browse_bbox)
        bbox_select_layout.addWidget(self.browse_bbox_button)
        
        bbox_layout.addLayout(bbox_select_layout)
        main_layout.addWidget(bbox_group)
        
        # Output Directory Group
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout(output_group)
        
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Select output directory for cropped files...")
        output_layout.addWidget(self.output_dir_input)
        
        self.browse_output_button = QPushButton("Browse...")
        self.browse_output_button.clicked.connect(self._on_browse_output)
        output_layout.addWidget(self.browse_output_button)
        
        main_layout.addWidget(output_group)
        
        # Action Buttons
        action_buttons_layout = QHBoxLayout()
        
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setMinimumHeight(40)
        self.analyze_button.clicked.connect(self._on_analyze)
        action_buttons_layout.addWidget(self.analyze_button)
        
        self.crop_button = QPushButton("Crop")
        self.crop_button.setMinimumHeight(40)
        self.crop_button.clicked.connect(self._on_crop)
        self.crop_button.setEnabled(False)  # Disabled until analysis is done
        action_buttons_layout.addWidget(self.crop_button)
        
        main_layout.addLayout(action_buttons_layout)
        
        # Results Display
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(200)
        results_layout.addWidget(self.results_text)
        
        main_layout.addWidget(results_group)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
    def _on_add_gis_files(self):
        """Handle Add Files button click."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select GIS Files",
            "",
            "GIS Files (*.shp *.geojson *.gpkg *.kml *.tif *.tiff *.img *.asc);;All Files (*)"
        )
        
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.gis_files:
                    self.gis_files.append(file_path)
                    self.gis_files_list.addItem(Path(file_path).name)
            
            # Clear previous analysis results
            self.analysis_results = {}
            self.crop_button.setEnabled(False)
            self.results_text.clear()
            
    def _on_remove_gis_files(self):
        """Handle Remove Selected button click."""
        selected_items = self.gis_files_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            row = self.gis_files_list.row(item)
            self.gis_files_list.takeItem(row)
            del self.gis_files[row]
        
        # Clear previous analysis results
        self.analysis_results = {}
        self.crop_button.setEnabled(False)
        self.results_text.clear()
        
    def _on_clear_gis_files(self):
        """Handle Clear All button click."""
        self.gis_files.clear()
        self.gis_files_list.clear()
        self.analysis_results = {}
        self.crop_button.setEnabled(False)
        self.results_text.clear()
        
    def _on_browse_bbox(self):
        """Handle Browse button click for bounding box selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Bounding Box File",
            "",
            "Vector Files (*.shp *.geojson *.gpkg *.kml *.gml);;All Files (*)"
        )
        
        if file_path:
            self.bbox_file = file_path
            self.bbox_path_input.setText(file_path)
            
            # Try to load the bounding box geometry
            try:
                gdf = gpd.read_file(file_path)
                if len(gdf) > 0:
                    # Use the first geometry
                    self.bbox_geometry = gdf.geometry.iloc[0]
                    self.results_text.append(f"Bounding box loaded: {Path(file_path).name}")
                else:
                    self.bbox_geometry = None
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Bounding box file contains no geometries."
                    )
            except Exception as e:
                self.bbox_geometry = None
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load bounding box:\n{str(e)}"
                )
            
            # Clear previous analysis results
            self.analysis_results = {}
            self.crop_button.setEnabled(False)
            
    def _on_browse_output(self):
        """Handle Browse button click for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        
        if dir_path:
            self.output_dir_input.setText(dir_path)
            
    def _on_analyze(self):
        """Analyze spatial relationship between GIS files and bounding box."""
        # Validate inputs
        if not self.gis_files:
            QMessageBox.warning(self, "Validation Error", "Please add at least one GIS file.")
            return
            
        if not self.bbox_file or self.bbox_geometry is None:
            QMessageBox.warning(self, "Validation Error", "Please select a valid bounding box file.")
            return
        
        # Clear previous results
        self.analysis_results = {}
        self.results_text.clear()
        self.results_text.append("=== ANALYSIS RESULTS ===\n")
        
        # Load bbox CRS
        bbox_gdf = gpd.read_file(self.bbox_file)
        bbox_crs = bbox_gdf.crs
        bbox_bounds = bbox_gdf.total_bounds
        
        # Display bounding box information
        self.results_text.append("BOUNDING BOX:")
        self.results_text.append(f"  File: {Path(self.bbox_file).name}")
        self.results_text.append(f"  CRS: {bbox_crs}")
        self.results_text.append(f"  Extents:")
        self.results_text.append(f"    Min X (West):  {bbox_bounds[0]:.6f}")
        self.results_text.append(f"    Min Y (South): {bbox_bounds[1]:.6f}")
        self.results_text.append(f"    Max X (East):  {bbox_bounds[2]:.6f}")
        self.results_text.append(f"    Max Y (North): {bbox_bounds[3]:.6f}")
        self.results_text.append(f"  Width:  {bbox_bounds[2] - bbox_bounds[0]:.6f}")
        self.results_text.append(f"  Height: {bbox_bounds[3] - bbox_bounds[1]:.6f}")
        self.results_text.append("\n" + "="*50 + "\n")
        
        # Analyze each file
        for file_path in self.gis_files:
            file_name = Path(file_path).name
            self.results_text.append(f"FILE: {file_name}")
            
            try:
                # Determine if raster or vector
                if self._is_raster(file_path):
                    result = self._analyze_raster(file_path, bbox_gdf)
                else:
                    result = self._analyze_vector(file_path, bbox_gdf)
                
                self.analysis_results[file_path] = result
                
                # Display file extents (already in bbox CRS from analysis)
                if 'bounds' in result:
                    bounds = result['bounds']
                    self.results_text.append(f"  CRS: {result.get('crs', 'Unknown')}")
                    self.results_text.append(f"  Extents (in bbox CRS):")
                    self.results_text.append(f"    Min X (West):  {bounds[0]:.6f}")
                    self.results_text.append(f"    Min Y (South): {bounds[1]:.6f}")
                    self.results_text.append(f"    Max X (East):  {bounds[2]:.6f}")
                    self.results_text.append(f"    Max Y (North): {bounds[3]:.6f}")
                    self.results_text.append(f"  Width:  {bounds[2] - bounds[0]:.6f}")
                    self.results_text.append(f"  Height: {bounds[3] - bounds[1]:.6f}")
                    self.results_text.append("")
                
                # Display overlap analysis
                status = result['status']
                if status == 'inside':
                    self.results_text.append(f"  ✓ INSIDE: Entire file fits within bounding box")
                elif status == 'partial':
                    self.results_text.append(f"  ⚠ PARTIAL: File partially overlaps bounding box")
                    if 'overlap_info' in result:
                        overlap = result['overlap_info']
                        self.results_text.append(f"    - File extends beyond bbox in:")
                        if overlap.get('extends_west'):
                            self.results_text.append(f"      • West by {overlap['extends_west']:.6f}")
                        if overlap.get('extends_east'):
                            self.results_text.append(f"      • East by {overlap['extends_east']:.6f}")
                        if overlap.get('extends_south'):
                            self.results_text.append(f"      • South by {overlap['extends_south']:.6f}")
                        if overlap.get('extends_north'):
                            self.results_text.append(f"      • North by {overlap['extends_north']:.6f}")
                elif status == 'outside':
                    self.results_text.append(f"  ✗ OUTSIDE: File does not intersect bounding box")
                else:
                    self.results_text.append(f"  ? UNKNOWN: {result.get('error', 'Unknown error')}")
                
                self.results_text.append("\n" + "-"*50 + "\n")
                
            except Exception as e:
                self.analysis_results[file_path] = {'status': 'error', 'error': str(e)}
                self.results_text.append(f"  ✗ ERROR: {str(e)}\n")
                self.results_text.append("-"*50 + "\n")
        
        self.results_text.append("=== ANALYSIS COMPLETE ===")
        
        # Enable crop button if we have results
        if self.analysis_results:
            self.crop_button.setEnabled(True)
            
    def _on_crop(self):
        """Crop all GIS files by the bounding box."""
        # Validate inputs
        if not self.analysis_results:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please run analysis first before cropping."
            )
            return
            
        if not self.output_dir_input.text().strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select an output directory."
            )
            return
        
        output_dir = Path(self.output_dir_input.text())
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear results and show cropping progress
        self.results_text.clear()
        self.results_text.append("=== CROPPING FILES ===\n")
        
        # Load bbox
        bbox_gdf = gpd.read_file(self.bbox_file)
        
        cropped_count = 0
        skipped_count = 0
        error_count = 0
        
        for file_path in self.gis_files:
            file_name = Path(file_path).name
            result = self.analysis_results.get(file_path, {})
            status = result.get('status', 'unknown')
            
            # Skip files that don't intersect
            if status == 'outside':
                self.results_text.append(f"Skipping (outside bbox): {file_name}")
                skipped_count += 1
                continue
            
            if status == 'error':
                self.results_text.append(f"Skipping (analysis error): {file_name}")
                skipped_count += 1
                continue
            
            self.results_text.append(f"Cropping: {file_name}")
            
            try:
                # Determine output path
                output_path = output_dir / f"cropped_{file_name}"
                
                # Crop based on file type
                if self._is_raster(file_path):
                    self._crop_raster(file_path, bbox_gdf, output_path)
                else:
                    self._crop_vector(file_path, bbox_gdf, output_path)
                
                self.results_text.append(f"  ✓ Saved to: {output_path.name}\n")
                cropped_count += 1
                
            except Exception as e:
                self.results_text.append(f"  ✗ ERROR: {str(e)}\n")
                error_count += 1
        
        # Summary
        self.results_text.append("=== CROPPING COMPLETE ===")
        self.results_text.append(f"Cropped: {cropped_count}")
        self.results_text.append(f"Skipped: {skipped_count}")
        self.results_text.append(f"Errors: {error_count}")
        
        QMessageBox.information(
            self,
            "Crop Complete",
            f"Cropping complete!\n\n"
            f"Cropped: {cropped_count}\n"
            f"Skipped: {skipped_count}\n"
            f"Errors: {error_count}"
        )
        
    def _is_raster(self, file_path: str) -> bool:
        """Check if file is a raster format."""
        raster_extensions = {'.tif', '.tiff', '.img', '.asc', '.jp2', '.png', '.jpg'}
        return Path(file_path).suffix.lower() in raster_extensions
        
    def _analyze_vector(self, file_path: str, bbox_gdf: gpd.GeoDataFrame) -> Dict:
        """Analyze spatial relationship for vector file."""
        try:
            # Read vector file
            gdf = gpd.read_file(file_path)
            original_crs = gdf.crs
            
            # Reproject to bbox CRS if needed
            if gdf.crs != bbox_gdf.crs:
                gdf = gdf.to_crs(bbox_gdf.crs)
            
            # Get bbox geometry and bounds
            bbox_geom = bbox_gdf.geometry.iloc[0]
            bbox_bounds = bbox_gdf.total_bounds
            
            # Check relationship
            # Get union of all geometries in the file
            file_geom = gdf.geometry.unary_union
            file_bounds = gdf.total_bounds
            
            result = {
                'type': 'vector',
                'crs': str(original_crs),
                'bounds': file_bounds
            }
            
            # Check if entirely within bbox
            if bbox_geom.contains(file_geom):
                result['status'] = 'inside'
                return result
            
            # Check if intersects at all
            if not bbox_geom.intersects(file_geom):
                result['status'] = 'outside'
                return result
            
            # Must be partial overlap - calculate how much it extends
            result['status'] = 'partial'
            overlap_info = {}
            
            # Check each direction
            if file_bounds[0] < bbox_bounds[0]:  # Extends west
                overlap_info['extends_west'] = bbox_bounds[0] - file_bounds[0]
            if file_bounds[2] > bbox_bounds[2]:  # Extends east
                overlap_info['extends_east'] = file_bounds[2] - bbox_bounds[2]
            if file_bounds[1] < bbox_bounds[1]:  # Extends south
                overlap_info['extends_south'] = bbox_bounds[1] - file_bounds[1]
            if file_bounds[3] > bbox_bounds[3]:  # Extends north
                overlap_info['extends_north'] = file_bounds[3] - bbox_bounds[3]
            
            result['overlap_info'] = overlap_info
            return result
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'type': 'vector'}
            
    def _analyze_raster(self, file_path: str, bbox_gdf: gpd.GeoDataFrame) -> Dict:
        """Analyze spatial relationship for raster file."""
        try:
            with rasterio.open(file_path) as src:
                # Get raster bounds as geometry
                raster_bounds = box(*src.bounds)
                original_crs = src.crs
                
                # Create GeoDataFrame for raster bounds
                raster_gdf = gpd.GeoDataFrame(
                    {'geometry': [raster_bounds]},
                    crs=src.crs
                )
                
                # Reproject to bbox CRS if needed
                if raster_gdf.crs != bbox_gdf.crs:
                    raster_gdf = raster_gdf.to_crs(bbox_gdf.crs)
                
                # Get bbox geometry and bounds
                bbox_geom = bbox_gdf.geometry.iloc[0]
                bbox_bounds = bbox_gdf.total_bounds
                raster_geom = raster_gdf.geometry.iloc[0]
                file_bounds = raster_gdf.total_bounds
                
                result = {
                    'type': 'raster',
                    'crs': str(original_crs),
                    'bounds': file_bounds
                }
                
                # Check if entirely within bbox
                if bbox_geom.contains(raster_geom):
                    result['status'] = 'inside'
                    return result
                
                # Check if intersects at all
                if not bbox_geom.intersects(raster_geom):
                    result['status'] = 'outside'
                    return result
                
                # Must be partial overlap - calculate how much it extends
                result['status'] = 'partial'
                overlap_info = {}
                
                # Check each direction
                if file_bounds[0] < bbox_bounds[0]:  # Extends west
                    overlap_info['extends_west'] = bbox_bounds[0] - file_bounds[0]
                if file_bounds[2] > bbox_bounds[2]:  # Extends east
                    overlap_info['extends_east'] = file_bounds[2] - bbox_bounds[2]
                if file_bounds[1] < bbox_bounds[1]:  # Extends south
                    overlap_info['extends_south'] = bbox_bounds[1] - file_bounds[1]
                if file_bounds[3] > bbox_bounds[3]:  # Extends north
                    overlap_info['extends_north'] = file_bounds[3] - bbox_bounds[3]
                
                result['overlap_info'] = overlap_info
                return result
                
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'type': 'raster'}
            
    def _crop_vector(self, file_path: str, bbox_gdf: gpd.GeoDataFrame, output_path: Path):
        """Crop vector file by bounding box."""
        # Read vector file
        gdf = gpd.read_file(file_path)
        
        # Reproject to bbox CRS if needed
        if gdf.crs != bbox_gdf.crs:
            gdf = gdf.to_crs(bbox_gdf.crs)
        
        # Get bbox geometry
        bbox_geom = bbox_gdf.geometry.iloc[0]
        
        # Clip geometries
        clipped = gdf.clip(bbox_geom)
        
        # Save to output
        # Determine driver based on extension
        ext = output_path.suffix.lower()
        if ext == '.shp':
            driver = 'ESRI Shapefile'
        elif ext == '.geojson':
            driver = 'GeoJSON'
        elif ext == '.gpkg':
            driver = 'GPKG'
        elif ext == '.kml':
            driver = 'KML'
        elif ext == '.gml':
            driver = 'GML'
        else:
            # Default to original format
            driver = None
            
        if driver:
            clipped.to_file(output_path, driver=driver)
        else:
            # Try to save with same format as input
            clipped.to_file(output_path)
            
    def _crop_raster(self, file_path: str, bbox_gdf: gpd.GeoDataFrame, output_path: Path):
        """Crop raster file by bounding box."""
        with rasterio.open(file_path) as src:
            # Reproject bbox to raster CRS
            bbox_reprojected = bbox_gdf.to_crs(src.crs)
            bbox_geom = bbox_reprojected.geometry.iloc[0]
            
            # Crop raster
            out_image, out_transform = mask(
                src,
                [mapping(bbox_geom)],
                crop=True,
                filled=True
            )
            
            # Update metadata
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })
            
            # Ensure output has .tif extension for GeoTIFF
            if output_path.suffix.lower() not in ['.tif', '.tiff']:
                output_path = output_path.with_suffix('.tif')
            
            # Write cropped raster
            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_image)
