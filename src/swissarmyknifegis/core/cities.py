"""
City coordinate data for quick location selection.

Provides coordinates for major cities worldwide to facilitate
quick centroid selection in GIS tools.
"""

from typing import Dict, List, Tuple


def get_major_cities() -> Dict[str, Tuple[float, float]]:
    """
    Get coordinates for major cities worldwide.
    
    Returns:
        Dictionary mapping city names to (longitude, latitude) tuples in WGS84.
        Cities are organized with US cities first, then international cities.
    """
    cities = {
        # === United States (Top 20 by population) ===
        "New York, NY, USA": (-74.0060, 40.7128),
        "Los Angeles, CA, USA": (-118.2437, 34.0522),
        "Chicago, IL, USA": (-87.6298, 41.8781),
        "Houston, TX, USA": (-95.3698, 29.7604),
        "Phoenix, AZ, USA": (-112.0740, 33.4484),
        "Philadelphia, PA, USA": (-75.1652, 39.9526),
        "San Antonio, TX, USA": (-98.4936, 29.4241),
        "San Diego, CA, USA": (-117.1611, 32.7157),
        "Dallas, TX, USA": (-96.7970, 32.7767),
        "San Jose, CA, USA": (-121.8863, 37.3382),
        "Austin, TX, USA": (-97.7431, 30.2672),
        "Jacksonville, FL, USA": (-81.6557, 30.3322),
        "Fort Worth, TX, USA": (-97.3308, 32.7555),
        "Columbus, OH, USA": (-82.9988, 39.9612),
        "Charlotte, NC, USA": (-80.8431, 35.2271),
        "San Francisco, CA, USA": (-122.4194, 37.7749),
        "Indianapolis, IN, USA": (-86.1581, 39.7684),
        "Seattle, WA, USA": (-122.3321, 47.6062),
        "Denver, CO, USA": (-104.9903, 39.7392),
        "Washington, DC, USA": (-77.0369, 38.9072),
        
        # === International (Top 20 major cities) ===
        "Tokyo, Japan": (139.6917, 35.6895),
        "Delhi, India": (77.1025, 28.7041),
        "Shanghai, China": (121.4737, 31.2304),
        "São Paulo, Brazil": (-46.6333, -23.5505),
        "Mumbai, India": (72.8777, 19.0760),
        "Beijing, China": (116.4074, 39.9042),
        "Cairo, Egypt": (31.2357, 30.0444),
        "Dhaka, Bangladesh": (90.4125, 23.8103),
        "Mexico City, Mexico": (-99.1332, 19.4326),
        "Osaka, Japan": (135.5022, 34.6937),
        "Karachi, Pakistan": (67.0011, 24.8607),
        "Istanbul, Turkey": (28.9784, 41.0082),
        "Chongqing, China": (106.5516, 29.5630),
        "Buenos Aires, Argentina": (-58.3816, -34.6037),
        "Lagos, Nigeria": (3.3792, 6.5244),
        "Manila, Philippines": (120.9842, 14.5995),
        "Rio de Janeiro, Brazil": (-43.1729, -22.9068),
        "Guangzhou, China": (113.2644, 23.1291),
        "London, United Kingdom": (-0.1276, 51.5074),
        "Paris, France": (2.3522, 48.8566),
    }
    
    return cities


def get_cities_grouped() -> List[Tuple[str, List[Tuple[str, float, float]]]]:
    """
    Get cities grouped by region for organized display.
    
    Returns:
        List of tuples: (region_name, list of (city_name, lon, lat))
    """
    cities = get_major_cities()
    
    # Split into US and international
    us_cities = []
    intl_cities = []
    
    for city, (lon, lat) in cities.items():
        if ", USA" in city:
            us_cities.append((city, lon, lat))
        else:
            intl_cities.append((city, lon, lat))
    
    return [
        ("United States", us_cities),
        ("International", intl_cities)
    ]


def populate_city_combo(combo_widget, placeholder_text: str = "-- Select City --"):
    """
    Populate a QComboBox with major cities organized by region.
    
    This utility function is used by bbox creation tools to provide a consistent
    city selection dropdown interface.
    
    Args:
        combo_widget: QComboBox instance to populate
        placeholder_text: Text for the first (placeholder) item
    """
    cities = get_major_cities()
    
    # Add placeholder item
    combo_widget.addItem(placeholder_text, None)
    
    # Add US cities with separator
    combo_widget.addItem("=== UNITED STATES ===", None)
    for city_name, coords in cities.items():
        if ", USA" in city_name:
            combo_widget.addItem(city_name, coords)
    
    # Add international cities with separator
    combo_widget.addItem("=== INTERNATIONAL ===", None)
    for city_name, coords in cities.items():
        if ", USA" not in city_name:
            combo_widget.addItem(city_name, coords)
