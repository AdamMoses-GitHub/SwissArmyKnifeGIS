"""GDAL operation utilities with comprehensive error handling.

This module provides safe wrappers around common GDAL operations to ensure:
- Proper error detection and reporting
- Resource cleanup on failure
- User-friendly error messages
- Detailed diagnostic information
"""

from pathlib import Path
from typing import Optional, Union, List
from osgeo import gdal


class GDALOperationError(Exception):
    """Custom exception for GDAL operations with enhanced error context."""
    pass


def safe_gdal_open(
    path: Union[str, Path], 
    mode: int = gdal.GA_ReadOnly
) -> gdal.Dataset:
    """Safely open a GDAL dataset with comprehensive error handling.
    
    Args:
        path: Path to the file to open
        mode: GDAL access mode (GA_ReadOnly or GA_Update)
        
    Returns:
        Opened GDAL dataset
        
    Raises:
        GDALOperationError: If file doesn't exist or GDAL cannot open it
    """
    path = Path(path)
    
    # Check file existence first
    if not path.exists():
        raise GDALOperationError(f"File not found: {path}")
    
    # Check file is readable
    if not path.is_file():
        raise GDALOperationError(f"Path is not a file: {path}")
    
    try:
        ds = gdal.Open(str(path), mode)
        
        if ds is None:
            # GDAL failed to open - get detailed error
            last_error = gdal.GetLastErrorMsg()
            raise GDALOperationError(
                f"GDAL failed to open file: {path}\n"
                f"GDAL Error: {last_error if last_error else 'Unknown error'}"
            )
        
        return ds
        
    except gdal.error as e:
        # GDAL raised an exception
        last_error = gdal.GetLastErrorMsg()
        raise GDALOperationError(
            f"GDAL error opening {path}:\n{str(e)}\n{last_error}"
        ) from e


def safe_gdal_warp(
    src_ds: Union[gdal.Dataset, str, List[Union[gdal.Dataset, str]]],
    output_path: Union[str, Path],
    options: gdal.WarpOptions,
    operation_name: str = "Warp"
) -> gdal.Dataset:
    """Safely execute GDAL Warp with comprehensive error handling.
    
    Args:
        src_ds: Source dataset(s) or path(s)
        output_path: Output file path
        options: GDAL WarpOptions object
        operation_name: Name of operation for error messages
        
    Returns:
        Result dataset
        
    Raises:
        GDALOperationError: If warp operation fails
    """
    output_path = Path(output_path)
    
    try:
        # Execute warp
        result_ds = gdal.Warp(str(output_path), src_ds, options=options)
        
        if result_ds is None:
            # Warp failed - get detailed error
            last_error = gdal.GetLastErrorMsg()
            raise GDALOperationError(
                f"{operation_name} operation failed\n"
                f"Output: {output_path}\n"
                f"GDAL Error: {last_error if last_error else 'Unknown error'}"
            )
        
        return result_ds
        
    except gdal.error as e:
        last_error = gdal.GetLastErrorMsg()
        raise GDALOperationError(
            f"GDAL error during {operation_name}:\n{str(e)}\n{last_error}"
        ) from e


def safe_gdal_buildvrt(
    output_path: Union[str, Path],
    input_files: List[Union[str, Path]],
    options: Optional[gdal.BuildVRTOptions] = None,
    operation_name: str = "BuildVRT"
) -> gdal.Dataset:
    """Safely build a VRT with comprehensive error handling.
    
    Args:
        output_path: Output VRT file path
        input_files: List of input raster files
        options: GDAL BuildVRTOptions object (optional)
        operation_name: Name of operation for error messages
        
    Returns:
        VRT dataset
        
    Raises:
        GDALOperationError: If VRT creation fails
    """
    output_path = Path(output_path)
    
    # Validate inputs exist
    missing_files = []
    for input_file in input_files:
        if not Path(input_file).exists():
            missing_files.append(str(input_file))
    
    if missing_files:
        raise GDALOperationError(
            f"Cannot build VRT: {len(missing_files)} input file(s) not found:\n" +
            "\n".join(f"  - {f}" for f in missing_files[:5]) +
            (f"\n  ... and {len(missing_files) - 5} more" if len(missing_files) > 5 else "")
        )
    
    try:
        # Convert paths to strings
        input_paths = [str(f) for f in input_files]
        
        # Build VRT
        vrt_ds = gdal.BuildVRT(str(output_path), input_paths, options=options)
        
        if vrt_ds is None:
            # VRT creation failed - get detailed error
            last_error = gdal.GetLastErrorMsg()
            raise GDALOperationError(
                f"{operation_name} operation failed\n"
                f"Output: {output_path}\n"
                f"Input files: {len(input_files)}\n"
                f"GDAL Error: {last_error if last_error else 'Unknown error'}"
            )
        
        return vrt_ds
        
    except gdal.error as e:
        last_error = gdal.GetLastErrorMsg()
        raise GDALOperationError(
            f"GDAL error during {operation_name}:\n{str(e)}\n{last_error}"
        ) from e


