"""
Base class for GIS tool tabs.
"""

from abc import ABCMeta, abstractmethod
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QObject


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
