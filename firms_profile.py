"""
AGNIVANI / SIH 2026 - PS 26162
Profiles a NASA FIRMS VIIRS CSV: strips non-India detections, finds persistent
thermal source candidates, and flags flare-like (nighttime, repeating) emitters.

Usage:
    python firms_profile.py firms_india.csv

Outputs (next to the input file):
    <name>_clean.csv          India-polygon-filtered detections
    <name>_persistent.csv     ~2km cells seen on 2+ distinct days, scored
"""

import csv
import math
import statistics
import sys
from collections import defaultdict

# ---- Simplified India mainland outline (lat, lon). Excludes Sri Lanka. ----
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
POLY = [(lon, lat) for lat, lon in OUTLINE]

# ---- Known Indian industrial sites (name, lat, lon) ----
FACILITIES = [
    ("Jamnagar Refinery",22.35,70.02),("Vadinar Refinery",22.56,69.73),("Kandla Port",23.00,70.22),
    ("Hazira LNG/Steel",21.13,72.64),("Dahej LNG",21.71,72.58),("Mumbai High/Uran",18.88,72.95),
    ("Panipat Refinery",29.39,76.97),("Mathura Refinery",27.59,77.68),("Bathinda Refinery",30.21,75.00),
    ("Barauni Refinery",25.44,86.05),("Bongaigaon Refinery",26.48,90.56),("Numaligarh Refinery",26.60,93.78),
    ("Guwahati Refinery",26.18,91.75),("Digboi Oil Field",27.39,95.62),("Duliajan Oil Field",27.36,95.32),
    ("Naharkatiya Field",27.28,95.38),("Bokaro Steel",23.67,86.15),("Jharia Coalfield",23.75,86.42),
    ("Jamshedpur Steel",22.80,86.20),("Rourkela Steel",22.25,84.88),("Bhilai Steel",21.19,81.35),
    ("Korba Thermal",22.36,82.68),("Singrauli Coal",24.20,82.67),("Vindhyachal Thermal",24.09,82.67),
    ("Talcher Coalfield",20.95,85.23),("Paradip Refinery",20.31,86.61),("Visakhapatnam",17.70,83.20),
    ("Ramagundam Thermal",18.76,79.45),("Manali Refinery",13.23,80.33),("Neyveli Lignite",11.60,79.48),
    ("Cauvery Basin",10.77,79.84),("Mangalore Refinery",12.96,74.80),("Kochi Refinery",10.00,76.28),
    ("Tuticorin Thermal",8.76,78.13),("Durgapur Steel",23.52,87.31),("IISCO Burnpur",23.67,86.94),
    ("Ankleshwar Ind.",21.63,72.98),("Vapi Ind.",20.37,72.90),
]

CELL_DEG = 0.02  # ~2 km


def point_in_india(lon: float, lat: float) -> bool:
    """Ray-casting point-in-polygon against the India outline."""
    inside = False
    n = len(POLY)
    j = n - 1
    for i in range(n):
        xi, yi = POLY[i]
        xj, yj = POLY[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def nearest_facility(lat: float, lon: float):
    """Returns (name, distance_km) to the closest known industrial site."""
    best, best_d = None, float("inf")
    for name, flat, flon in FACILITIES:
        dy = (lat - flat) * 111.0
        dx = (lon - flon) * 111.0 * math.cos(math.radians(lat))
        d = math.hypot(dx, dy)
        if d < best_d:
            best, best_d = name, d
    return best, best_d


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["latitude"] = float(r["latitude"])
        r["longitude"] = float(r["longitude"])
        r["bright_ti4"] = float(r["bright_ti4"])
        r["bright_ti5"] = float(r["bright_ti5"])
        r["frp"] = float(r["frp"])
    return rows


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    stem = src[:-4] if src.lower().endswith(".csv") else src

    rows = load(src)
    dates = sorted({r["acq_date"] for r in rows})
    print(f"loaded {len(rows)} rows from {src}")
    print(f"date range: {dates[0]} .. {dates[-1]}  ({len(dates)} distinct days)")
    for d in dates:
        print(f"   {d}  {sum(1 for r in rows if r['acq_date'] == d):5d}")

    india = [r for r in rows if point_in_india(r["longitude"], r["latitude"])]
    print(f"\ninside India polygon : {len(india)}")
    print(f"outside (Sri Lanka / neighbours / sea): {len(rows) - len(india)}")

    with open(f"{stem}_clean.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(india)
    print(f"wrote {stem}_clean.csv")

    # ---- persistent source detection ----
    cells = defaultdict(list)
    for r in india:
        key = (round(r["latitude"] / CELL_DEG) * CELL_DEG,
               round(r["longitude"] / CELL_DEG) * CELL_DEG)
        cells[key].append(r)

    persistent = {k: v for k, v in cells.items() if len({x["acq_date"] for x in v}) >= 2}
    print(f"\ngrid cells: {len(cells)}   persistent (2+ distinct days): {len(persistent)}")

    scored = []
    for (lat, lon), hits in persistent.items():
        days = len({x["acq_date"] for x in hits})
        nights = sum(1 for x in hits if x["daynight"] == "N")
        t4 = [x["bright_ti4"] for x in hits]
        t5 = [x["bright_ti5"] for x in hits]
        frp = [x["frp"] for x in hits]
        name, dist = nearest_facility(lat, lon)
        # flare-likeness: repeats across days, fires at night, steady radiance
        steadiness = 1.0 / (1.0 + statistics.pstdev(t4)) if len(t4) > 1 else 0.0
        score = (days * 2.0) + (nights * 1.5) + (steadiness * 10) + min(max(frp) / 10.0, 5.0)
        scored.append({
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "hits": len(hits), "days": days, "night_hits": nights,
            "median_ti4": round(statistics.median(t4), 2),
            "median_ti5": round(statistics.median(t5), 2),
            "max_frp": round(max(frp), 2), "mean_frp": round(statistics.mean(frp), 2),
            "stdev_ti4": round(statistics.pstdev(t4), 2) if len(t4) > 1 else 0.0,
            "nearest_facility": name, "facility_km": round(dist, 1),
            "flare_score": round(score, 2),
        })

    scored.sort(key=lambda r: -r["flare_score"])
    fields = list(scored[0].keys()) if scored else []
    with open(f"{stem}_persistent.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(scored)
    print(f"wrote {stem}_persistent.csv")

    print("\ntop persistent source candidates (flare_score = repeats + night + steadiness + power):")
    hdr = f"{'lat':>7} {'lon':>7} {'hits':>4} {'days':>4} {'night':>5} {'maxFRP':>6} {'medT4':>6} {'score':>6}  nearest"
    print(hdr)
    print("-" * len(hdr) + "-------")
    for r in scored[:15]:
        print(f"{r['latitude']:>7.2f} {r['longitude']:>7.2f} {r['hits']:>4} {r['days']:>4} "
              f"{r['night_hits']:>5} {r['max_frp']:>6.1f} {r['median_ti4']:>6.1f} {r['flare_score']:>6.1f}  "
              f"{r['nearest_facility']} ({r['facility_km']:.0f} km)")


if __name__ == "__main__":
    main()
