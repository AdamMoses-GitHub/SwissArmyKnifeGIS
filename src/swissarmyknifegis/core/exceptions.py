"""
Custom exception classes for SwissArmyKnifeGIS.

Provides a hierarchy of domain-specific exceptions for consistent error handling
across the application.
"""


class GISError(Exception):
    """Base exception for all GIS-related errors."""
    pass


class ValidationError(GISError):
    """Raised when input validation fails."""
    pass


class GDALError(GISError):
    """Raised when GDAL operations fail."""
    pass


class ExportError(GISError):
    """Raised when exporting GIS data fails."""
    pass


class ConfigError(GISError):
    """Raised when configuration operations fail."""
    pass


class CoordinateError(ValidationError):
    """Raised when coordinate conversion or validation fails."""
    pass


class CRSError(ValidationError):
    """Raised when coordinate reference system operations fail."""
    pass


class FileOperationError(GISError):
    """Raised when file operations fail."""
    pass
