"""India mainland polygon adapted verbatim from the prototype profiler."""
from __future__ import annotations
import numpy as np
from shapely.geometry import Point, Polygon
from shapely import contains_xy

OUTLINE = [
    [23.9,68.2],[23.2,68.4],[22.4,69.0],[21.6,70.0],[20.9,71.0],[19.9,72.5],[19.0,72.9],
    [18.2,73.2],[17.2,73.4],[16.2,73.6],[15.1,74.1],[14.1,74.5],[13.0,74.7],[12.0,75.3],
    [11.0,75.9],[10.2,76.3],[9.2,76.6],[8.6,77.0],[8.08,77.55],[9.3,78.2],[10.3,79.2],
    [11.4,79.8],[12.4,80.1],[13.1,80.3],[14.2,80.2],[15.3,80.2],[16.3,81.3],[17.2,82.4],
    [18.2,83.5],[19.1,84.7],[20.0,85.8],[20.9,86.8],[21.7,88.3],[22.6,88.6],[23.9,88.1],
    [25.0,88.2],[26.0,88.4],[26.6,89.0],[26.9,89.9],[26.7,90.8],[26.4,92.0],[26.9,93.5],
    [28.0,94.8],[28.4,96.2],[27.4,96.6],[26.9,95.4],[25.9,94.8],[24.7,94.0],[23.5,93.2],
    [22.9,92.5],[23.5,91.4],[24.0,90.5],[24.2,89.5],[24.8,88.9],[25.6,88.5],[26.2,88.2],
    [27.0,88.1],[27.6,88.2],[27.9,88.2],[27.5,87.3],[27.4,85.0],[27.5,83.0],[27.6,81.0],
    [28.3,80.2],[29.2,79.6],[30.1,78.6],[31.0,77.6],[32.1,76.4],[33.0,75.7],[34.0,74.6],
    [34.6,75.6],[35.3,76.6],[35.6,78.0],[34.8,78.6],[34.0,77.6],[33.2,76.4],[32.3,75.6],
    [31.4,75.4],[30.4,74.4],[29.4,73.4],[28.4,72.0],[27.4,70.6],[26.4,69.6],[25.4,69.0],
    [24.4,68.6],
]
# Shapely coordinates are x=longitude, y=latitude.
INDIA_POLY = Polygon([(lon, lat) for lat, lon in OUTLINE])


def point_in_india(lon: float, lat: float) -> bool:
    return bool(INDIA_POLY.covers(Point(float(lon), float(lat))))


def is_mainland(lon: float, lat: float) -> bool:
    return point_in_india(lon, lat)


def india_mask(lons, lats) -> np.ndarray:
    """Vectorised mainland mask; boundary points are accepted."""
    x, y = np.asarray(lons, dtype=float), np.asarray(lats, dtype=float)
    return np.asarray(contains_xy(INDIA_POLY, x, y) | (np.vectorize(point_in_india)(x, y) & ~contains_xy(INDIA_POLY, x, y)))
