"""Tests for coordinate utility helpers."""

from swissarmyknifegis.core.coord_utils import (
    calculate_utm_zone,
    calculate_utm_epsg,
    validate_utm_epsg,
    transform_coordinates,
    wgs84_to_utm,
    utm_to_wgs84,
)


def test_calculate_utm_zone_bounds() -> None:
    assert calculate_utm_zone(-180.0) == 1
    assert calculate_utm_zone(179.9) == 60


def test_calculate_utm_epsg_hemisphere() -> None:
    assert calculate_utm_epsg(-73.0, 40.0) == 32618
    assert calculate_utm_epsg(-73.0, -40.0) == 32718


def test_validate_utm_epsg_ranges() -> None:
    assert validate_utm_epsg(32633) == (True, None)
    is_valid, message = validate_utm_epsg(30000)
    assert not is_valid
    assert message is not None


def test_transform_coordinates_identity() -> None:
    lon, lat = -73.9857, 40.7484
    out_lon, out_lat = transform_coordinates(lon, lat, "EPSG:4326", "EPSG:4326")
    assert abs(out_lon - lon) < 1e-12
    assert abs(out_lat - lat) < 1e-12


def test_wgs84_utm_roundtrip() -> None:
    lon, lat = -73.9857, 40.7484
    easting, northing, epsg = wgs84_to_utm(lon, lat)
    lon_back, lat_back = utm_to_wgs84(easting, northing, epsg)

    assert abs(lon_back - lon) < 1e-5
    assert abs(lat_back - lat) < 1e-5
