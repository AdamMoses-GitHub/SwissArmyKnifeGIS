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
        
        # Instantiate and register all tool tabs
        self._initialize_tool_tabs()
        
        # Create bottom button area
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push button to the right
        
        # Add Quit button
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        quit_button.setFixedWidth(100)
        button_layout.addWidget(quit_button)
        
        layout.addLayout(button_layout)
        
    def _initialize_tool_tabs(self) -> None:
        """Register tools and add lightweight placeholder tabs. Each tool is lazily
        instantiated the first time its tab is activated, keeping startup fast."""
        # Registry: (class, display name) — names are hardcoded to avoid eager instantiation.
        self._tool_registry = [
            (BoundingBoxCreatorTool, "BBox - Centroid"),
            (QuadBBoxCreatorTool,    "BBox - Points"),
            (GISCropperTool,         "GIS Cropper"),
            (CoordinateConverterTool, "CRS Converter"),
            (RasterMergerTool,       "Raster Merger"),
        ]
        self._tool_instances: dict = {}
        self._initializing_tab = False

        # Add a lightweight placeholder QWidget for each tool tab.
        # Tabs are added BEFORE connecting currentChanged so these additions
        # do not trigger our lazy-init handler.
        for _, name in self._tool_registry:
            self.tab_widget.addTab(QWidget(), name)

        # About tab is always eager — it is a trivial read-only widget.
        self.about_tab = AboutTab()
        self.tab_widget.addTab(self.about_tab, self.about_tab.get_tool_name())

        # Connect lazy initializer and eagerly init the first tab so the app
        # is immediately usable without a blank placeholder on launch.
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self._on_tab_changed(0)

    def _on_tab_changed(self, index: int) -> None:
        """Lazily instantiate the real tool widget when its tab is activated."""
        if self._initializing_tab or index >= len(self._tool_registry):
            return  # About tab or re-entrant guard
        if index in self._tool_instances:
            return  # Already initialised

        self._initializing_tab = True
        try:
            tool_class, name = self._tool_registry[index]
            tool = tool_class()
            self._tool_instances[index] = tool
            self.tab_widget.removeTab(index)
            self.tab_widget.insertTab(index, tool, name)
            self.tab_widget.setCurrentIndex(index)
        finally:
            self._initializing_tab = False
        
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
