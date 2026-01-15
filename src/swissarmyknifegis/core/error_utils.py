"""
Error handling utilities for SwissArmyKnifeGIS.

Provides centralized error logging, exception chaining, and user notification.
"""

import logging
from typing import Optional, Callable
from PySide6.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)


def log_and_notify(
    error: Exception,
    user_message: str,
    parent: Optional[QWidget] = None,
    log_level: int = logging.ERROR,
    show_dialog: bool = True,
    callback: Optional[Callable] = None,
) -> None:
    """
    Log an exception and optionally notify the user.
    
    Handles error logging with proper context and exception chaining,
    while providing user-friendly error messages via dialog or callback.
    
    Args:
        error: The exception that occurred
        user_message: User-friendly message to display
        parent: Parent widget for error dialog (None for no dialog)
        log_level: Logging level (logging.ERROR, WARNING, DEBUG, etc.)
        show_dialog: Whether to show QMessageBox dialog
        callback: Alternative callback for error handling instead of dialog
        
    Example:
        try:
            do_something()
        except ValueError as e:
            log_and_notify(
                e,
                "Failed to process input. Please check your values.",
                parent=self,
                show_dialog=True
            )
    """
    # Log the exception with full traceback
    logger.log(
        log_level,
        f"{user_message} Error: {str(error)}",
        exc_info=True,
    )
    
    # Notify user via callback if provided
    if callback:
        callback(user_message, str(error))
        return
    
    # Show dialog if requested and parent widget available
    if show_dialog and parent:
        message_box_type = {
            logging.ERROR: QMessageBox.Critical,
            logging.WARNING: QMessageBox.Warning,
            logging.INFO: QMessageBox.Information,
            logging.DEBUG: QMessageBox.Information,
        }.get(log_level, QMessageBox.Warning)
        
        title = {
            logging.ERROR: "Error",
            logging.WARNING: "Warning",
            logging.INFO: "Information",
            logging.DEBUG: "Debug",
        }.get(log_level, "Notice")
        
        QMessageBox(
            message_box_type,
            title,
            user_message,
            QMessageBox.Ok,
            parent,
        ).exec()


def safe_operation(
    operation: Callable,
    error_message: str,
    parent: Optional[QWidget] = None,
    default_return=None,
    show_dialog: bool = True,
) -> Optional:
    """
    Execute an operation with automatic error handling.
    
    Args:
        operation: Callable to execute
        error_message: Message to display on error
        parent: Parent widget for error dialog
        default_return: Value to return on exception
        show_dialog: Whether to show error dialog
        
    Returns:
        Result of operation, or default_return on exception
        
    Example:
        result = safe_operation(
            lambda: risky_function(),
            "Operation failed",
            parent=self
        )
    """
    try:
        return operation()
    except Exception as e:
        log_and_notify(
            e,
            error_message,
            parent=parent,
            show_dialog=show_dialog,
        )
        return default_return
