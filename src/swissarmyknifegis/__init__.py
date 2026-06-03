"""
SwissArmyKnifeGIS - A comprehensive GIS toolkit with GUI interface.

This package provides tools for reading, writing, modifying, and analyzing
both raster and vector GIS data.
"""

__version__ = "0.1.1"
__author__ = "SwissArmyKnifeGIS Team"

def run_app() -> None:
	"""Run the GUI application using a lazy import.

	Keeping the import local prevents package import failures in environments
	that only need core utilities (for example, CI test runs).
	"""
	from .app import run_app as _run_app
	_run_app()

__all__ = ["run_app"]
