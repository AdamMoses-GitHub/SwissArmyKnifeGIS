"""
Main application window with tabbed interface for GIS tools.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QStatusBar, QMessageBox, QPushButton
)
from PySide6.QtGui import QAction
from swissarmyknifegis.gui.map_canvas import MapCanvas
from swissarmyknifegis.tools import BoundingBoxCreatorTool, GISCropperTool


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwissArmyKnifeGIS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize components
        self._setup_ui()
        # self._create_menus()  # Commented out - menu bar hidden
        self._create_status_bar()
        
    def _setup_ui(self):
        """Set up the main UI components."""
        # Create central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget for different tools
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
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
        
    def _add_placeholder_tab(self):
        """Add tool tabs."""
        # Add Bounding Box Creator tool
        self.bbox_creator_tool = BoundingBoxCreatorTool()
        self.tab_widget.addTab(self.bbox_creator_tool, self.bbox_creator_tool.get_tool_name())
        
        # Add GIS Cropper tool
        self.gis_cropper_tool = GISCropperTool()
        self.tab_widget.addTab(self.gis_cropper_tool, self.gis_cropper_tool.get_tool_name())
        
    def _create_menus(self):
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        preferences_action = QAction("&Preferences...", self)
        preferences_action.triggered.connect(self._on_preferences)
        edit_menu.addAction(preferences_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self._on_zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self._on_zoom_out)
        view_menu.addAction(zoom_out_action)
        
        zoom_extent_action = QAction("Zoom to &Extent", self)
        zoom_extent_action.setShortcut("Ctrl+E")
        zoom_extent_action.triggered.connect(self._on_zoom_extent)
        view_menu.addAction(zoom_extent_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
        
    def _create_status_bar(self):
        """Create application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    # Menu action handlers
    def _on_open(self):
        """Handle File -> Open action."""
        self.status_bar.showMessage("Open file dialog (to be implemented)")
        
    def _on_save(self):
        """Handle File -> Save action."""
        self.status_bar.showMessage("Save file dialog (to be implemented)")
        
    def _on_preferences(self):
        """Handle Edit -> Preferences action."""
        self.status_bar.showMessage("Preferences dialog (to be implemented)")
        
    def _on_zoom_in(self):
        """Handle View -> Zoom In action."""
        if hasattr(self, 'map_canvas'):
            self.map_canvas.zoom_in()
            
    def _on_zoom_out(self):
        """Handle View -> Zoom Out action."""
        if hasattr(self, 'map_canvas'):
            self.map_canvas.zoom_out()
            
    def _on_zoom_extent(self):
        """Handle View -> Zoom to Extent action."""
        if hasattr(self, 'map_canvas'):
            self.map_canvas.zoom_to_extent()
            
    def _on_about(self):
        """Handle Help -> About action."""
        QMessageBox.about(
            self,
            "About SwissArmyKnifeGIS",
            "<h3>SwissArmyKnifeGIS v0.1.0</h3>"
            "<p>A comprehensive GIS toolkit for working with raster and vector data.</p>"
            "<p>Built with PySide6 and open-source GIS libraries.</p>"
        )
