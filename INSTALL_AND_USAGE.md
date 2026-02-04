# Installation and Usage Guide

## Features

- **Dual Bounding Box Tools**: Create bounding boxes from centroid+dimensions OR from four arbitrary corner points
- **Raster Support**: Read, write, crop, and merge raster data using GDAL and Rasterio
- **Vector Support**: Process and crop vector data with GeoPandas, Shapely, and Fiona
- **Batch CRS Conversion**: Reproject multiple raster/vector files between coordinate systems
- **Interactive Map Canvas**: Pan, zoom, and visualize GIS layers in real-time
- **Spatial Analysis**: Analyze overlap percentages and containment relationships
- **Multiple Export Formats**: Output to KML, Shapefile, GeoJSON, or all three at once
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Method A: Using Conda (Recommended)

Conda provides the most reliable installation because GDAL can be tricky to install via pip alone.

```bash
# Clone the repository
git clone https://github.com/AdamMoses-GitHub/SwissArmyKnifeGIS.git
cd SwissArmyKnifeGIS

# Create and activate conda environment
conda env create -f environment.yml
conda activate swissarmyknifegis

# Install the package in development mode
pip install -e .
```

### Method B: Using pip (Quick)

If you already have GDAL installed system-wide or prefer pip:

```bash
# Clone the repository
git clone https://github.com/AdamMoses-GitHub/SwissArmyKnifeGIS.git
cd SwissArmyKnifeGIS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

**Note**: If pip installation fails on GDAL, use Method A (Conda) instead.

## Usage - Execution

Launch the application using either of these methods:

```bash
# Method 1: As a Python module
python -m swissarmyknifegis

# Method 2: Using the installed command (if installed via pip)
swissarmyknifegis
```

The application opens with a tabbed interface containing five GIS tools plus an About tab.

## Usage - Workflows

The application features a tabbed interface with five main tools. Here are common workflows for each:

#### 1. Bounding Box Creator (Centroid-Based)

**Scenario**: You need to define a precise rectangular area of interest around a specific location for downloading satellite imagery.

**Workflow**:
1. Open the **BBox - Centroid** tab
2. Choose your coordinate system: Lon/Lat (WGS84) or UTM
3. Enter centroid coordinates manually OR select from the city dropdown (includes 50+ major world cities)
4. Specify dimensions (width × height) in meters or kilometers
5. Preview the bounding box on the map canvas
6. Select output format(s): KML, Shapefile, GeoJSON, or all three
7. Click "Create Bounding Box" and choose your save location

**Example Use Case**: You're researching urban heat islands in Chicago. Select "Chicago" from the city dropdown, set dimensions to 20 km × 20 km, and export as Shapefile to use as a download boundary for Landsat imagery.

#### 2. 4-Point Bounding Box Creator

**Scenario**: Your study area is not rectangular or you have specific corner coordinates from a survey that define an arbitrary quadrilateral.

**Workflow**:
1. Open the **BBox - Points** tab
2. Select coordinate system (Lon/Lat or UTM with zone specification)
3. Enter coordinates for all four corner points (SW, SE, NE, NW) manually OR select a city to auto-populate approximate bounds
4. The tool automatically creates a polygon connecting these four points
5. Preview the polygon on the interactive map
6. Choose output format(s): KML, Shapefile, GeoJSON
7. Click "Create Bounding Box" to save

**Example Use Case**: You have GPS coordinates from four corner markers placed in the field that define your agricultural study plot. Input these exact coordinates to create a polygon boundary that matches your field layout.

#### 2. GIS Cropper

**Scenario**: You have a massive satellite image or vector dataset covering an entire continent, but you only need data for a small region.

**Workflow**:
1. Open the **GIS Cropper** tab
2. Load the file you want to crop (supports GeoTIFF, TIFF for rasters; Shapefile, GeoJSON for vectors)
3. Define your crop area using ONE of these methods:
   - Draw a bounding box directly on the map canvas (click and drag)
   - Load an existing shapefile or GeoJSON that defines your area of interest
4. Click "Analyze" to see spatial overlap statistics:
   - Percentage of your input file that falls within the crop area
   - Whether the file is fully inside, partially overlapping, or outside the crop region
5. Review the analysis results
6. Click "Crop" to extract only the data within your defined area
7. Choose output location and format

**Example Use Case**: You downloaded a 5 GB Sentinel-2 scene covering three states, but you only need the portion covering your 500 km² national park. Load the scene, draw a box around the park, analyze (shows 3% overlap), crop, and reduce file size to 150 MB.

#### 3. Coordinate System Converter

**Scenario**: Your collaborators use different coordinate systems and you need to reproject your entire dataset to match their requirements.

**Workflow**:
1. Open the **CRS Converter** tab
2. Click "Add Files" to load one or more files (supports batch processing of raster and vector files)
3. The tool auto-detects the current CRS for each file (or you can manually specify if needed)
4. Select the target CRS from the dropdown:
   - Common presets include WGS84, Web Mercator, UTM zones (30N-33N, etc.), NAD83, British National Grid
   - Or enter a custom EPSG code
5. For raster files, choose a resampling method:
   - **Nearest Neighbor**: For categorical data (land cover, classifications)
   - **Bilinear**: For continuous data (elevation, temperature)
   - **Cubic**: Higher quality for imagery
6. (Optional) Configure compression and multithreading options
7. Select output directory
8. Click "Reproject" to transform all files
9. Results display shows success/failure for each file with detailed messages

**Example Use Case**: Your team receives 50 shapefiles in various UTM zones from different field surveys. You need everything in WGS84 (EPSG:4326) for web mapping. Load all 50 files, select WGS84 as target, click Reproject, and the tool processes the entire batch in minutes.

#### 4. Raster Merger

**Scenario**: You have multiple satellite tiles or drone imagery covering adjacent areas that need to be stitched together into a single seamless raster.

**Workflow**:
1. Open the **Raster Merger** tab
2. Click "Add Rasters" to load all files you want to merge (typically 2+ GeoTIFFs covering adjacent or overlapping areas)
3. The tool automatically analyzes:
   - Spatial extent of all input files
   - Overlap regions and percentage
   - CRS consistency (warns if files use different projections)
4. Configure merge options:
   - **Merge Method**: How to handle overlapping pixels:
     - First: Use pixel from first file
     - Last: Use pixel from last file
     - Min/Max: Take minimum/maximum value
     - Sum: Add values together (useful for accumulation)
   - **Output Resolution**: Match input or specify custom resolution
   - **Output Data Type**: uint8, uint16, int16, float32, float64
   - **Compression**: LZW or DEFLATE for smaller file sizes
5. Select output directory and filename
6. Click "Merge Rasters" to create the composite
7. Progress dialog shows merging status
8. Save the merged output—one seamless raster covering the entire region

**Example Use Case**: Your drone survey produced 12 individual GeoTIFF tiles (each 1 GB) covering a 5 km² mining site. Use the merger with "First" method and LZW compression to create a single 8 GB orthomosaic for analysis and visualization.

## Development

### Project Structure

```
SwissArmyKnifeGIS/
├── src/swissarmyknifegis/
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # Entry point (allows python -m swissarmyknifegis)
│   ├── app.py                   # Application initialization and configuration
│   ├── gui/
│   │   ├── main_window.py       # Main window with tabbed interface
│   │   ├── map_canvas.py        # Interactive map visualization
│   │   └── __init__.py
│   ├── tools/
│   │   ├── base_tool.py         # Base class for all tools
│   │   ├── bbox_creator.py      # Bounding Box Creator (centroid-based)
│   │   ├── quad_bbox_creator.py # 4-Point Bounding Box Creator
│   │   ├── gis_cropper.py       # GIS Cropper tool
│   │   ├── crs_converter.py     # Coordinate System Converter
│   │   ├── raster_merger.py     # Raster Merger tool
│   │   ├── about_tab.py         # About tab with project info
│   │   └── __init__.py
│   ├── core/
│   │   ├── config_manager.py    # Configuration persistence
│   │   ├── layer_manager.py     # Layer handling utilities
│   │   ├── coord_utils.py       # Coordinate transformation utilities
│   │   ├── geo_export_utils.py  # Multi-format export functions
│   │   ├── gdal_utils.py        # GDAL helper functions
│   │   ├── cities.py            # Major city database
│   │   ├── validation.py        # Input validation
│   │   ├── error_utils.py       # Error handling utilities
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── __init__.py
│   └── resources/
│       └── __init__.py          # Reserved for icons, stylesheets
├── environment.yml              # Conda environment specification
├── pyproject.toml               # Project metadata and pip dependencies
├── setup.py                     # Installation script (delegates to pyproject.toml)
├── README.md                    # Project overview
├── INSTALL_AND_USAGE.md         # This file
├── LICENSE                      # MIT License
└── TODO.md                      # Future features and roadmap
```
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
- **gui/** - Qt/PySide6 UI components including the main tabbed window and interactive map canvas
- **tools/** - Each tool inherits from `BaseTool` for consistent interface and shared functionality
- **core/** - Shared utilities for coordinate transformations, GDAL operations, config management, and validation
- **resources/** - Reserved for UI assets (icons, stylesheets, images) - currently empty

### Running Tests

```bash
# Activate your environment first
conda activate swissarmyknifegis

