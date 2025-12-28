"""
Main application entry point for SwissArmyKnifeGIS.
"""

import sys
from PySide6.QtWidgets import QApplication
from swissarmyknifegis.gui.main_window import MainWindow


def run_app():
    """Initialize and run the SwissArmyKnifeGIS application."""
    app = QApplication(sys.argv)
    app.setApplicationName("SwissArmyKnifeGIS")
    app.setOrganizationName("SwissArmyKnifeGIS")
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
