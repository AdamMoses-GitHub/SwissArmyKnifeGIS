"""
Base class for GIS tool tabs.
"""

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QWidget, QFileDialog
from swissarmyknifegis.core.config_manager import get_config_manager


class QABCMeta(type(QWidget), ABCMeta):
    """Metaclass that combines Qt and ABC metaclasses."""
    pass


class BaseTool(QWidget, metaclass=QABCMeta):
    """
    Abstract base class for tool tabs in SwissArmyKnifeGIS.
    
    All tool implementations should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    @abstractmethod
    def setup_ui(self):
        """
        Set up the user interface for this tool.
        
        This method should create and arrange all UI elements for the tool.
        """
        pass
        
    @abstractmethod
    def get_tool_name(self) -> str:
        """
        Return the display name for this tool.
        
        Returns:
            str: The name to display in the tab.
        """
        pass
        
    def on_activate(self):
        """
        Called when this tool's tab becomes active.
        
        Override this method to perform any setup needed when the tool
        becomes visible.
        """
        pass
        
    def on_deactivate(self):
        """
        Called when this tool's tab becomes inactive.
        
        Override this method to perform any cleanup needed when switching
        away from this tool.
        """
        pass
        
    def validate_inputs(self) -> bool:
        """
        Validate the current tool inputs.
        
        Returns:
            bool: True if inputs are valid, False otherwise.
        """
        return True
        
    def reset(self):
        """
        Reset the tool to its initial state.
        
        Override this method to clear any user inputs or intermediate results.
        """
        pass
    
    def _get_last_path(self, config_key: str, default: Optional[str] = None) -> str:
        """Get the last used path for a specific operation.
        
        Args:
            config_key: Configuration key for the path (e.g., 'input/raster_files')
            default: Default path if no saved path exists
            
        Returns:
            Path string to use as starting directory
        """
        config = get_config_manager()
        return config.get_path(config_key, default)
    
    def _save_last_path(self, config_key: str, path: str):
        """Save the last used path for a specific operation.
        
        Args:
            config_key: Configuration key for the path (e.g., 'input/raster_files')
            path: File or directory path to save
        """
        if not path:
            return
        
        config = get_config_manager()
        
        # If path is a file, save its directory
        path_obj = Path(path)
        if path_obj.is_file():
            path = str(path_obj.parent)
        
        config.set_path(config_key, path)
    
    @staticmethod
    def map_resampling_to_gdal(resampling_name: str) -> int:
        """Map resampling method name to GDAL constant.
        
        Supports common resampling methods used in raster processing.
        
        Args:
            resampling_name: Name of resampling method (e.g., 'bilinear', 'nearest')
            
        Returns:
            GDAL resampling constant. Defaults to GRA_Bilinear if name not found.
        """
        from osgeo import gdalconst
        
        resampling_map = {
            'nearest': gdalconst.GRA_NearestNeighbour,
            'bilinear': gdalconst.GRA_Bilinear,
            'cubic': gdalconst.GRA_Cubic,
            'cubicspline': gdalconst.GRA_CubicSpline,
            'lanczos': gdalconst.GRA_Lanczos,
            'average': gdalconst.GRA_Average,
            'mode': gdalconst.GRA_Mode,
            'max': gdalconst.GRA_Max,
            'min': gdalconst.GRA_Min,
        }
        return resampling_map.get(resampling_name.lower(), gdalconst.GRA_Bilinear)
    
    def _update_status(self, message: str, timeout_ms: int = 5000, permanent: bool = False) -> None:
        """Update the main window status bar with a message.
        
        Safely updates the status bar if the main window has one.
        
        Args:
            message: Message to display in the status bar
            timeout_ms: How long to display the message in milliseconds (ignored if permanent=True)
            permanent: If True, message stays until explicitly cleared
        """
        from PySide6.QtWidgets import QMainWindow
        main_window = self.window()
        if isinstance(main_window, QMainWindow) and main_window.statusBar():
            if permanent:
                main_window.statusBar().showMessage(message)
            else:
                main_window.statusBar().showMessage(message, timeout_ms)
    
    def _clear_status(self) -> None:
        """Clear the status bar message."""
        from PySide6.QtWidgets import QMainWindow
        main_window = self.window()
        if isinstance(main_window, QMainWindow) and main_window.statusBar():
            main_window.statusBar().clearMessage()
    
    @staticmethod
    def sanitize_layer_name(name: str) -> str:
        """Sanitize a name for use as a layer name in GIS formats.
        
        Replaces spaces with underscores and removes special characters
        that may cause issues in layer names.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name safe for use as layer name
        """
        return name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
    
    def _confirm_overwrite(self, file_path: str) -> bool:
        """Ask user for confirmation before overwriting an existing file.
        
        Args:
            file_path: Path to the file that may be overwritten
            
        Returns:
            True if user confirms or file doesn't exist, False otherwise
        """
        from PySide6.QtWidgets import QMessageBox
        
        if not Path(file_path).exists():
            return True
        
        reply = QMessageBox.question(
            self,
            "File Exists",
            f"File already exists:\n{Path(file_path).name}\n\nOverwrite?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        return reply == QMessageBox.Yes
    
    def _safe_create_directory(self, dir_path: str) -> bool:
        """Safely create a directory with comprehensive error handling.
        
        Args:
            dir_path: Path to the directory to create
            
        Returns:
            True if successful, False otherwise (error message shown to user)
        """
        from PySide6.QtWidgets import QMessageBox
        import errno
        
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            return True
            
        except PermissionError:
            QMessageBox.critical(
                self,
                "Permission Denied",
                f"Cannot create directory:\n{dir_path}\n\nCheck folder permissions."
            )
            return False
            
        except OSError as e:
            if e.errno == errno.ENOSPC:
                QMessageBox.critical(
                    self,
                    "Disk Full",
                    "Not enough disk space to create directory."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create directory:\n{str(e)}"
                )
            return False
    
    def _check_disk_space(self, output_path: str, estimated_size_bytes: int) -> bool:
        """Check if enough disk space is available for operation.
        
        Args:
            output_path: Path where output will be written
            estimated_size_bytes: Estimated size of output in bytes
            
        Returns:
            True if sufficient space available, False otherwise
        """
        from PySide6.QtWidgets import QMessageBox
        import shutil
        
        try:
            # Get disk usage statistics
            stat = shutil.disk_usage(Path(output_path).parent)
            
            # Require 20% buffer over estimated size
            required_space = estimated_size_bytes * 1.2
            
            if stat.free < required_space:
                QMessageBox.warning(
                    self,
                    "Insufficient Disk Space",
                    f"Estimated output size: {estimated_size_bytes / (1024**3):.2f} GB\n"
                    f"Available space: {stat.free / (1024**3):.2f} GB\n\n"
                    f"Free up disk space before continuing."
                )
                return False
            
            return True
            
        except Exception as e:
            # If we can't check disk space, allow operation to proceed
            # (better than blocking legitimate operations)
            return True
    
    def _validate_output_path(self, path: str) -> bool:
        """Validate that the output path is writable.
        
        Args:
            path: Output file path to validate
            
        Returns:
            True if path is writable, False otherwise
        """
        from PySide6.QtWidgets import QMessageBox
        
        try:
            # Ensure parent directory exists
            parent = Path(path).parent
            parent.mkdir(parents=True, exist_ok=True)
            
            # Test write access by creating and deleting a test file
            test_file = parent / ".write_test_swissgis"
            test_file.touch()
            test_file.unlink()
            
            return True
            
        except PermissionError:
            QMessageBox.critical(
                self,
                "Permission Denied",
                f"Cannot write to location:\n{path}\n\nCheck folder permissions."
            )
            return False
            
        except OSError as e:
            QMessageBox.critical(
                self,
                "Cannot Write",
                f"Cannot write to:\n{path}\n\n{str(e)}"
            )
            return False
    
    def _display_success(self, message: str):
        """Display a success message in results display (if available).
        
        Args:
            message: Success message to display
        """
        if hasattr(self, 'results_display'):
            self.results_display.append(f"✓ {message}")
    
    def _display_error(self, message: str):
        """Display an error message in results display (if available).
        
        Args:
            message: Error message to display
        """
        if hasattr(self, 'results_display'):
            self.results_display.append(f"✗ {message}")
    
    def _display_warning(self, message: str):
        """Display a warning message in results display (if available).
        
        Args:
            message: Warning message to display
        """
        if hasattr(self, 'results_display'):
            self.results_display.append(f"⚠ {message}")
    
    def _display_info(self, message: str):
        """Display an info message in results display (if available).
        
        Args:
            message: Info message to display
        """
        if hasattr(self, 'results_display'):
            self.results_display.append(f"ℹ {message}")
