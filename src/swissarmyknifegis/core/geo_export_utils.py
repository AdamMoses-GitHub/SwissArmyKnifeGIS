"""Geographic data export utilities for multiple GIS formats.

This module provides functions to export GeoDataFrames to various formats:
- Shapefile (.shp)
- GeoJSON (.geojson)
- KML (.kml)
- KMZ (.kmz - compressed KML)
- GeoPackage (.gpkg)
- GML (.gml)
- MapInfo TAB (.tab)
"""

import zipfile
from pathlib import Path
from typing import List, Dict, Optional
import geopandas as gpd


def sanitize_layer_name(name: str) -> str:
    """Sanitize a name for use as a layer name in GIS formats.
    
    Replaces spaces with underscores and removes special characters.
    
    Args:
        name: Original name
        
    Returns:
        Sanitized name safe for use as layer name
    """
    return name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")


def export_to_shapefile(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    convert_to_wgs84: bool = False
) -> str:
    """Export GeoDataFrame to Shapefile format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .shp extension)
        convert_to_wgs84: If True, convert to WGS84 before export
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    try:
        gdf_export = gdf.to_crs("EPSG:4326") if convert_to_wgs84 else gdf
        gdf_export.to_file(output_path, driver="ESRI Shapefile")
        return str(output_path)
    except Exception as e:
        raise Exception(f"Failed to export Shapefile to {output_path}: {str(e)}") from e


def export_to_geojson(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    convert_to_wgs84: bool = False
) -> str:
    """Export GeoDataFrame to GeoJSON format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .geojson extension)
        convert_to_wgs84: If True, convert to WGS84 before export
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    try:
        gdf_export = gdf.to_crs("EPSG:4326") if convert_to_wgs84 else gdf
        gdf_export.to_file(output_path, driver="GeoJSON")
        return str(output_path)
    except Exception as e:
        raise Exception(f"Failed to export GeoJSON to {output_path}: {str(e)}") from e


def export_to_kml(
    gdf: gpd.GeoDataFrame,
    output_path: Path
) -> str:
    """Export GeoDataFrame to KML format.
    
    KML requires WGS84 coordinates, so conversion is automatic.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .kml extension)
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    try:
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        gdf_wgs84.to_file(output_path, driver="KML")
        return str(output_path)
    except Exception as e:
        raise Exception(f"Failed to export KML to {output_path}: {str(e)}") from e


def export_to_kmz(
    gdf: gpd.GeoDataFrame,
    output_path: Path
) -> str:
    """Export GeoDataFrame to KMZ format (compressed KML).
    
    KMZ is a zipped KML file. WGS84 conversion is automatic.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .kmz extension)
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    temp_kml = output_path.with_suffix('.kml.temp')
    try:
        # Create temporary KML file
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        gdf_wgs84.to_file(temp_kml, driver="KML")
        
        # Compress to KMZ
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            kmz.write(temp_kml, 'doc.kml')
        
        # Remove temporary KML
        temp_kml.unlink()
        
        return str(output_path)
    except Exception as e:
        # Clean up temp file if it exists
        if temp_kml.exists():
            temp_kml.unlink()
        raise Exception(f"Failed to export KMZ to {output_path}: {str(e)}") from e


def export_to_geopackage(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    layer_name: str,
    convert_to_wgs84: bool = False
) -> str:
    """Export GeoDataFrame to GeoPackage format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .gpkg extension)
        layer_name: Name for the layer in the GeoPackage
        convert_to_wgs84: If True, convert to WGS84 before export
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    try:
        gdf_export = gdf.to_crs("EPSG:4326") if convert_to_wgs84 else gdf
        sanitized_name = sanitize_layer_name(layer_name)
        gdf_export.to_file(output_path, driver="GPKG", layer=sanitized_name)
        return str(output_path)
    except Exception as e:
        raise Exception(f"Failed to export GeoPackage to {output_path}: {str(e)}") from e


def export_to_gml(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    convert_to_wgs84: bool = False
) -> str:
    """Export GeoDataFrame to GML format (Geography Markup Language).
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .gml extension)
        convert_to_wgs84: If True, convert to WGS84 before export
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    try:
        gdf_export = gdf.to_crs("EPSG:4326") if convert_to_wgs84 else gdf
        gdf_export.to_file(output_path, driver="GML")
        return str(output_path)
    except Exception as e:
        raise Exception(f"Failed to export GML to {output_path}: {str(e)}") from e