def safe_gdal_translate(
    src_ds: Union[gdal.Dataset, str],
    output_path: Union[str, Path],
    options: gdal.TranslateOptions,
    operation_name: str = "Translate"
) -> gdal.Dataset:
    """Safely execute GDAL Translate with comprehensive error handling.
    
    Args:
        src_ds: Source dataset or path
        output_path: Output file path
        options: GDAL TranslateOptions object
        operation_name: Name of operation for error messages
        
    Returns:
        Result dataset
        
    Raises:
        GDALOperationError: If translate operation fails
    """
    output_path = Path(output_path)
    
    try:
        # Execute translate
        result_ds = gdal.Translate(str(output_path), src_ds, options=options)
        
        if result_ds is None:
            # Translate failed - get detailed error
            last_error = gdal.GetLastErrorMsg()
            raise GDALOperationError(
                f"{operation_name} operation failed\n"
                f"Output: {output_path}\n"
                f"GDAL Error: {last_error if last_error else 'Unknown error'}"
            )
        
        return result_ds
        
    except gdal.error as e:
        last_error = gdal.GetLastErrorMsg()
        raise GDALOperationError(
            f"GDAL error during {operation_name}:\n{str(e)}\n{last_error}"
        ) from e


def validate_raster_compatibility(
    file_paths: List[Union[str, Path]],
    check_crs: bool = True,
    check_resolution: bool = False,
    check_bands: bool = False
) -> tuple[bool, Optional[str]]:
    """Validate that multiple rasters are compatible for merging/processing.
    
    Args:
        file_paths: List of raster file paths to validate
        check_crs: Whether to check CRS compatibility
        check_resolution: Whether to check resolution compatibility
        check_bands: Whether to check band count compatibility
        
    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if not file_paths:
        return False, "No files provided for validation"
    
    if len(file_paths) < 2:
        return True, None  # Single file is always compatible
    
    try:
        # Open first file as reference
        ref_ds = safe_gdal_open(file_paths[0])
        ref_crs = ref_ds.GetProjection()
        ref_geotransform = ref_ds.GetGeoTransform()
        ref_bands = ref_ds.RasterCount
        
        # Check other files
        for file_path in file_paths[1:]:
            ds = safe_gdal_open(file_path)
            
            if check_crs:
                if ds.GetProjection() != ref_crs:
                    return False, (
                        f"CRS mismatch detected:\n"
                        f"Reference: {Path(file_paths[0]).name}\n"
                        f"Different: {Path(file_path).name}"
                    )
            
            if check_resolution:
                gt = ds.GetGeoTransform()
                if gt[1] != ref_geotransform[1] or gt[5] != ref_geotransform[5]:
                    return False, (
                        f"Resolution mismatch detected:\n"
                        f"Reference: {ref_geotransform[1]} x {abs(ref_geotransform[5])}\n"
                        f"Different: {gt[1]} x {abs(gt[5])} in {Path(file_path).name}"
                    )
            
            if check_bands:
                if ds.RasterCount != ref_bands:
                    return False, (
                        f"Band count mismatch detected:\n"
                        f"Reference: {ref_bands} bands\n"
                        f"Different: {ds.RasterCount} bands in {Path(file_path).name}"
                    )
        
        return True, None
        
    except GDALOperationError as e:
        return False, f"Error validating rasters: {str(e)}"
