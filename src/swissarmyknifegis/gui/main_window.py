"""
Main application window with tabbed interface for GIS tools.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QMessageBox, QPushButton, QComboBox, QLabel
)
from swissarmyknifegis.tools import AboutTab, BoundingBoxCreatorTool, QuadBBoxCreatorTool, GISCropperTool, CoordinateConverterTool, RasterMergerTool
from swissarmyknifegis.core.config_manager import get_config_manager


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwissArmyKnifeGIS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize components
        self.config_manager = get_config_manager()
        self._setup_ui()
        self._create_status_bar()
        self._setup_keyboard_shortcuts()
        
    def _setup_ui(self) -> None:
        """Set up the main UI components."""
        # Create central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for different tools
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setMovable(False)
        layout.addWidget(self.tab_widget)
        
        # Add placeholder for first tab (will be populated when user describes it)
        self._add_placeholder_tab()
        
        # Create bottom button area
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push button to the right
        
        # Add Quit button
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        quit_button.setFixedWidth(100)
        button_layout.addWidget(quit_button)
        
        layout.addLayout(button_layout)
        
    def _add_placeholder_tab(self) -> None:
        """Add tool tabs using registry pattern. The About tab is always added last to remain rightmost."""
        # Registry of tool classes to instantiate
        tool_classes = [
            BoundingBoxCreatorTool,
            QuadBBoxCreatorTool,
            GISCropperTool,
            CoordinateConverterTool,
            RasterMergerTool,
        ]
        
        # Instantiate and add all tools
        self.tools = []
        for tool_class in tool_classes:
            tool = tool_class()
            self.tools.append(tool)
            self.tab_widget.addTab(tool, tool.get_tool_name())
        
        # Add About tab last so it remains as the rightmost tab
        self.about_tab = AboutTab()
        self.tab_widget.addTab(self.about_tab, self.about_tab.get_tool_name())
        
    def _create_status_bar(self) -> None:
        """Create application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard shortcuts for navigation."""
        # Ctrl+Tab to go to next tab
        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self._next_tab)
        
        # Ctrl+Shift+Tab to go to previous tab
        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self._prev_tab)
        
    def _next_tab(self) -> None:
        """Move to the next tab."""
        current = self.tab_widget.currentIndex()
        next_index = (current + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)
        
    def _prev_tab(self) -> None:
        """Move to the previous tab."""
        current = self.tab_widget.currentIndex()
        prev_index = (current - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)
