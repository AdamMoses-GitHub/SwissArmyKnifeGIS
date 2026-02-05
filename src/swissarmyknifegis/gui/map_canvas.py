"""
Map canvas widget for displaying and interacting with GIS data.
"""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent


class MapCanvas(QGraphicsView):
    """
    Custom map canvas widget for displaying GIS data.
    
    Provides pan and zoom functionality using mouse interactions.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create and set up scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Configure view properties
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Set initial scene rect (will be updated when data is loaded)
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        
        # Zoom settings
        self.zoom_factor = 1.15
        self.min_zoom = 0.1
        self.max_zoom = 20.0
        self.current_zoom = 1.0
        
        # Pan settings
        self._is_panning = False
        self._pan_start_pos = QPointF()
        
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel zoom."""
        # Calculate zoom factor based on wheel delta
        if event.angleDelta().y() > 0:
            factor = self.zoom_factor
        else:
            factor = 1.0 / self.zoom_factor
            
        # Apply zoom with limits
        new_zoom = self.current_zoom * factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.scale(factor, factor)
            self.current_zoom = new_zoom
            
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning."""
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning."""
        if self._is_panning:
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            
            # Pan the view
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MiddleButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
    def zoom_in(self) -> None:
        """Zoom in by fixed factor."""
        if self.current_zoom * self.zoom_factor <= self.max_zoom:
            self.scale(self.zoom_factor, self.zoom_factor)
            self.current_zoom *= self.zoom_factor
    
    def zoom_out(self) -> None:
        """Zoom out by fixed factor."""
        if self.current_zoom / self.zoom_factor >= self.min_zoom:
            factor = 1.0 / self.zoom_factor
            self.scale(factor, factor)
            self.current_zoom *= factor
            
    def zoom_to_extent(self) -> None:
        """Zoom to fit all items in the scene."""
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        # Reset zoom level tracking
        self.current_zoom = 1.0
        
    def reset_view(self) -> None:
        """Reset view to default zoom and position."""
        self.resetTransform()
        self.current_zoom = 1.0
        self.centerOn(0, 0)
