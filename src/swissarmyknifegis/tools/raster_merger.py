"""Raster Merger Tool - Merge multiple raster files into a single output."""

import os
from typing import Any, Dict, List, Optional

import numpy as np
import rasterio
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
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from rasterio.merge import merge
from rasterio.transform import Affine
from rasterio.io import MemoryFile
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from swissarmyknifegis.tools.base_tool import BaseTool


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

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === Input Files Section ===
        files_group = QGroupBox("Input Raster Files")
        files_layout = QVBoxLayout()

        # File table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(8)
        self.files_table.setHorizontalHeaderLabels(
            ["Filename", "CRS", "Width", "Height", "Resolution (m)", "Data Type", "NoData Value", "Path"]
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
        
        self.nodata_auto_checkbox = QCheckBox("Use first file's NoData value")
        self.nodata_auto_checkbox.setChecked(True)
        self.nodata_auto_checkbox.toggled.connect(self._toggle_nodata_auto)
        nodata_layout.addWidget(self.nodata_auto_checkbox)
        
        self.nodata_spinbox = QDoubleSpinBox()
        self.nodata_spinbox.setMinimum(-999999.0)
        self.nodata_spinbox.setMaximum(999999.0)
        self.nodata_spinbox.setValue(-9999.0)
        self.nodata_spinbox.setDecimals(6)
        self.nodata_spinbox.setEnabled(False)  # Disabled when auto is checked
        nodata_layout.addWidget(self.nodata_spinbox)
        
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
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Raster Files to Merge",
            "",
            "All Supported (*.tif *.tiff *.img *.vrt);;GeoTIFF (*.tif *.tiff);;ERDAS IMAGINE (*.img);;All Files (*.*)",
        )

        for file_path in file_paths:
            # Check if already loaded
            if any(f["path"] == file_path for f in self.loaded_files):
                continue

            # Get file info
            file_info = self._get_file_info(file_path)
            if file_info:
                self.loaded_files.append(file_info)

        self._update_table()
        self.merge_button.setEnabled(False)  # Reset merge button
        self.analysis_results = None

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
        self.merge_button.setEnabled(False)
        self.analysis_results = None
    def _clear_all_files(self):
        """Clear all loaded files."""
        self.loaded_files.clear()
        self._update_table()
        self.merge_button.setEnabled(False)
        self.analysis_results = None

    def _select_output_directory(self):
        """Select output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", ""
        )
        if directory:
            self.output_directory = directory
            self.output_path_label.setText(directory)

    def _toggle_nodata_auto(self, checked):
        """Enable or disable manual NoData value input."""
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
                self.nodata_auto_checkbox.setChecked(False)
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
            self.merge_button.setEnabled(True)

        except Exception as e:
            self.results_display.append(f"✗ Error during analysis: {str(e)}")
            import traceback

            self.results_display.append(traceback.format_exc())

    def _on_merge(self):
        """Perform the raster merge operation."""
        if self.analysis_results is None:
            QMessageBox.warning(self, "Error", "Please run Analyze first")
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
            if self.nodata_auto_checkbox.isChecked():
                # Use first file's NoData value
                nodata_value = self.loaded_files[0]["nodata"]
                if nodata_value is not None:
                    self.results_display.append(f"Using NoData value from first file: {nodata_value}")
                else:
                    nodata_value = -9999.0
                    self.results_display.append("First file has no NoData value, using default: -9999")
            else:
                nodata_value = self.nodata_spinbox.value()
            
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

            self.results_display.append(f"\nMerging rasters...")

            # Open all source rasters
            src_files = [
                rasterio.open(f["path"]) for f in self.loaded_files
            ]

            try:
                # Perform merge
                mosaic, out_trans = merge(
                    src_files, method=merge_method
                )

                # Get metadata from first file
                out_meta = src_files[0].meta.copy()
                
                # Convert mosaic data to output dtype if different
                if output_dtype != str(mosaic.dtype):
                    self.results_display.append(f"Converting data type from {mosaic.dtype} to {output_dtype}...")
                    # Handle data type conversion carefully
                    if output_dtype.startswith('uint'):
                        # For unsigned types, clip negative values to 0
                        mosaic = np.clip(mosaic, 0, None)
                    mosaic = mosaic.astype(output_dtype)

                # Update output metadata with correct parameters
                out_meta.update(
                    {
                        "driver": output_format,
                        "height": mosaic.shape[1],
                        "width": mosaic.shape[2],
                        "count": mosaic.shape[0],  # Number of bands
                        "transform": out_trans,
                        "dtype": output_dtype,
                        "nodata": nodata_value,
                        "compress": compression,
                    }
                )

                # Write output
                self.results_display.append("Writing output file...")
                with rasterio.open(output_path, "w", **out_meta) as dst:
                    dst.write(mosaic)

                self.results_display.append(f"✓ Successfully merged {len(self.loaded_files)} rasters")
                self.results_display.append(f"✓ Output: {output_path}")
                self.results_display.append(f"✓ Dimensions: {mosaic.shape[2]} x {mosaic.shape[1]}")
                self.results_display.append(f"✓ Bands: {mosaic.shape[0]}")
                self.results_display.append("✓ Merge complete!")

                QMessageBox.information(
                    self,
                    "Success",
                    f"Rasters merged successfully!\n\nOutput: {output_path}",
                )

            finally:
                # Close all source files
                for src in src_files:
                    src.close()

        except Exception as e:
            self.results_display.append(f"✗ Error during merge: {str(e)}")
            import traceback

            self.results_display.append(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Merge failed:\n{str(e)}")
