"""
About Tab - Displays information about SwissArmyKnifeGIS application.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QGroupBox, QTextEdit
)

from swissarmyknifegis.tools.base_tool import BaseTool
from swissarmyknifegis import __version__


class AboutTab(BaseTool):
    """
    About tab displaying project information and application overview.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def get_tool_name(self) -> str:
        """Return the display name for this tool."""
        return "About"
        
    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)
        
        # About the Project section
        about_group = QGroupBox("About This Project")
        about_layout = QVBoxLayout(about_group)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setText(
            f"SwissArmyKnifeGIS v{__version__}\n\n"
            "Hi, I'm Adam Moses. I got tired of wrestling with expensive GIS software "
            "and complicated command-line tools just to do basic geospatial tasks. "
            "So I built SwissArmyKnifeGIS—a no-nonsense toolkit that handles the common stuff: "
            "cropping rasters, converting coordinates, merging imagery, and managing layers "
            "without making you take a semester-long course first.\n\n"
            "The goal is simple: make GIS accessible. Whether you're a seasoned analyst or just "
            "need to reproject some shapefiles, this tool should get you there without the headache.\n\n"
            "Project Repository: https://github.com/AdamMoses-GitHub/SwissArmyKnifeGIS"
        )
        about_layout.addWidget(about_text)
        main_layout.addWidget(about_group)
        
        # Application Overview section
        overview_group = QGroupBox("Application Overview")
        overview_layout = QVBoxLayout(overview_group)
        
        overview_text = QTextEdit()
        overview_text.setReadOnly(True)
        overview_text.setText(
            "SwissArmyKnifeGIS is a lightweight, user-friendly GIS toolkit with a clean GUI "
            "for working with raster and vector geospatial data.\n\n"
            
            "KEY FEATURES:\n"
            "• Tabbed Interface - Keep your workflows organized without drowning in windows\n"
            "• Raster Tools - Crop, merge, and analyze raster data (GeoTIFF, TIFF, etc.)\n"
            "• Vector Support - Work with shapefiles, GeoJSON, and other vector formats\n"
            "• CRS Converter - Transform coordinates between any projection\n"
            "• Interactive Map Canvas - Pan, zoom, and actually see what you're working with\n"
            "• Cross-Platform - Works on Windows, macOS, and Linux\n\n"
            
            "TOOLS INCLUDED:\n"
            "1. Bounding Box Creator - Define areas of interest for spatial analysis\n"
            "2. GIS Cropper - Extract specific regions from large datasets\n"
            "3. Coordinate System Converter - Reproject data between coordinate systems\n"
            "4. Raster Merger - Stitch multiple tiles together into seamless imagery\n\n"
            
            "BUILT ON PROVEN TECHNOLOGY:\n"
            "• GDAL - Industry standard for raster/vector I/O\n"
            "• GeoPandas - Spatial data analysis with Python\n"
            "• Rasterio - Simple, Pythonic raster data access\n"
            "• PySide6 - Powerful Qt GUI framework\n"
            "• Shapely - Robust geometric operations\n\n"
            
            "For detailed usage instructions and workflows, see INSTALL_AND_USAGE.md"
        )
        overview_layout.addWidget(overview_text)
        main_layout.addWidget(overview_group)
        
        main_layout.addStretch()
