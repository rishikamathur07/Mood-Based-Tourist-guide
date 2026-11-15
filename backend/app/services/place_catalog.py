"""Select the trustworthy local catalog when a city has curated Indian data."""

from __future__ import annotations


# The original supplied dataset includes generated worldwide rows. The project
# adds grounded Indian destinations after row 2000; this prevents generated
# Delhi/Jaipur records with implausible prices from entering local itineraries.
CURATED_INDIAN_PLACE_ID_START = 2001


def _place_id_number(place) -> int:
    try:
        return int(place.place_id)
    except (TypeError, ValueError):
        return 0


def uses_curated_indian_catalog(place) -> bool:
    return (
        (getattr(place, "country", "") or "").strip().casefold() == "india"
        and _place_id_number(place) >= CURATED_INDIAN_PLACE_ID_START
    )


def trusted_city_places(places: list) -> list:
    """Prefer curated Indian entries whenever the selected city has them.

    This is a selection rule, not a hidden price adjustment: stop prices and
    the final budget always point to the same stored catalog records.
    """
    curated_indian = [place for place in places if uses_curated_indian_catalog(place)]
    return curated_indian or places
