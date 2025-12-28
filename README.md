# SwissArmyKnifeGIS

A comprehensive GIS toolkit with GUI interface for working with raster and vector geospatial data.

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

Run the application:

```bash
# As a module
python -m swissarmyknifegis

# Or using the installed command
swissarmyknifegis
```

## Development

### Project Structure

```
SwissArmyKnifeGIS/
├── src/swissarmyknifegis/    # Main package
│   ├── gui/                   # GUI components
│   ├── tools/                 # GIS tool implementations
│   ├── core/                  # Core functionality
│   └── resources/             # Icons, stylesheets, etc.
├── tests/                     # Unit tests
├── docs/                      # Documentation
└── examples/                  # Example scripts and data
```

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

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
