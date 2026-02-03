"""
Main application window with tabbed interface for GIS tools.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
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
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(False)
        layout.addWidget(self.tab_widget)
        
        # Add placeholder for first tab (will be populated when user describes it)
        self._add_placeholder_tab()
        
        # Create toolbar area with recent files
        toolbar_layout = QHBoxLayout()
        
        recent_label = QLabel("Recent Files:")
        toolbar_layout.addWidget(recent_label)
        
        self.recent_files_combo = QComboBox()
        self.recent_files_combo.setMaximumWidth(300)
        self.recent_files_combo.addItem("(None)")
        self.recent_files_combo.currentTextChanged.connect(self._on_recent_file_selected)
        toolbar_layout.addWidget(self.recent_files_combo)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Load recent files
        self._load_recent_files()
        
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
        
    def _load_recent_files(self) -> None:
        """Load recent files from configuration."""
        recent_files = self.config_manager.get('preferences/recent_files', default=[])
        # Remove duplicates and keep order
        seen = set()
        unique_files = []
        for f in recent_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)
        
        # Update combo box
        self.recent_files_combo.blockSignals(True)
        self.recent_files_combo.clear()
        self.recent_files_combo.addItem("(None)")
        for file_path in unique_files[:10]:  # Show last 10 files
            self.recent_files_combo.addItem(file_path)
        self.recent_files_combo.blockSignals(False)
        
    def _on_recent_file_selected(self, file_path: str) -> None:
        """Handle selection of a recent file from the combo box."""
        if file_path and file_path != "(None)":
            self.status_bar.showMessage(f"Selected: {file_path}")
            
    def add_recent_file(self, file_path: str) -> None:
        """Add a file to the recent files list and save to config.
        
        Args:
            file_path: The path of the file to add to recent files.
        """
        recent_files = self.config_manager.get('preferences/recent_files', default=[])
        
        # Move to front if already exists, otherwise add to front
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        
        # Keep only last 20 files
        recent_files = recent_files[:20]
        
        # Save to config
        self.config_manager.set('preferences/recent_files', recent_files)
        self.config_manager.save()
        
        # Update UI
        self._load_recent_files()
