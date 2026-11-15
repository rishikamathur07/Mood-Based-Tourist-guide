"""Checks that curated local data wins over older synthetic rows."""

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.place_catalog import trusted_city_places


def main():
    older_row = SimpleNamespace(country="India", place_id="101", name="Generated Delhi Place")
    curated_row = SimpleNamespace(country="India", place_id="2001", name="India Gate")

    selected = trusted_city_places([older_row, curated_row])
    assert selected == [curated_row]

    overseas_row = SimpleNamespace(country="Japan", place_id="101", name="Imported Tokyo Place")
    assert trusted_city_places([overseas_row]) == [overseas_row]
    print("PASS catalog selection: curated Indian pricing data is preferred")


if __name__ == "__main__":
    main()
