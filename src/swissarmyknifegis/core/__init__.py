"""
Core functionality for SwissArmyKnifeGIS.
"""

from .layer_manager import LayerManager, Layer, LayerType
from .exceptions import (
    GISError,
    ValidationError,
    GDALError,
    ExportError,
    ConfigError,
    CoordinateError,
    CRSError,
    FileOperationError,
)
from .error_utils import log_and_notify, safe_operation

__all__ = [
    "LayerManager",
    "Layer",
    "LayerType",
    "GISError",
    "ValidationError",
    "GDALError",
    "ExportError",
    "ConfigError",
    "CoordinateError",
    "CRSError",
    "FileOperationError",
    "log_and_notify",
    "safe_operation",
]
