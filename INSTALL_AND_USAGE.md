# Installation and Usage Guide

## Features

- **Tabbed Interface**: Organize different GIS tools and workflows in separate tabs
- **Raster Support**: Read, write, and analyze raster data using GDAL and Rasterio
- **Vector Support**: Process vector data with GeoPandas, Shapely, and Fiona
- **Interactive Map Canvas**: Pan, zoom, and visualize GIS layers
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Using Conda (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/swissarmyknifegis.git
cd swissarmyknifegis

# Create and activate conda environment
conda env create -f environment.yml
conda activate swissarmyknifegis

# Install the package in development mode
pip install -e .
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/swissarmyknifegis.git
cd swissarmyknifegis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Usage

### Running the Application

```bash
# As a module
python -m swissarmyknifegis

# Or using the installed command
swissarmyknifegis
```

### Tool Workflows

The application features a tabbed interface with four main tools. Here are common workflows for each:

#### 1. Bounding Box Creator

**Scenario**: You need to define an area of interest for a remote sensing analysis around a city.

Workflow:
1. Open the **Bounding Box Creator** tab
2. Select your coordinate system (WGS84 for global coordinates, UTM for a specific zone)
3. Enter the center point coordinates (latitude/longitude or UTM easting/northing)
4. Specify the dimensions you want (e.g., 10 km × 10 km around your study area)
5. Choose output format(s): KML for Google Earth viewing, Shapefile for GIS software, or GeoJSON for web applications
6. Click "Create Bounding Box" and save your output
7. Use the generated file as an overlay in other tools or in external GIS software

**Example Use Case**: You're planning a field survey in an area 50 km × 50 km around a specific location. Use this tool to create a boundary shapefile that you can share with your team.

#### 2. GIS Cropper

**Scenario**: You have satellite imagery or a large vector dataset that covers a wide area, but you only need a specific region.

Workflow:
1. Open the **GIS Cropper** tab
2. Load the file you want to crop (raster like GeoTIFF, or vector like Shapefile)
3. Either:
   - Draw a bounding box directly on the map canvas, or
   - Load a shapefile/GeoJSON that defines your crop area
4. Analyze the spatial relationship to see what percentage of your file falls within the crop area
5. Click "Crop" to extract only the data within your defined area
6. Save the cropped output in your preferred format
7. The resulting file will be smaller and faster to work with

**Example Use Case**: You downloaded a Landsat scene covering three states, but you only need the portion covering your county. Use the cropper to extract just your area, reducing file size from 2GB to 100MB.

#### 3. Coordinate System Converter

**Scenario**: Your project team uses different coordinate systems—your GIS analyst prefers WGS84, but your engineering team needs UTM Zone 32N.

Workflow:
1. Open the **Coordinate Converter** tab
2. Load your file(s) that need reprojection (supports batch processing multiple files)
3. Select the current coordinate system (if not auto-detected)
4. Choose your target coordinate system from the dropdown (includes common presets like UTM zones, Web Mercator, etc.)
5. For raster files, select your resampling method (nearest neighbor for categorical data, bilinear for continuous)
6. Click "Reproject" to transform your data
7. Save the reprojected file—your coordinates are now in the new system

**Example Use Case**: Your vector data is in EPSG:4326 (WGS84), but you need it in EPSG:32633 (UTM Zone 33N) for accurate distance measurements and area calculations in your region.

#### 4. Raster Merger

**Scenario**: You have multiple satellite tiles or aerial photos covering a larger area that you want to combine into a single seamless image.

Workflow:
1. Open the **Raster Merger** tab
2. Add all the raster files you want to merge (typically 2+ GeoTIFFs covering adjacent areas)
3. The tool analyzes the spatial extent of all files and shows overlap information
4. Configure merge options:
   - Choose how to handle overlapping pixels (average, first file, last file)
   - Set output resolution and data type
   - Select output format (GeoTIFF recommended for analysis)
5. Click "Merge Rasters" to create your composite
6. Save the merged output—you now have a single, seamless image covering the entire region

**Example Use Case**: You purchased four tiles of high-resolution imagery (0.5m resolution) from a drone survey. Use the merger to stitch them together into one orthomosaic that covers your entire 2 km² study site.

## Development

### Project Structure

```
SwissArmyKnifeGIS/
├── src/swissarmyknifegis/
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Entry point (allows python -m swissarmyknifegis)
│   ├── app.py                 # Application initialization and setup
│   ├── gui/
│   │   ├── main_window.py     # Main application window with tab interface
│   │   ├── map_canvas.py      # Interactive map visualization
│   │   └── __init__.py
│   ├── tools/
│   │   ├── base_tool.py       # Base class for all tools
│   │   ├── bbox_creator.py    # Bounding Box Creator tool
│   │   ├── gis_cropper.py     # GIS Cropper tool
│   │   ├── crs_converter.py   # Coordinate System Converter tool
│   │   ├── raster_merger.py   # Raster Merger tool
│   │   └── __init__.py
│   ├── core/
│   │   ├── config_manager.py  # Configuration management
│   │   ├── layer_manager.py   # Layer handling utilities
│   │   ├── cities.py          # City data and lookup
│   │   └── __init__.py
│   ├── resources/
│   │   └── __init__.py        # Place for icons, stylesheets, etc.
│   └── __pycache__/
├── environment.yml            # Conda environment specification
├── pyproject.toml             # Project metadata and dependencies
├── setup.py                   # Installation script
├── README.md                  # Project overview
├── INSTALL_AND_USAGE.md       # This file
├── LICENSE                    # MIT License
└── TODO.md                    # Future features and roadmap
```

**Key Directories Explained**:
- **gui/** - Contains the Qt/PySide6 user interface components including the main window and interactive map
- **tools/** - Each tool is implemented as a class inheriting from `BaseTool`, providing a consistent interface
- **core/** - Shared utilities for configuration, layer management, and data handling
- **resources/** - Reserved for UI resources (icons, stylesheets, images)
- **src/swissarmyknifegis/egg-info/** - Auto-generated by pip during installation

### Running Tests

```bash
pytest
```

### Code Style

This project uses Black for code formatting:

```bash
black src/ tests/
```

## Requirements

- Python >= 3.10
- PySide6 >= 6.6.0
- GDAL >= 3.6.0
- GeoPandas >= 0.14.0
- Rasterio >= 1.3.9
- Shapely >= 2.0.0
- See [environment.yml](environment.yml) for complete list

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
