"""
Input validation decorators for SwissArmyKnifeGIS.

Provides reusable decorators for validating function inputs such as paths,
CRS codes, and coordinates.
"""

import logging
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, Any, Optional, Union

from .exceptions import ValidationError, CoordinateError, CRSError, FileOperationError

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def validate_path(
    param_name: str = "path",
    must_exist: bool = False,
    must_be_writable: bool = False,
    create_parents: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to validate file/directory paths.
    
    Args:
        param_name: Name of the path parameter to validate
        must_exist: If True, path must already exist
        must_be_writable: If True, path must be writable
        create_parents: If True, create parent directories if they don't exist
        
    Raises:
        FileOperationError: If path validation fails
        
    Example:
        @validate_path("output_file", must_be_writable=True)
        def save_file(output_file: Path) -> None:
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find the path parameter
            path_value = kwargs.get(param_name)
            
            # For positional args, try to infer from annotations
            if path_value is None:
                annotations = getattr(func, '__annotations__', {})
                param_names = list(annotations.keys())
                if param_name in param_names:
                    idx = param_names.index(param_name)
                    if idx < len(args):
                        path_value = args[idx]
            
            if path_value is not None:
                path_obj = Path(path_value)
                
                # Check existence
                if must_exist and not path_obj.exists():
                    raise FileOperationError(f"Path does not exist: {path_obj}")
                
                # Check writeability
                if must_be_writable:
                    if path_obj.exists():
                        if not path_obj.parent.is_dir():
                            raise FileOperationError(f"Parent directory does not exist: {path_obj.parent}")
                    else:
                        if not path_obj.parent.exists():
                            if not create_parents:
                                raise FileOperationError(f"Parent directory does not exist: {path_obj.parent}")
                
                # Create parents if requested
                if create_parents and not path_obj.parent.exists():
                    try:
                        path_obj.parent.mkdir(parents=True, exist_ok=True)
                    except OSError as e:
                        raise FileOperationError(f"Cannot create parent directory: {e}") from e
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


def validate_coordinates(
    lat_param: str = "latitude",
    lon_param: str = "longitude",
) -> Callable[[F], F]:
    """
    Decorator to validate coordinate values (latitude/longitude).
    
    Args:
        lat_param: Name of latitude parameter
        lon_param: Name of longitude parameter
        
    Raises:
        CoordinateError: If coordinates are out of valid range
        
    Example:
        @validate_coordinates("lat", "lon")
        def transform(lat: float, lon: float) -> None:
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            lat = kwargs.get(lat_param)
            lon = kwargs.get(lon_param)
            
            if lat is not None and not (-90 <= lat <= 90):
                raise CoordinateError(f"Invalid latitude {lat}. Must be between -90 and 90.")
            
            if lon is not None and not (-180 <= lon <= 180):
                raise CoordinateError(f"Invalid longitude {lon}. Must be between -180 and 180.")
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


def validate_crs(param_name: str = "crs") -> Callable[[F], F]:
    """
    Decorator to validate CRS (Coordinate Reference System) values.
    
    Validates that the CRS can be parsed by pyproj.
    
    Args:
        param_name: Name of the CRS parameter to validate
        
    Raises:
        CRSError: If CRS is invalid
        
    Example:
        @validate_crs("crs_code")
        def reproject(crs_code: str) -> None:
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            crs_value = kwargs.get(param_name)
            
            if crs_value is not None:
                try:
                    from pyproj import CRS as ProjCRS
                    ProjCRS.from_string(str(crs_value))
                except Exception as e:
                    raise CRSError(f"Invalid CRS: {crs_value}. Error: {str(e)}") from e
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


def validate_utm_epsg(param_name: str = "epsg_code") -> Callable[[F], F]:
    """
    Decorator to validate UTM EPSG codes.
    
    Args:
        param_name: Name of the EPSG code parameter
        
    Raises:
        CRSError: If EPSG code is not a valid UTM zone
        
    Example:
        @validate_utm_epsg("utm_zone")
        def process_utm(utm_zone: int) -> None:
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            epsg = kwargs.get(param_name)
            
            if epsg is not None:
                if not isinstance(epsg, int):
                    raise CRSError(f"EPSG code must be integer, got {type(epsg).__name__}")
                
                # Valid UTM zones: 32601-32660 (Northern), 32701-32760 (Southern)
                if not ((32601 <= epsg <= 32660) or (32701 <= epsg <= 32760)):
                    raise CRSError(f"Invalid UTM EPSG code: {epsg}. Must be 32601-32660 or 32701-32760.")
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


def validate_not_empty(param_name: str) -> Callable[[F], F]:
    """
    Decorator to validate that a parameter is not empty (list, dict, str, etc).
    
    Args:
        param_name: Name of parameter to validate
        
    Raises:
        ValidationError: If parameter is empty
        
    Example:
        @validate_not_empty("files")
        def process(files: List[str]) -> None:
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            value = kwargs.get(param_name)
            
            if value is not None and len(value) == 0:
                raise ValidationError(f"Parameter '{param_name}' cannot be empty.")
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator
