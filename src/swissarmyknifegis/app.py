"""
Main application entry point for SwissArmyKnifeGIS.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from swissarmyknifegis.gui.main_window import MainWindow
from swissarmyknifegis.core.config_manager import get_config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_app():
    """Initialize and run the SwissArmyKnifeGIS application."""
    app = QApplication(sys.argv)
    app.setApplicationName("SwissArmyKnifeGIS")
    app.setOrganizationName("SwissArmyKnifeGIS")
    
    # Initialize configuration manager
    config = get_config_manager()
    
    # Save configuration on application exit with error handling
    def safe_save_config():
        """Safely save configuration with user notification on failure."""
        try:
            config.save()
            logger.debug("Configuration save initiated")
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.warning(f"Failed to save configuration: {e}", exc_info=True)
            QMessageBox.warning(
                None,
                "Configuration Save Failed",
                f"Failed to save application settings:\n{str(e)}\n\n"
                f"Your preferences may be lost."
            )
    
    app.aboutToQuit.connect(safe_save_config)
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