def export_to_mapinfo(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    convert_to_wgs84: bool = False
) -> str:
    """Export GeoDataFrame to MapInfo TAB format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path (with .tab extension)
        convert_to_wgs84: If True, convert to WGS84 before export
        
    Returns:
        Path to exported file
        
    Raises:
        Exception: If export fails
    """
    try:
        gdf_export = gdf.to_crs("EPSG:4326") if convert_to_wgs84 else gdf
        gdf_export.to_file(output_path, driver="MapInfo File")
        return str(output_path)
    except Exception as e:
        raise Exception(f"Failed to export MapInfo TAB to {output_path}: {str(e)}") from e


def export_geodataframe_multi(
    gdf: gpd.GeoDataFrame,
    output_prefix: Path,
    formats: Dict[str, bool],
    layer_name: Optional[str] = None,
    keep_utm: bool = True
) -> List[str]:
    """Export GeoDataFrame to multiple formats based on format selection.
    
    This is the main convenience function for batch export operations.
    
    Args:
        gdf: GeoDataFrame to export
        output_prefix: Path prefix for output files (without extension)
        formats: Dict mapping format name to enabled status, e.g.:
            {'shp': True, 'geojson': True, 'kml': False, 'kmz': True,
             'gpkg': True, 'gml': False, 'tab': False}
        layer_name: Layer name for GeoPackage (will be sanitized)
        keep_utm: If True, keep original CRS for formats that support it;
                  if False, convert to WGS84 for all formats except KML/KMZ
        
    Returns:
        List of successfully exported file paths
        
    Raises:
        Exception: If any export fails
    """
    exported_files = []
    convert_to_wgs84 = not keep_utm
    
    # Use basename as default layer name if not provided
    if layer_name is None:
        layer_name = output_prefix.stem
    
    try:
        # Shapefile
        if formats.get('shp', False) or formats.get('shapefile', False):
            shp_path = output_prefix.with_suffix('.shp')
            exported_files.append(export_to_shapefile(gdf, shp_path, convert_to_wgs84))
        
        # GeoJSON
        if formats.get('geojson', False):
            geojson_path = output_prefix.with_suffix('.geojson')
            exported_files.append(export_to_geojson(gdf, geojson_path, convert_to_wgs84))
        
        # KML (always WGS84)
        if formats.get('kml', False):
            kml_path = output_prefix.with_suffix('.kml')
            exported_files.append(export_to_kml(gdf, kml_path))
        
        # KMZ (always WGS84)
        if formats.get('kmz', False):
            kmz_path = output_prefix.with_suffix('.kmz')
            exported_files.append(export_to_kmz(gdf, kmz_path))
        
        # GeoPackage
        if formats.get('gpkg', False) or formats.get('geopackage', False):
            gpkg_path = output_prefix.with_suffix('.gpkg')
            exported_files.append(export_to_geopackage(gdf, gpkg_path, layer_name, convert_to_wgs84))
        
        # GML
        if formats.get('gml', False):
            gml_path = output_prefix.with_suffix('.gml')
            exported_files.append(export_to_gml(gdf, gml_path, convert_to_wgs84))
        
        # MapInfo TAB
        if formats.get('tab', False) or formats.get('mapinfo', False):
            tab_path = output_prefix.with_suffix('.tab')
            exported_files.append(export_to_mapinfo(gdf, tab_path, convert_to_wgs84))
        
        return exported_files
        
    except Exception as e:
        # Re-raise with context about which format failed
        raise Exception(f"Export failed after {len(exported_files)} successful exports: {str(e)}") from e
