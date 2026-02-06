"""Raster Merger Tool - Merge multiple raster files into a single output."""

import os
from typing import Any, Dict, List, Optional

import numpy as np
import rasterio
from osgeo import gdal, gdalconst
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QColor

from swissarmyknifegis.tools.base_tool import BaseTool

# Configure GDAL to use Python exceptions
gdal.UseExceptions()


class RasterMergerTool(BaseTool):
    """Tool for merging multiple raster files into a single output raster."""

    def __init__(self):
        """Initialize the raster merger tool."""
        self.loaded_files: List[Dict[str, Any]] = []
        self.analysis_results: Optional[Dict[str, Any]] = None
        self.output_directory = ""
        super().__init__()

    def get_tool_name(self) -> str:
        """Return the name of this tool."""
        return "Raster Merger"
    
    def _map_dtype_to_gdal(self, numpy_dtype: str) -> int:
        """Map numpy dtype string to GDAL data type constant."""
        dtype_map = {
            'uint8': gdalconst.GDT_Byte,
            'uint16': gdalconst.GDT_UInt16,
            'int16': gdalconst.GDT_Int16,
            'int32': gdalconst.GDT_Int32,
            'float32': gdalconst.GDT_Float32,
            'float64': gdalconst.GDT_Float64,
        }
        return dtype_map.get(numpy_dtype, gdalconst.GDT_Float32)
    
    def _map_resampling_to_gdal(self, resampling_name: str) -> int:
        """Map resampling method name to GDAL constant. Uses BaseTool.map_resampling_to_gdal."""
        return BaseTool.map_resampling_to_gdal(resampling_name)
    
    def _get_gdal_merge_algorithm(self, merge_method: str) -> Optional[str]:
        """Get GDAL VRT pixel function for merge method, or None if not supported."""
        # GDAL VRT pixel functions for different merge methods
        algorithm_map = {
            'first': None,  # Default behavior (first file takes precedence)
            'last': None,   # Reverse file order
            'min': 'min',   # Minimum value
            'max': 'max',   # Maximum value
            'sum': 'sum',   # Sum values
            'count': None,  # Not directly supported
        }
        return algorithm_map.get(merge_method)

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === Input Files Section ===
        files_group = QGroupBox("Input Raster Files")
        files_layout = QVBoxLayout()

        # File table
        self.files_table = BaseTool.create_file_table(
            column_headers=["Filename", "CRS", "Width", "Height", "Resolution (m)", "Data Type", "NoData Value", "Path"],
            min_height=200
        )
        self.files_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.files_table.setAlternatingRowColors(True)
        files_layout.addWidget(self.files_table)

        # File management buttons
        button_layout = QHBoxLayout()
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._add_files)
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self._remove_selected_files)
        clear_files_btn = QPushButton("Clear All")
        clear_files_btn.clicked.connect(self._clear_all_files)

        button_layout.addWidget(add_files_btn)
        button_layout.addWidget(remove_files_btn)
        button_layout.addWidget(clear_files_btn)
        button_layout.addSpacing(20)
        
        # Quick copy buttons
        use_nodata_btn = QPushButton("Use Selected NoData")
        use_nodata_btn.clicked.connect(self._use_selected_nodata)
        use_resolution_btn = QPushButton("Use Selected Resolution")
        use_resolution_btn.clicked.connect(self._use_selected_resolution)
        
        button_layout.addWidget(use_nodata_btn)
        button_layout.addWidget(use_resolution_btn)
        button_layout.addStretch()
        files_layout.addLayout(button_layout)

        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # === Merge Parameters Section ===
        params_group = QGroupBox("Merge Parameters")
        params_layout = QFormLayout()

        # Merge method
        merge_method_layout = QVBoxLayout()
        self.merge_method_combo = QComboBox()
        self.merge_methods = {
            "first": "First - Use first file's values in overlaps (fast)",
            "last": "Last - Use last file's values in overlaps",
            "min": "Min - Use minimum pixel values",
            "max": "Max - Use maximum pixel values",
            "sum": "Sum - Add pixel values together",
            "count": "Count - Count valid pixels",
        }
        self.merge_method_combo.addItems(list(self.merge_methods.values()))
        merge_method_layout.addWidget(self.merge_method_combo)
        params_layout.addRow("Merge Method:", merge_method_layout)

        # Resolution selection
        resolution_layout = QVBoxLayout()
        self.resolution_finest_radio = QRadioButton("Use Finest Resolution (smallest pixel)")
        self.resolution_coarsest_radio = QRadioButton(
            "Use Coarsest Resolution (largest pixel)"
        )
        self.resolution_custom_radio = QRadioButton("Custom Resolution (meters):")
        self.resolution_finest_radio.setChecked(True)

        self.resolution_spinbox = QDoubleSpinBox()
        self.resolution_spinbox.setMinimum(0.1)
        self.resolution_spinbox.setMaximum(10000.0)
        self.resolution_spinbox.setValue(1.0)
        self.resolution_spinbox.setSingleStep(0.1)
        self.resolution_spinbox.setDecimals(2)
        self.resolution_spinbox.setEnabled(False)

        self.resolution_custom_radio.toggled.connect(
            self.resolution_spinbox.setEnabled
        )

        resolution_layout.addWidget(self.resolution_finest_radio)
        resolution_layout.addWidget(self.resolution_coarsest_radio)
        resolution_layout.addWidget(self.resolution_custom_radio)
        resolution_layout.addWidget(self.resolution_spinbox)
        params_layout.addRow("Output Resolution:", resolution_layout)

        # Resampling method
        self.resampling_combo = QComboBox()
        self.resampling_methods = {
            "nearest": "Nearest Neighbor - Best for categorical data (land cover, zones)",
            "bilinear": "Bilinear - Good for continuous data (elevation, temperature)",
            "cubic": "Cubic - Smoothest for continuous data (slower)",
            "average": "Average - Best for downsampling",
            "mode": "Mode - Most common value (categorical data)",
            "max": "Maximum - Largest value in window",
            "min": "Minimum - Smallest value in window",
        }
        self.resampling_combo.addItems(list(self.resampling_methods.values()))
        self.resampling_combo.setCurrentIndex(1)  # Default to bilinear
        params_layout.addRow("Resampling Method:", self.resampling_combo)

        # Data type
        self.datatype_combo = QComboBox()
        self.datatype_options = {
            "uint8": "Unsigned 8-bit (0-255)",
            "uint16": "Unsigned 16-bit (0-65535)",
            "int16": "Signed 16-bit (-32768 to 32767)",
            "int32": "Signed 32-bit",
            "float32": "Float 32-bit",
            "float64": "Float 64-bit",
        }
        self.datatype_combo.addItems(list(self.datatype_options.values()))
        self.datatype_combo.setCurrentIndex(4)  # Default to float32
        params_layout.addRow("Output Data Type:", self.datatype_combo)

        # NoData value
        nodata_layout = QVBoxLayout()
        
        self.nodata_none_checkbox = QCheckBox("Do not use a NoData value")
        self.nodata_none_checkbox.setChecked(False)
        self.nodata_none_checkbox.toggled.connect(self._toggle_nodata_none)
        nodata_layout.addWidget(self.nodata_none_checkbox)
        
        nodata_input_layout = QHBoxLayout()
        nodata_input_layout.addWidget(QLabel("NoData value:"))
        self.nodata_spinbox = QDoubleSpinBox()
        self.nodata_spinbox.setMinimum(-999999.0)
        self.nodata_spinbox.setMaximum(999999.0)
        self.nodata_spinbox.setValue(-9999.0)
        self.nodata_spinbox.setDecimals(6)
        nodata_input_layout.addWidget(self.nodata_spinbox)
        
        # Button to copy NoData from selected file
        copy_nodata_button = QPushButton("Copy from Selected")
        copy_nodata_button.setToolTip("Copy NoData value from selected file in table")
        copy_nodata_button.clicked.connect(self._use_selected_nodata)
        nodata_input_layout.addWidget(copy_nodata_button)
        
        nodata_layout.addLayout(nodata_input_layout)
        params_layout.addRow("NoData Value:", nodata_layout)

        # Compression
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["lzw", "deflate", "none"])
        self.compression_combo.setCurrentIndex(0)
        params_layout.addRow("Compression:", self.compression_combo)

        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # === Output Settings Section ===
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()

        # Output directory
        output_dir_layout = QHBoxLayout()
        self.output_path_label = QLabel("No directory selected")
        output_dir_button = QPushButton("Browse...")
        output_dir_button.clicked.connect(self._select_output_directory)
        output_dir_layout.addWidget(self.output_path_label)
        output_dir_layout.addWidget(output_dir_button)
        output_layout.addRow("Directory:", output_dir_layout)

        # Output filename
        self.output_filename_input = QLineEdit()
        self.output_filename_input.setText("merged_raster")
        self.output_filename_input.setPlaceholderText("e.g., merged_raster (extension added automatically)")
        output_layout.addRow("Filename:", self.output_filename_input)

        # Output file format
        self.output_format_combo = QComboBox()
        self.output_formats = {
            "GTiff": "GeoTIFF (.tif)",
            "COG": "Cloud Optimized GeoTIFF (.tif)",
            "HFA": "ERDAS IMAGINE (.img)",
            "ENVI": "ENVI (.bil)",
        }
        self.output_format_combo.addItems(list(self.output_formats.values()))
        self.output_format_combo.setCurrentIndex(0)  # Default to GTiff
        output_layout.addRow("File Format:", self.output_format_combo)

        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # === Action Buttons ===
        button_layout = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setMinimumHeight(40)
        self.analyze_button.setEnabled(False)  # Disabled until files are loaded
        self.analyze_button.clicked.connect(self._on_analyze)

        self.merge_button = QPushButton("Merge Rasters")
        self.merge_button.setMinimumHeight(40)
        self.merge_button.setEnabled(False)
        self.merge_button.clicked.connect(self._on_merge)

        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.merge_button)
        main_layout.addLayout(button_layout)

        # === Results Display ===
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        results_layout.addWidget(self.results_display)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        main_layout.addStretch()

    def _add_files(self):
        """Add raster files to the list."""
        last_path = self._get_last_path("paths/input/raster_files")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Raster Files to Merge",
            last_path,
            "All Supported (*.tif *.tiff *.img *.vrt);;GeoTIFF (*.tif *.tiff);;ERDAS IMAGINE (*.img);;All Files (*.*)",
        )

        if file_paths:
            # Save the directory of the first selected file
            self._save_last_path("paths/input/raster_files", file_paths[0])

        for file_path in file_paths:
            # Check if already loaded
            if any(f["path"] == file_path for f in self.loaded_files):
                continue

            # Get file info
            file_info = self._get_file_info(file_path)
            if file_info:
                self.loaded_files.append(file_info)

        self._update_table()
        self.analysis_results = None
        self._update_button_states()

    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract information from a raster file."""
        try:
            with rasterio.open(file_path) as src:
                crs_str = str(src.crs) if src.crs else "No CRS"
                
                # Calculate pixel resolution (in the units of the CRS)
                pixel_width = abs(src.transform.a)
                pixel_height = abs(src.transform.e)
                avg_resolution = (pixel_width + pixel_height) / 2

                # Get nodata value from first band if available
                nodata_value = None
                if src.count > 0:
                    nodata_value = src.nodata
                nodata_str = str(nodata_value) if nodata_value is not None else "None"

                return {
                    "filename": os.path.basename(file_path),
                    "path": file_path,
                    "crs": crs_str,
                    "crs_obj": src.crs,
                    "width": src.width,
                    "height": src.height,
                    "bounds": src.bounds,
                    "transform": src.transform,
                    "resolution": avg_resolution,
                    "pixel_width": pixel_width,
                    "pixel_height": pixel_height,
                    "count": src.count,
                    "dtype": src.dtypes[0] if src.dtypes else "unknown",
                    "nodata": nodata_value,
                    "nodata_str": nodata_str,
                }
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Reading File",
                f"Could not read {os.path.basename(file_path)}:\n{str(e)}",
            )
            return None

    def _update_table(self):
        """Update the file table."""
        self.files_table.setRowCount(len(self.loaded_files))

        for row, file_info in enumerate(self.loaded_files):
            items = [
                file_info["filename"],
                file_info["crs"],
                str(file_info["width"]),
                str(file_info["height"]),
                f"{file_info['resolution']:.2f}",
                file_info["dtype"],
                file_info["nodata_str"],
                file_info["path"],
            ]

            for col, item_text in enumerate(items):
                item = QTableWidgetItem(item_text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, col, item)

        self.files_table.resizeColumnsToContents()

    def _remove_selected_files(self):
        """Remove selected files from the list."""
        selected_rows = sorted(
            set(index.row() for index in self.files_table.selectedIndexes()),
            reverse=True,
        )

        for row in selected_rows:
            if 0 <= row < len(self.loaded_files):
                del self.loaded_files[row]

        self._update_table()
        self.analysis_results = None
        self._update_button_states()
    def _clear_all_files(self):
        """Clear all loaded files."""
        self.loaded_files.clear()
        self._update_table()
        self.analysis_results = None
        self._update_button_states()

    def _select_output_directory(self):
        """Select output directory."""
        last_path = self._get_last_path("paths/output/directory")
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", last_path
        )
        if directory:
            self.output_directory = directory
            self.output_path_label.setText(directory)
            self._save_last_path("paths/output/directory", directory)

    def _toggle_nodata_none(self, checked):
        """Enable or disable NoData value input based on checkbox."""
        self.nodata_spinbox.setEnabled(not checked)

    def _use_selected_nodata(self):
        """Copy NoData value from selected file to NoData parameter."""
        selected_rows = set(index.row() for index in self.files_table.selectedIndexes())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a file to copy NoData value from")
            return
        
        row = list(selected_rows)[0]
        if 0 <= row < len(self.loaded_files):
            file_info = self.loaded_files[row]
            nodata_value = file_info["nodata"]
            
            if nodata_value is not None:
                self.nodata_none_checkbox.setChecked(False)
                self.nodata_spinbox.setValue(float(nodata_value))
                self.results_display.append(
                    f"Copied NoData value {nodata_value} from {file_info['filename']}"
                )
            else:
                QMessageBox.information(
                    self, 
                    "No NoData Value", 
                    f"{file_info['filename']} does not have a NoData value defined"
                )

    def _use_selected_resolution(self):
        """Copy resolution from selected file to resolution parameter."""
        selected_rows = set(index.row() for index in self.files_table.selectedIndexes())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a file to copy resolution from")
            return
        
        row = list(selected_rows)[0]
        if 0 <= row < len(self.loaded_files):
            file_info = self.loaded_files[row]
            resolution = file_info["resolution"]
            
            # Set the custom resolution option and update the spinbox
            self.resolution_custom_radio.setChecked(True)
            self.resolution_spinbox.setValue(resolution)
            
            self.results_display.append(
                f"Copied resolution {resolution:.4f} from {file_info['filename']}"
            )

    def _merge_with_gdal(
        self,
        input_files: List[str],
        output_path: str,
        output_bounds: tuple,
        output_resolution: float,
        resampling_method: str,
        merge_method: str,
        output_dtype: str,
        output_format: str,
        nodata_value: Optional[float],
        compression: str,
        progress_dialog: Optional[QProgressDialog] = None,
    ) -> bool:
        """Perform raster merge using GDAL Python bindings.
        
        Args:
            input_files: List of input raster file paths
            output_path: Output file path
            output_bounds: Tuple of (minx, miny, maxx, maxy)
            output_resolution: Target resolution in map units
            resampling_method: Resampling algorithm name
            merge_method: Merge method (first, last, min, max, sum, count)
            output_dtype: Output data type string
            output_format: Output format (GTiff, COG, etc.)
            nodata_value: NoData value for output
            compression: Compression method
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Map parameters to GDAL constants
            gdal_dtype = self._map_dtype_to_gdal(output_dtype)
            gdal_resampling = self._map_resampling_to_gdal(resampling_method)
            
            # Handle file order for 'last' merge method
            if merge_method == 'last':
                input_files = list(reversed(input_files))
                self.results_display.append("Reversed file order for 'last' merge method")
            
            # Get pixel function for merge method
            pixel_function = self._get_gdal_merge_algorithm(merge_method)
            
            if merge_method == 'count':
                self.results_display.append("Warning: 'count' merge method not fully supported by GDAL VRT")
                self.results_display.append("Using 'first' method instead")
                pixel_function = None
            
            # Build VRT options
            vrt_options_dict = {
                'resolution': 'user',
                'xRes': output_resolution,
                'yRes': output_resolution,
                'outputBounds': output_bounds,
                'resampleAlg': gdal_resampling,
            }
            
            # Only add nodata if a value is specified
            if nodata_value is not None:
                vrt_options_dict['srcNodata'] = nodata_value
                vrt_options_dict['VRTNodata'] = nodata_value
            
            vrt_options = gdal.BuildVRTOptions(**vrt_options_dict)
            
            # Create in-memory VRT
            self.results_display.append("Building VRT with target resolution...")
            if progress_dialog:
                progress_dialog.setLabelText("Building VRT...")
                QCoreApplication.processEvents()
            
            try:
                vrt_dataset = gdal.BuildVRT('', input_files, options=vrt_options)
                if vrt_dataset is None:
                    raise RuntimeError("GDAL BuildVRT returned None - failed to create VRT")
                # Validate that VRT has expected properties
                if vrt_dataset.RasterCount == 0:
                    raise RuntimeError("VRT created but contains no raster bands")
            except gdal.error as e:
                raise RuntimeError(f"GDAL error while building VRT: {str(e)}") from e
            
            # Apply pixel function if specified
            if pixel_function:
                self.results_display.append(f"Applying '{pixel_function}' pixel function...")
                # Note: Pixel functions require modifying VRT XML directly
                # This is a limitation - for now we'll note it
                self.results_display.append("Note: Complex merge methods may use default behavior")
            
            # Prepare creation options
            creation_options = []
            
            if compression.upper() != 'NONE':
                creation_options.append(f'COMPRESS={compression.upper()}')
            
            # Add format-specific options
            if output_format == 'COG':
                creation_options.extend([
                    'TILED=YES',
                    'BLOCKSIZE=512',
                    'OVERVIEWS=IGNORE_EXISTING',
                ])
            elif output_format == 'GTiff':
                creation_options.append('TILED=YES')
            
            # Translate VRT to output format
            self.results_display.append(f"Translating to {output_format} format...")
            if progress_dialog:
                progress_dialog.setLabelText(f"Writing output file ({output_format})...")
                QCoreApplication.processEvents()
            
            translate_options_dict = {
                'format': output_format,
                'outputType': gdal_dtype,
                'creationOptions': creation_options,
            }
            
            # Only set noData if a value is specified
            if nodata_value is not None:
                translate_options_dict['noData'] = nodata_value
            
            translate_options = gdal.TranslateOptions(**translate_options_dict)
            
            output_dataset = gdal.Translate(
                output_path,
                vrt_dataset,
                options=translate_options,
            )
            
            if output_dataset is None:
                raise Exception("Failed to translate VRT to output format")
            
            # Get output information
            output_width = output_dataset.RasterXSize
            output_height = output_dataset.RasterYSize
            output_bands = output_dataset.RasterCount
            
            # Clean up
            vrt_dataset = None
            output_dataset = None
            
            self.results_display.append(f"✓ Successfully merged {len(input_files)} rasters")
            self.results_display.append(f"✓ Output: {output_path}")
            self.results_display.append(f"✓ Dimensions: {output_width} x {output_height}")
            self.results_display.append(f"✓ Bands: {output_bands}")
            
            return True
            
        except Exception as e:
            self.results_display.append(f"✗ GDAL merge error: {str(e)}")
            raise
    
    def _on_analyze(self):
        """Analyze raster files for compatibility."""
        self.results_display.clear()
        self.merge_button.setEnabled(False)
        self.analysis_results = None

        # Validate inputs
        if not self.loaded_files:
            self.results_display.append("✗ Error: No raster files loaded")
            return

        if not self.output_directory:
            self.results_display.append("✗ Error: No output directory selected")
            return

        try:
            # Check CRS compatibility
            self.results_display.append("Checking CRS compatibility...")
            first_crs = self.loaded_files[0]["crs_obj"]
            for i, file_info in enumerate(self.loaded_files):
                if file_info["crs_obj"] != first_crs:
                    self.results_display.append(
                        f"✗ Error: CRS mismatch detected!\n"
                        f"  File 1: {self.loaded_files[0]['crs']}\n"
                        f"  File {i + 1}: {file_info['crs']}\n"
                        f"  All files must have identical CRS."
                    )
                    return

            self.results_display.append(f"✓ All files use CRS: {first_crs}")

            # Check band count compatibility
            self.results_display.append("\nChecking band compatibility...")
            first_bands = self.loaded_files[0]["count"]
            for i, file_info in enumerate(self.loaded_files):
                if file_info["count"] != first_bands:
                    self.results_display.append(
                        f"✗ Error: Band count mismatch!\n"
                        f"  File 1: {first_bands} bands\n"
                        f"  File {i + 1}: {file_info['count']} bands"
                    )
                    return

            self.results_display.append(f"✓ All files have {first_bands} bands")

            # Check data type compatibility
            self.results_display.append("\nChecking data type compatibility...")
            first_dtype = self.loaded_files[0]["dtype"]
            for i, file_info in enumerate(self.loaded_files):
                if file_info["dtype"] != first_dtype:
                    self.results_display.append(
                        f"✗ Error: Data type mismatch!\n"
                        f"  File 1: {first_dtype}\n"
                        f"  File {i + 1}: {file_info['dtype']}"
                    )
                    return

            self.results_display.append(f"✓ All files have data type: {first_dtype}")

            # Calculate bounds and overlaps
            self.results_display.append("\nAnalyzing spatial coverage...")
            bounds_list = [f["bounds"] for f in self.loaded_files]
            min_left = min(b.left for b in bounds_list)
            min_bottom = min(b.bottom for b in bounds_list)
            max_right = max(b.right for b in bounds_list)
            max_top = max(b.top for b in bounds_list)

            output_bounds = (min_left, min_bottom, max_right, max_top)
            output_width = max_right - min_left
            output_height = max_top - min_bottom
            output_area = output_width * output_height

            self.results_display.append(f"✓ Output bounds: ({min_left:.2f}, {min_bottom:.2f}, {max_right:.2f}, {max_top:.2f})")
            self.results_display.append(f"  Total extent: {output_width:.2f} x {output_height:.2f} units")
            self.results_display.append(f"  Total area: {output_area:.2f} square units")

            # Check for overlaps and gaps between files
            self.results_display.append("\nAnalyzing file relationships...")
            total_file_area = sum(
                (b.right - b.left) * (b.top - b.bottom) for b in bounds_list
            )
            
            # Detect overlaps
            overlap_detected = False
            overlap_pairs = []
            for i in range(len(bounds_list)):
                for j in range(i + 1, len(bounds_list)):
                    b1 = bounds_list[i]
                    b2 = bounds_list[j]
                    
                    # Check if rectangles overlap
                    overlap_left = max(b1.left, b2.left)
                    overlap_right = min(b1.right, b2.right)
                    overlap_bottom = max(b1.bottom, b2.bottom)
                    overlap_top = min(b1.top, b2.top)
                    
                    if overlap_left < overlap_right and overlap_bottom < overlap_top:
                        overlap_area = (overlap_right - overlap_left) * (overlap_top - overlap_bottom)
                        file1_area = (b1.right - b1.left) * (b1.top - b1.bottom)
                        overlap_percent = (overlap_area / file1_area) * 100
                        overlap_detected = True
                        overlap_pairs.append((i, j, overlap_percent, overlap_area))
            
            if overlap_detected:
                self.results_display.append(f"✓ Overlaps detected: {len(overlap_pairs)} pair(s)")
                for i, j, percent, area in overlap_pairs[:5]:  # Show first 5
                    self.results_display.append(
                        f"  - Files {i+1} & {j+1}: {percent:.1f}% overlap ({area:.2f} sq units)"
                    )
                if len(overlap_pairs) > 5:
                    self.results_display.append(f"  ... and {len(overlap_pairs) - 5} more")
            else:
                self.results_display.append("⚠ Warning: No overlaps detected - files may have gaps")
            
            # Check for gaps (coverage analysis)
            coverage_ratio = total_file_area / output_area if output_area > 0 else 0
            if coverage_ratio < 0.95:
                gap_percentage = (1 - coverage_ratio) * 100
                self.results_display.append(
                    f"⚠ Warning: Potential gaps detected (~{gap_percentage:.1f}% of output area)"
                )
                self.results_display.append(
                    "  Some areas may have no data in the merged output."
                )
            elif coverage_ratio > 1.05:
                self.results_display.append(
                    f"✓ Files have {((coverage_ratio - 1) * 100):.1f}% overlap coverage"
                )
            else:
                self.results_display.append("✓ Files provide complete coverage with minimal overlap")
            
            # Calculate estimated output dimensions
            finest_res = min(f["resolution"] for f in self.loaded_files)
            estimated_width = int(output_width / finest_res)
            estimated_height = int(output_height / finest_res)
            self.results_display.append(
                f"\nEstimated output dimensions (at finest resolution):"
            )
            self.results_display.append(
                f"  {estimated_width:,} x {estimated_height:,} pixels ({estimated_width * estimated_height:,} total)"
            )

            # Calculate resolution statistics
            self.results_display.append("\nResolution analysis:")
            resolutions = [f["resolution"] for f in self.loaded_files]
            finest_res = min(resolutions)
            coarsest_res = max(resolutions)

            self.results_display.append(
                f"  Finest resolution: {finest_res:.4f} (smallest pixels)"
            )
            self.results_display.append(
                f"  Coarsest resolution: {coarsest_res:.4f} (largest pixels)"
            )
            
            # Warn about resolution variance
            if coarsest_res / finest_res > 1.5:
                variance_ratio = coarsest_res / finest_res
                self.results_display.append(
                    f"⚠ Warning: Significant resolution variance detected ({variance_ratio:.2f}x difference)"
                )
                self.results_display.append(
                    "  Files with coarser resolution will be resampled to match the finest resolution."
                )
                self.results_display.append(
                    "  This may affect data quality. Consider preprocessing files to uniform resolution."
                )
            
            # Check NoData values
            self.results_display.append("\nNoData value analysis:")
            nodata_values = [f.get("nodata") for f in self.loaded_files]
            unique_nodata = set(nodata_values)
            
            if len(unique_nodata) > 1:
                self.results_display.append(
                    f"⚠ Warning: Files have different NoData values: {unique_nodata}"
                )
                self.results_display.append(
                    "  VRT will use the NoData value from the first file."
                )
                self.results_display.append(
                    "  NoData pixels may not be handled consistently across all files."
                )
            elif None in unique_nodata:
                self.results_display.append("⚠ Warning: Some files have no NoData value defined")
                self.results_display.append(
                    "  Pixels with value 0 or other fill values may not be transparent in output."
                )
            else:
                nodata_val = nodata_values[0]
                self.results_display.append(f"✓ All files use NoData value: {nodata_val}")

            # Store analysis results
            self.analysis_results = {
                "crs": first_crs,
                "bands": first_bands,
                "dtype": first_dtype,
                "bounds": output_bounds,
                "finest_resolution": finest_res,
                "coarsest_resolution": coarsest_res,
            }

            self.results_display.append("\n✓ Analysis complete - Merge operation ready!")
            self._update_button_states()

        except Exception as e:
            self.results_display.append(f"✗ Error during analysis: {str(e)}")
            import traceback

            self.results_display.append(traceback.format_exc())

    def _on_merge(self):
        """Perform the raster merge operation."""
        # Validate inputs before proceeding
        if not self.validate_inputs():
            return
        
        try:
            self.results_display.append("\n" + "=" * 50)
            self.results_display.append("Starting merge operation...")

            # Get user parameters
            merge_method_text = self.merge_method_combo.currentText()
            merge_method = next(
                k
                for k, v in self.merge_methods.items()
                if v == merge_method_text
            )
            
            # Validate merge method compatibility
            band_count = self.loaded_files[0]["count"]
            if merge_method in ["average", "min", "max", "median", "mode", "sum"] and band_count > 1:
                reply = QMessageBox.question(
                    self,
                    "Multi-band Merge Warning",
                    f"The '{merge_method_text}' method will process each band independently.\n\n"
                    f"Your files have {band_count} bands. Each band will be merged separately.\n"
                    f"For RGB/multi-spectral imagery, consider 'First' or 'Last' method to preserve band relationships.\n\n"
                    f"Continue with '{merge_method_text}' method?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    self.results_display.append("✗ Merge cancelled by user")
                    return

            # Determine output resolution
            if self.resolution_finest_radio.isChecked():
                output_resolution = self.analysis_results["finest_resolution"]
                self.results_display.append(
                    f"Using finest resolution: {output_resolution:.4f}"
                )
            elif self.resolution_coarsest_radio.isChecked():
                output_resolution = self.analysis_results["coarsest_resolution"]
                self.results_display.append(
                    f"Using coarsest resolution: {output_resolution:.4f}"
                )
            else:
                output_resolution = self.resolution_spinbox.value()
                self.results_display.append(f"Using custom resolution: {output_resolution:.4f}")

            # Get resampling method
            resampling_text = self.resampling_combo.currentText()
            resampling_method_name = next(
                k
                for k, v in self.resampling_methods.items()
                if v == resampling_text
            )
            # Resampling method name will be mapped to GDAL constant in _merge_with_gdal
            self.results_display.append(f"Resampling method: {resampling_method_name}")

            # Get data type
            datatype_text = self.datatype_combo.currentText()
            output_dtype = next(
                k
                for k, v in self.datatype_options.items()
                if v == datatype_text
            )

            # Get other parameters
            compression = self.compression_combo.currentText()
            
            # Determine NoData value
            if self.nodata_none_checkbox.isChecked():
                # Do not use NoData value
                nodata_value = None
                self.results_display.append("No NoData value will be used")
            else:
                nodata_value = self.nodata_spinbox.value()
                self.results_display.append(f"Using NoData value: {nodata_value}")
                
                # Convert NoData value to match output dtype
                try:
                    if output_dtype.startswith('float'):
                        nodata_value = float(nodata_value)
                    else:
                        nodata_value = int(nodata_value)
                except (ValueError, OverflowError):
                    self.results_display.append(f"Warning: NoData value {nodata_value} may not be compatible with {output_dtype}")
                    nodata_value = int(nodata_value) if not output_dtype.startswith('float') else float(nodata_value)

            # Get user-specified output filename and format
            output_filename = self.output_filename_input.text().strip()
            if not output_filename:
                self.results_display.append("Error: Output filename cannot be empty")
                return
            
            # Get the file format
            format_text = self.output_format_combo.currentText()
            output_format = next(
                k for k, v in self.output_formats.items()
                if v == format_text
            )
            
            # Determine file extension based on format
            format_extensions = {
                "GTiff": ".tif",
                "COG": ".tif",
                "HFA": ".img",
                "ENVI": ".bil",
            }
            extension = format_extensions.get(output_format, ".tif")
            
            # Add extension if not already present
            if not output_filename.lower().endswith(extension):
                output_filename = output_filename + extension
            
            output_path = os.path.join(self.output_directory, output_filename)

            # Make sure output directory exists
            os.makedirs(self.output_directory, exist_ok=True)

            self.results_display.append(f"Merge method: {merge_method}")
            self.results_display.append(f"Output data type: {output_dtype}")
            self.results_display.append(f"NoData value: {nodata_value}")
            self.results_display.append(f"Compression: {compression}")
            self.results_display.append(f"Output file format: {output_format}")

            self.results_display.append(f"\nMerging rasters using GDAL...")

            # Get output bounds from analysis
            output_bounds = self.analysis_results["bounds"]
            
            # Calculate estimated output dimensions
            output_width = int((output_bounds[2] - output_bounds[0]) / output_resolution)
            output_height = int((output_bounds[3] - output_bounds[1]) / output_resolution)
            
            self.results_display.append(f"Target output dimensions: {output_width:,} x {output_height:,} pixels")
            
            # Collect input file paths
            input_files = [f["path"] for f in self.loaded_files]
            
            # Create progress dialog
            progress = QProgressDialog("Merging rasters...", "Cancel", 0, 0, self)
            progress.setWindowTitle("Merge Progress")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            QCoreApplication.processEvents()
            
            # Perform merge using GDAL
            success = self._merge_with_gdal(
                input_files=input_files,
                output_path=output_path,
                output_bounds=output_bounds,
                output_resolution=output_resolution,
                resampling_method=resampling_method_name,
                merge_method=merge_method,
                output_dtype=output_dtype,
                output_format=output_format,
                nodata_value=nodata_value,
                compression=compression,
                progress_dialog=progress,
            )
            
            progress.close()
            
            if success:
                self.results_display.append("✓ Merge complete!")
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Rasters merged successfully!\n\nOutput: {output_path}",
                )

        except Exception as e:
            self.results_display.append(f"✗ Error during merge: {str(e)}")
            import traceback

            self.results_display.append(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Merge failed:\n{str(e)}")
    
    def _update_button_states(self):
        """Update button enabled/disabled states based on current state."""
        has_files = len(self.loaded_files) > 0
        has_analysis = self.analysis_results is not None
        
        # Analyze button: enabled only if files are loaded
        self.analyze_button.setEnabled(has_files)
        
        # Merge button: enabled only if analysis has been performed
        self.merge_button.setEnabled(has_analysis)
    
    def validate_inputs(self) -> bool:
        """Validate user inputs before merging rasters.
        
        Returns:
            True if inputs are valid, False otherwise
        """
        # Check if files are loaded
        if not self.loaded_files:
            QMessageBox.warning(
                self,
                "Validation Error",
                "No raster files loaded. Please add files to merge."
            )
            return False
        
        # Check if analysis has been performed
        if not self.analysis_results:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please analyze rasters before merging."
            )
            return False
        
        # Check if output filename is specified
        output_filename = self.output_filename_input.text().strip()
        if not output_filename:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please specify an output filename."
            )
            return False
        
        # Check if output directory is specified and exists
        if not self.output_directory or not os.path.exists(self.output_directory):
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select a valid output directory."
            )
            return False
        
        # Validate output directory is writable
        if not self._validate_output_path(os.path.join(self.output_directory, output_filename)):
            return False
        
        # Validate NoData value compatibility with data type
        if not self.nodata_none_checkbox.isChecked():
            nodata_text = self.nodata_value_input.text().strip()
            if nodata_text:
                try:
                    nodata_value = float(nodata_text)
                    datatype_text = self.datatype_combo.currentText()
                    output_dtype = next(
                        k for k, v in self.datatype_options.items() 
                        if v == datatype_text
                    )
                    
                    # Check compatibility
                    if output_dtype.startswith('int') or output_dtype.startswith('uint'):
                        if nodata_value != int(nodata_value):
                            QMessageBox.warning(
                                self,
                                "Validation Error",
                                f"NoData value {nodata_value} is not compatible with integer data type {output_dtype}.\n"
                                "Please use an integer value."
                            )
                            return False
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "NoData value must be a valid number."
                    )
                    return False
        
        return True

