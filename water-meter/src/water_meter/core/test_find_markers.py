#!/usr/bin/env python3
"""Quick smoketest for find_markers() — run on one image and print results.

Usage:
    .venv/bin/python scripts/water_meter/test_find_markers.py ~/pictures/water_meter/latest.jpg
    .venv/bin/python scripts/water_meter/test_find_markers.py ~/pictures/water_meter/water_meter_20260719_093806.jpg --debug
"""

import argparse
import json
import os
import sys

# Allow running from repo root — add 'scripts' dir to path so 'water_meter' is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # src/

from water_meter.find_markers import find_markers  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoketest find_markers on one image.")
    parser.add_argument("image", help="Path to a water meter image.")
    parser.add_argument("--debug", action="store_true", help="Save debug_markers.jpg overlay.")
    args = parser.parse_args()

    image_path = os.path.expanduser(args.image)
    if not os.path.exists(image_path):
        print(f"ERROR: not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    result = find_markers(image_path, debug=args.debug)
    print(json.dumps(result, indent=2, default=str))

    # Quick summary
    for key in ("dial_center", "needle_pivot", "needle_angle", "odometer_roi"):
        val = result.get(key)
        if val:
            print(f"  {key}: {val}")
        else:
            print(f"  {key}: NOT FOUND")


if __name__ == "__main__":
    main()