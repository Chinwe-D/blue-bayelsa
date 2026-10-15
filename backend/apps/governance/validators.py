from django.conf import settings
from django.core.exceptions import ValidationError


def validate_point_in_bounds(point):
    """Reject GPS points outside the configured project area.

    Catches the most common field-data errors: swapped latitude/longitude,
    missing minus signs, and coordinates typed into the wrong column.
    """
    if point is None:
        return
    min_lon, min_lat, max_lon, max_lat = settings.GPS_BOUNDS
    lon, lat = point.x, point.y
    if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
        hint = ""
        if min_lon <= lat <= max_lon and min_lat <= lon <= max_lat:
            hint = " Latitude and longitude appear to be swapped."
        raise ValidationError(
            f"Location ({lat:.5f}, {lon:.5f}) is outside Bayelsa State.{hint}",
            code="out_of_bounds",
        )