# Run tests with pytest
pytest

# Run with coverage report
pytest --cov=swissarmyknifegis
```

### Code Style

This project uses Black for code formatting and Flake8 for linting:

```bash
# Format code
black src/ tests/

# Check code style
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

## Requirements

### Core Dependencies
- **Python** >= 3.10
- **GDAL** >= 3.6.0 (raster/vector I/O and transformations)
- **PySide6** >= 6.6.0 (Qt GUI framework)
- **GeoPandas** >= 0.14.0 (vector data operations)
- **Rasterio** >= 1.3.9 (raster data access)
- **Shapely** >= 2.0.0 (geometric operations)
- **Fiona** >= 1.9.5 (vector file I/O)
- **PyProj** >= 3.6.0 (coordinate transformations)
- **NumPy** >= 1.24.0 (numerical operations)
- **Pandas** >= 2.0.0 (data manipulation)
- **Matplotlib** >= 3.8.0 (visualization)
- **Pillow** >= 10.0.0 (image processing)
- **Rtree** >= 1.1.0 (spatial indexing)

See [environment.yml](environment.yml) or [pyproject.toml](pyproject.toml) for the complete dependency list.

## Troubleshooting

**GDAL installation fails with pip**: Use Conda (Method A) instead. GDAL has complex system dependencies that Conda handles automatically.

**"ModuleNotFoundError: No module named 'osgeo'"**: Your GDAL installation is incomplete. Reinstall using: `conda install -c conda-forge gdal`

**GUI doesn't appear on macOS**: Try running with: `pythonw -m swissarmyknifegis` instead of `python -m swissarmyknifegis`

**Coordinate transformation errors**: Ensure PyProj datum grids are installed: `conda install -c conda-forge proj-data`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
