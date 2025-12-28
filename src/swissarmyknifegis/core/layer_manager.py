"""
Layer management for GIS data.
"""

from enum import Enum
from typing import List, Optional
from pathlib import Path


class LayerType(Enum):
    """Enumeration of supported layer types."""
    VECTOR = "vector"
    RASTER = "raster"
    UNKNOWN = "unknown"


class Layer:
    """
    Represents a GIS data layer (vector or raster).
    
    Attributes:
        name: Display name of the layer
        path: File path to the data source
        layer_type: Type of layer (vector or raster)
        visible: Whether the layer is currently visible
        crs: Coordinate reference system (EPSG code or WKT)
    """
    
    def __init__(
        self, 
        name: str, 
        path: Path, 
        layer_type: LayerType,
        crs: Optional[str] = None
    ):
        self.name = name
        self.path = path
        self.layer_type = layer_type
        self.visible = True
        self.crs = crs
        self._data = None  # Placeholder for loaded data
        
    def load_data(self):
        """Load the layer data from file."""
        # To be implemented with GDAL/GeoPandas/Rasterio
        pass
        
    def unload_data(self):
        """Unload the layer data from memory."""
        self._data = None
        
    def get_extent(self):
        """
        Get the spatial extent of this layer.
        
        Returns:
            tuple: (minx, miny, maxx, maxy) or None if not loaded
        """
        # To be implemented
        return None
        
    def __repr__(self):
        return f"Layer(name='{self.name}', type={self.layer_type.value}, visible={self.visible})"


class LayerManager:
    """
    Manages the collection of GIS layers in the application.
    
    Provides methods to add, remove, reorder, and query layers.
    """
    
    def __init__(self):
        self._layers: List[Layer] = []
        
    def add_layer(self, layer: Layer, position: Optional[int] = None):
        """
        Add a layer to the manager.
        
        Args:
            layer: The layer to add
            position: Optional position to insert at (default: append)
        """
        if position is None:
            self._layers.append(layer)
        else:
            self._layers.insert(position, layer)
            
    def remove_layer(self, layer: Layer):
        """Remove a layer from the manager."""
        if layer in self._layers:
            layer.unload_data()
            self._layers.remove(layer)
            
    def remove_layer_by_name(self, name: str):
        """Remove a layer by its name."""
        layer = self.get_layer_by_name(name)
        if layer:
            self.remove_layer(layer)
            
    def get_layer_by_name(self, name: str) -> Optional[Layer]:
        """Get a layer by its name."""
        for layer in self._layers:
            if layer.name == name:
                return layer
        return None
        
    def get_all_layers(self) -> List[Layer]:
        """Get all layers in order."""
        return self._layers.copy()
        
    def get_visible_layers(self) -> List[Layer]:
        """Get only visible layers."""
        return [layer for layer in self._layers if layer.visible]
        
    def get_layers_by_type(self, layer_type: LayerType) -> List[Layer]:
        """Get all layers of a specific type."""
        return [layer for layer in self._layers if layer.layer_type == layer_type]
        
    def move_layer(self, layer: Layer, new_position: int):
        """
        Move a layer to a new position in the stack.
        
        Args:
            layer: The layer to move
            new_position: The new position (0 = bottom)
        """
        if layer in self._layers:
            self._layers.remove(layer)
            self._layers.insert(new_position, layer)
            
    def clear_all(self):
        """Remove all layers."""
        for layer in self._layers:
            layer.unload_data()
        self._layers.clear()
        
    def get_combined_extent(self):
        """
        Get the combined spatial extent of all visible layers.
        
        Returns:
            tuple: (minx, miny, maxx, maxy) or None if no layers
        """
        extents = [layer.get_extent() for layer in self.get_visible_layers()]
        extents = [e for e in extents if e is not None]
        
        if not extents:
            return None
            
        minx = min(e[0] for e in extents)
        miny = min(e[1] for e in extents)
        maxx = max(e[2] for e in extents)
        maxy = max(e[3] for e in extents)
        
        return (minx, miny, maxx, maxy)
        
    def __len__(self):
        return len(self._layers)
        
    def __iter__(self):
        return iter(self._layers)
