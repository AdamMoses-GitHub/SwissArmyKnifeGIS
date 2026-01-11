from pathlib import Path
from typing import List, Dict, Optional
import traceback
import tempfile
import json

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
from osgeo import gdal, ogr, osr

from swissarmyknifegis.tools.base_tool import BaseTool

# Configure GDAL to use Python exceptions
gdal.UseExceptions()


class GISCropperTool(BaseTool):
    """
    Tool for analyzing and cropping GIS files by bounding box.
    """
    def analyze_spatial_relationship(self, file_geom, bbox_geom, file_bounds, bbox_bounds, total_area=None, inside_area=None, total_pixels=None, inside_pixels=None):
        """
        Shared logic for overlap/containment and percentage calculation.
        For vector: use area, for raster: use pixel counts.
        """
        from shapely.geometry.base import BaseGeometry
        result = {}
        # Percentage calculation
        if total_area is not None and inside_area is not None:
            percentage = (inside_area / total_area * 100) if total_area > 0 else 0.0
        elif total_pixels is not None and inside_pixels is not None:
            percentage = (inside_pixels / total_pixels * 100) if total_pixels > 0 else 0.0
        else:
            percentage = None
        if percentage is not None:
            result['percentage'] = round(percentage, 2)

        # Containment/overlap
        if isinstance(file_geom, BaseGeometry) and isinstance(bbox_geom, BaseGeometry):
            if bbox_geom.contains(file_geom):
                result['status'] = 'inside'
                return result
            if not bbox_geom.intersects(file_geom):
                result['status'] = 'outside'
                result['percentage'] = 0.0
                return result
            result['status'] = 'partial'
            overlap_info = {}
            if file_bounds[0] < bbox_bounds[0]:
                overlap_info['extends_west'] = bbox_bounds[0] - file_bounds[0]
            if file_bounds[2] > bbox_bounds[2]:
                overlap_info['extends_east'] = file_bounds[2] - bbox_bounds[2]
            if file_bounds[1] < bbox_bounds[1]:
                overlap_info['extends_south'] = bbox_bounds[1] - file_bounds[1]
            if file_bounds[3] > bbox_bounds[3]:
                overlap_info['extends_north'] = file_bounds[3] - bbox_bounds[3]
            result['overlap_info'] = overlap_info
        return result

    def ensure_same_crs(self, gdf, target_crs):
        """Return GeoDataFrame in target_crs if needed and possible."""
        if gdf.crs and target_crs and gdf.crs != target_crs:
            return gdf.to_crs(target_crs)
        return gdf

    def _get_shapely_geom(self, geom):
        # Helper to extract a shapely geometry from a GeoDataFrame, Series, or geometry
        import pandas as pd
        from shapely.geometry.base import BaseGeometry
        if isinstance(geom, BaseGeometry):
            return geom
        if isinstance(geom, pd.Series) or hasattr(geom, 'iloc'):
            return geom.iloc[0]
        return geom

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
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
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
        last_path = self._get_last_path("paths/input/gis_files")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select GIS Files",
            last_path,
            "GIS Files (*.shp *.geojson *.gpkg *.kml *.tif *.tiff *.img *.asc);;All Files (*)"
        )
        
        if file_paths:
            self._save_last_path("paths/input/gis_files", file_paths[0])
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
        last_path = self._get_last_path("paths/gis_cropper/bbox_file")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Bounding Box File",
            last_path,
            "Vector Files (*.shp *.geojson *.gpkg *.kml *.gml);;All Files (*)"
        )
        
        if file_path:
            self._save_last_path("paths/gis_cropper/bbox_file", file_path)
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
        last_path = self._get_last_path("paths/output/directory")
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            last_path
        )
        
        if dir_path:
            self._save_last_path("paths/output/directory", dir_path)
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
                percentage = result.get('percentage')
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

                # Show percentage if available
                if percentage is not None:
                    self.results_text.append(f"  Coverage: {percentage:.2f}% of file within bounding box")

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
        # Validate all inputs
        if not self.validate_inputs():
            return
        
        # Additional validation for analysis results
        if not self.analysis_results:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please run analysis first before cropping."
            )
            return
        
        output_dir = Path(self.output_dir_input.text())
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear results and show cropping progress
        self.results_text.clear()
        self.results_text.append("=== CROPPING FILES ===\n")
        
        # Load bbox with error handling
        try:
            bbox_gdf = gpd.read_file(self.bbox_file)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load bounding box file: {str(e)}")
            self.results_text.append(f"✗ Error loading bbox: {str(e)}")
            return
        
        # Validate bbox CRS
        if bbox_gdf.crs is None:
            QMessageBox.critical(self, "Error", "Bounding box file has no CRS defined")
            self.results_text.append("✗ Bounding box has no CRS")
            return
        
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
            
            # Reproject to bbox CRS if needed and possible
            gdf = self.ensure_same_crs(gdf, bbox_gdf.crs)

            # Get bbox geometry and bounds (ensure shapely geometry, not Series)
            bbox_geom = bbox_gdf.geometry.values[0]
            bbox_bounds = bbox_gdf.total_bounds

            # Get union of all geometries in the file as a shapely geometry
            file_geom = gdf.geometry.unary_union
            file_bounds = gdf.total_bounds
            intersection_geom = file_geom.intersection(bbox_geom)
            total_area = file_geom.area if file_geom.area > 0 else 0
            inside_area = intersection_geom.area if not intersection_geom.is_empty else 0
            result = {
                'type': 'vector',
                'crs': str(original_crs),
                'bounds': file_bounds
            }
            result.update(self.analyze_spatial_relationship(
                file_geom, bbox_geom, file_bounds, bbox_bounds,
                total_area=total_area, inside_area=inside_area
            ))
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
                
                # Reproject to bbox CRS if needed and possible
                raster_gdf = self.ensure_same_crs(raster_gdf, bbox_gdf.crs)
                # Get bbox geometry and bounds (ensure shapely geometry, not Series)
                bbox_geom = self._get_shapely_geom(bbox_gdf.geometry)
                bbox_bounds = bbox_gdf.total_bounds
                raster_geom = self._get_shapely_geom(raster_gdf.geometry)
                file_bounds = raster_gdf.total_bounds
                
                result = {
                    'type': 'raster',
                    'crs': str(original_crs),
                    'bounds': file_bounds
                }
                # Calculate percentage of valid pixels within bbox
                full_data = src.read(1, masked=True)
                total_pixels = np.count_nonzero(~full_data.mask) if hasattr(full_data, 'mask') else full_data.size
                from shapely.geometry.base import BaseGeometry
                geom_for_mapping = bbox_geom if isinstance(bbox_geom, BaseGeometry) else self._get_shapely_geom(bbox_geom)
                bbox_shapes = [mapping(geom_for_mapping)]
                try:
                    clipped, _ = mask(src, bbox_shapes, crop=False, filled=True)
                    clipped_masked = np.ma.masked_array(clipped[0], mask=(clipped[0] == src.nodata) if src.nodata is not None else False)
                    inside_pixels = np.count_nonzero(~clipped_masked.mask) if hasattr(clipped_masked, 'mask') else clipped_masked.size
                except Exception:
                    inside_pixels = 0
                result.update(self.analyze_spatial_relationship(
                    raster_geom, bbox_geom, file_bounds, bbox_bounds,
                    total_pixels=total_pixels, inside_pixels=inside_pixels
                ))
                return result
                
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'type': 'raster'}
            
    def _crop_vector(self, file_path: str, bbox_gdf: gpd.GeoDataFrame, output_path: Path):
        """Crop vector file by bounding box."""
        # Read vector file
        gdf = gpd.read_file(file_path)
        
        # Validate input CRS
        if bbox_gdf.crs is None:
            raise ValueError("Bounding box has no CRS defined")
        
        # Reproject to bbox CRS if needed
        if gdf.crs != bbox_gdf.crs:
            gdf = gdf.to_crs(bbox_gdf.crs)
        
        # Get bbox geometry as Shapely geometry object
        bbox_geom = bbox_gdf.geometry.values[0]
        
        # Clip geometries - convert to tuple of bounds for clip operation
        clipped = gdf.clip(bbox_gdf)
        
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
        """Crop raster file by bounding box using GDAL Warp for better performance."""
        # Open source raster to get CRS
        src_ds = gdal.Open(file_path, gdal.GA_ReadOnly)
        if src_ds is None:
            raise Exception(f"Failed to open raster: {file_path}")
        
        try:
            # Get raster CRS
            src_srs = osr.SpatialReference()
            src_srs.ImportFromWkt(src_ds.GetProjection())
            
            # Reproject bbox to raster CRS
            bbox_reprojected = bbox_gdf.to_crs(src_srs.ExportToProj4())
            bbox_geom = bbox_reprojected.geometry.values[0]
            
            # Create a temporary GeoJSON file for the cutline
            with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as tmp:
                cutline_path = tmp.name
                # Write bbox geometry as GeoJSON
                cutline_gdf = gpd.GeoDataFrame([{'geometry': bbox_geom}], crs=bbox_reprojected.crs)
                cutline_gdf.to_file(cutline_path, driver='GeoJSON')
            
            try:
                # Ensure output has .tif extension
                if output_path.suffix.lower() not in ['.tif', '.tiff']:
                    output_path = output_path.with_suffix('.tif')
                
                # Use GDAL Warp to crop with cutline
                warp_options = gdal.WarpOptions(
                    format='GTiff',
                    cutlineDSName=cutline_path,
                    cropToCutline=True,
                    creationOptions=['COMPRESS=LZW', 'TILED=YES']
                )
                
                result_ds = gdal.Warp(str(output_path), src_ds, options=warp_options)
                
                if result_ds is None:
                    raise Exception("GDAL Warp failed during crop operation")
                
                # Clean up
                result_ds = None
                
            finally:
                # Remove temporary cutline file
                import os
                if os.path.exists(cutline_path):
                    os.remove(cutline_path)
        
        finally:
            src_ds = None
    
    def validate_inputs(self) -> bool:
        """Validate user inputs before cropping.
        
        Returns:
            True if inputs are valid, False otherwise
        """
        # Check if GIS files are loaded
        if not self.loaded_files:
            QMessageBox.warning(
                self,
                "Validation Error",
                "No GIS files loaded. Please add files to crop."
            )
            return False
        
        # Check if bounding box file is selected
        if not self.bbox_file_path.strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "No bounding box file selected. Please select a bbox file."
            )
            return False
        
        # Check if output directory is specified
        if not self.output_directory.strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "No output directory selected. Please choose an output directory."
            )
            return False
        
        # Check if output directory exists or can be created
        output_dir = Path(self.output_directory)
        if not output_dir.exists():
            if not self._safe_create_directory(str(output_dir)):
                return False
        
        # Validate output directory is writable
        test_file = output_dir / "test_cropped.tif"
        if not self._validate_output_path(str(test_file)):
            return False
        
        return True
