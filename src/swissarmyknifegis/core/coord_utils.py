"""Coordinate transformation utilities for GIS operations.

This module provides functions for:
- UTM zone calculations
- EPSG code validation and generation
- Coordinate transformations between CRS
- WGS84 ↔ UTM conversions
"""

from typing import Tuple, Optional
from pyproj import Transformer
from .exceptions import CoordinateError


def calculate_utm_zone(longitude: float) -> int:
    """Calculate UTM zone number from longitude.
    
    Args:
        longitude: Longitude in degrees (-180 to 180)
        
    Returns:
        UTM zone number (1-60)
    """
    return int((longitude + 180) / 6) + 1


def calculate_utm_epsg(longitude: float, latitude: float) -> int:
    """Calculate UTM EPSG code from longitude and latitude.
    
    Args:
        longitude: Longitude in degrees (-180 to 180)
        latitude: Latitude in degrees (-90 to 90)
        
    Returns:
        EPSG code (32601-32660 for Northern hemisphere, 32701-32760 for Southern)
    """
    utm_zone = calculate_utm_zone(longitude)
    
    if latitude >= 0:
        return 32600 + utm_zone  # Northern hemisphere
    else:
        return 32700 + utm_zone  # Southern hemisphere


def validate_utm_epsg(epsg_code: int) -> Tuple[bool, Optional[str]]:
    """Validate if EPSG code is a valid UTM zone.
    
    Args:
        epsg_code: EPSG code to validate
        
    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if (32601 <= epsg_code <= 32660) or (32701 <= epsg_code <= 32760):
        return True, None
    
    return False, (
        "Invalid UTM EPSG code. Valid ranges:\n"
        "Northern Hemisphere: 32601-32660\n"
        "Southern Hemisphere: 32701-32760"
    )


def transform_coordinates(
    x: float,
    y: float,
    source_crs: str,
    target_crs: str,
    always_xy: bool = True
) -> Tuple[float, float]:
    """Transform coordinates between coordinate reference systems.
    
    Args:
        x: X coordinate (easting or longitude)
        y: Y coordinate (northing or latitude)
        source_crs: Source CRS (e.g., "EPSG:4326")
        target_crs: Target CRS (e.g., "EPSG:32633")
        always_xy: Use traditional GIS order (lon, lat) instead of (lat, lon)
        
    Returns:
        Tuple of (transformed_x, transformed_y)
        
    Raises:
        Exception: If transformation fails
    """
    try:
        transformer = Transformer.from_crs(
            source_crs,
            target_crs,
            always_xy=always_xy
        )
        return transformer.transform(x, y)
    except Exception as e:
        raise CoordinateError(
            f"Failed to transform coordinates from {source_crs} to {target_crs}: {str(e)}"
        ) from e


def wgs84_to_utm(
    longitude: float,
    latitude: float
) -> Tuple[float, float, int]:
    """Convert WGS84 coordinates to UTM.
    
    Auto-determines the appropriate UTM zone.
    
    Args:
        longitude: Longitude in degrees
        latitude: Latitude in degrees
        
    Returns:
        Tuple of (utm_easting, utm_northing, epsg_code)
        
    Raises:
        Exception: If transformation fails
    """
    epsg_code = calculate_utm_epsg(longitude, latitude)
    utm_x, utm_y = transform_coordinates(
        longitude,
        latitude,
        "EPSG:4326",
        f"EPSG:{epsg_code}"
    )
    return utm_x, utm_y, epsg_code


def utm_to_wgs84(
    easting: float,
    northing: float,
    epsg_code: int
) -> Tuple[float, float]:
    """Convert UTM coordinates to WGS84.
    
    Args:
        easting: UTM easting in meters
        northing: UTM northing in meters
        epsg_code: UTM zone EPSG code (32601-32660 or 32701-32760)
        
    Returns:
        Tuple of (longitude, latitude)
        
    Raises:
        Exception: If EPSG code is invalid or transformation fails
    """
    is_valid, error_msg = validate_utm_epsg(epsg_code)
    if not is_valid:
        raise ValueError(error_msg)
    
    longitude, latitude = transform_coordinates(
        easting,
        northing,
        f"EPSG:{epsg_code}",
        "EPSG:4326"
    )
    return longitude, latitude
