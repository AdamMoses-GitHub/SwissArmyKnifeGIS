"""
Main application window with tabbed interface for GIS tools.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QMessageBox, QPushButton
)
from swissarmyknifegis.tools import AboutTab, BoundingBoxCreatorTool, QuadBBoxCreatorTool, GISCropperTool, CoordinateConverterTool, RasterMergerTool


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwissArmyKnifeGIS")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize components
        self._setup_ui()
        self._create_status_bar()
        
    def _setup_ui(self) -> None:
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
        
    def _add_placeholder_tab(self) -> None:
        """Add tool tabs. The About tab is always added last to remain rightmost."""
        # Add Bounding Box Creator tool
        self.bbox_creator_tool = BoundingBoxCreatorTool()
        self.tab_widget.addTab(self.bbox_creator_tool, self.bbox_creator_tool.get_tool_name())
        
        # Add 4-Point BBox Creator tool
        self.quad_bbox_creator_tool = QuadBBoxCreatorTool()
        self.tab_widget.addTab(self.quad_bbox_creator_tool, self.quad_bbox_creator_tool.get_tool_name())
        
        # Add GIS Cropper tool
        self.gis_cropper_tool = GISCropperTool()
        self.tab_widget.addTab(self.gis_cropper_tool, self.gis_cropper_tool.get_tool_name())
        
        # Add Coordinate Converter tool
        self.crs_converter_tool = CoordinateConverterTool()
        self.tab_widget.addTab(self.crs_converter_tool, self.crs_converter_tool.get_tool_name())
        
        # Add Raster Merger tool
        self.raster_merger_tool = RasterMergerTool()
        self.tab_widget.addTab(self.raster_merger_tool, self.raster_merger_tool.get_tool_name())
        
        # Add About tab last so it remains as the rightmost tab
        self.about_tab = AboutTab()
        self.tab_widget.addTab(self.about_tab, self.about_tab.get_tool_name())
        
    def _create_status_bar(self) -> None:
        """Create application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
