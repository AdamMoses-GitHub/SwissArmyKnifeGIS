"""Tests for validation decorators."""

from pathlib import Path

import pytest

from swissarmyknifegis.core.exceptions import CoordinateError, ValidationError
from swissarmyknifegis.core.validation import (
    validate_coordinates,
    validate_not_empty,
    validate_path,
)


class DecoratorFixture:
    @validate_coordinates("lat", "lon")
    def process_coords(self, lat: float, lon: float) -> tuple[float, float]:
        return lat, lon

    @validate_not_empty("items")
    def process_items(self, items: list[str]) -> int:
        return len(items)

    @validate_path("output_file", must_be_writable=True, create_parents=True)
    def process_output_path(self, output_file: Path) -> Path:
        return output_file


def test_validate_coordinates_with_positional_method_args() -> None:
    subject = DecoratorFixture()
    assert subject.process_coords(40.0, -73.0) == (40.0, -73.0)


def test_validate_coordinates_rejects_invalid_latitude() -> None:
    subject = DecoratorFixture()
    with pytest.raises(CoordinateError):
        subject.process_coords(120.0, -73.0)


def test_validate_not_empty_with_positional_method_args() -> None:
    subject = DecoratorFixture()
    assert subject.process_items(["a", "b"]) == 2

    with pytest.raises(ValidationError):
        subject.process_items([])


def test_validate_path_create_parents_for_missing_directory(tmp_path: Path) -> None:
    subject = DecoratorFixture()
    target_path = tmp_path / "nested" / "output.geojson"
    returned_path = subject.process_output_path(target_path)

    assert returned_path == target_path
    assert target_path.parent.exists()
