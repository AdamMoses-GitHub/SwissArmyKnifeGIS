"""Configuration Manager - Persistent storage for user preferences and paths."""

import json
import os
from pathlib import Path
from typing import Any, Optional


class ConfigManager:
    """Singleton configuration manager for storing user preferences."""
    
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager."""
        if self._initialized:
            return
            
        self._initialized = True
        self._config: dict = {}
        self._config_dir = Path.home() / ".swissarmyknifegis"
        self._config_file = self._config_dir / "config.json"
        
        # Load existing config or create new one
        self.load()
    
    def load(self):
        """Load configuration from JSON file."""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                # Initialize with default structure
                self._config = {
                    "paths": {
                        "input": {},
                        "output": {},
                        "bbox_creator": {},
                        "raster_merger": {},
                        "crs_converter": {},
                        "gis_cropper": {},
                    },
                    "window": {},
                    "tools": {},
                    "preferences": {},
                }
                self.save()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file: {e}")
            print("Creating new configuration with defaults")
            self._config = {
                "paths": {
                    "input": {},
                    "output": {},
                    "bbox_creator": {},
                    "raster_merger": {},
                    "crs_converter": {},
                    "gis_cropper": {},
                },
                "window": {},
                "tools": {},
                "preferences": {},
            }
    
    def save(self):
        """Save configuration to JSON file."""
        try:
            # Create config directory if it doesn't exist
            self._config_dir.mkdir(parents=True, exist_ok=True)
            
            # Write config file with pretty formatting
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by hierarchical key.
        
        Args:
            key: Hierarchical key using '/' separator (e.g., 'paths/input/raster_files')
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        keys = key.split('/')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by hierarchical key.
        
        Args:
            key: Hierarchical key using '/' separator (e.g., 'paths/input/raster_files')
            value: Value to store
        """
        keys = key.split('/')
        config = self._config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
        
        # Auto-save after setting
        self.save()
    
    def get_path(self, key: str, default: Optional[str] = None) -> str:
        """Get a path from configuration with validation.
        
        Args:
            key: Configuration key for the path
            default: Default path if key doesn't exist or path is invalid
            
        Returns:
            Valid path string or default
        """
        path = self.get(key, default)
        
        if path is None:
            # Return user home directory as ultimate fallback
            return str(Path.home())
        
        # Validate path exists
        path_obj = Path(path)
        if path_obj.exists():
            return str(path)
        
        # If path doesn't exist, try parent directory
        if path_obj.parent.exists():
            return str(path_obj.parent)
        
        # Fall back to default or user home
        if default and Path(default).exists():
            return default
        
        return str(Path.home())
    
    def set_path(self, key: str, path: str):
        """Set a path in configuration.
        
        Args:
            key: Configuration key for the path
            path: Path string to store
        """
        if path:
            # Convert to absolute path and normalize
            abs_path = str(Path(path).resolve())
            self.set(key, abs_path)
    
    def reset(self):
        """Reset configuration to defaults."""
        self._config = {
            "paths": {
                "input": {},
                "output": {},
                "bbox_creator": {},
                "raster_merger": {},
                "crs_converter": {},
                "gis_cropper": {},
            },
            "window": {},
            "tools": {},
            "preferences": {},
        }
        self.save()


# Global singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance.
    
    Returns:
        ConfigManager singleton instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
