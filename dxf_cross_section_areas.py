"""
Calculate cross-sectional areas from a series of DXF files containing open polylines.

Each polyline is treated as a cross section: it is closed by connecting the
leftmost and rightmost endpoints (i.e. the two ends of the profile), forming a
polygon. The signed area is computed with the shoelace formula.

Supports both LWPOLYLINE (2D) and POLYLINE (2D/3D) entities.
"""

from pathlib import Path
import argparse

try:
    import ezdxf
except ImportError:
    raise ImportError("Please install ezdxf: pip install ezdxf")


def shoelace_area_2d(points):
    """
    Compute signed area of a 2D polygon using the shoelace formula.
    Points must be in order (e.g. along the polyline then back to start).
    Returns positive area for counter-clockwise, negative for clockwise.
    """
    if len(points) < 3:
        return 0.0
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return 0.5 * area


def get_polyline_points_2d(entity):
    """
    Extract 2D (x, y) points from a LWPOLYLINE or POLYLINE entity.
    For 3D polylines, uses (x, y); for LWPOLYLINE uses (x, y) in OCS with elevation.
    """
    points = []
    if entity.dxftype() == "LWPOLYLINE":
        # vertices_in_wcs() returns Vec3(x, y, z); we use (x, y) for cross-section area
        for v in entity.vertices_in_wcs():
            points.append((v.x, v.y))
    elif entity.dxftype() == "POLYLINE":
        for vertex in entity.vertices:
            loc = vertex.dxf.location
            points.append((loc.x, loc.y))
    return points


def polyline_to_closed_polygon_points(entity):
    """
    Get 2D points for the polyline and close it (first point = left/right end,
    last point = other end; closing connects them into a polygon).
    If the polyline is already closed, returns points as-is (no duplicate end).
    """
    points = get_polyline_points_2d(entity)
    if not points:
        return []
    # If already closed in DXF, don't add closing segment
    if entity.dxftype() == "LWPOLYLINE" and entity.is_closed:
        return points
    if entity.dxftype() == "POLYLINE" and entity.is_closed:
        return points
    # Open polyline: close by connecting ends (leftmost–rightmost)
    points.append(points[0])
    return points


def area_of_entity(entity):
    """Return the absolute area of one polyline entity (closed as described)."""
    points = polyline_to_closed_polygon_points(entity)
    if len(points) < 3:
        return 0.0
    return abs(shoelace_area_2d(points))


def process_dxf_file(path):
    """
    Read one DXF file and return areas for each polyline (LWPOLYLINE and POLYLINE).
    Returns list of (entity_index, area) and total area.
    """
    path = Path(path)
    if not path.suffix.lower() == ".dxf":
        return None
    try:
        doc = ezdxf.readfile(path)
    except Exception as e:
        return {"error": str(e), "path": str(path)}

    msp = doc.modelspace()
    results = []
    total_area = 0.0

    # Query both polyline types
    for entity in msp.query("LWPOLYLINE"):
        a = area_of_entity(entity)
        results.append(("LWPOLYLINE", a))
        total_area += a

    for entity in msp.query("POLYLINE"):
        a = area_of_entity(entity)
        results.append(("POLYLINE", a))
        total_area += a

    return {
        "path": str(path),
        "name": path.name,
        "areas": results,
        "total_area": total_area,
        "count": len(results),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute cross-sectional areas from DXF files (open polylines closed by connecting endpoints)."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=str,
        help="DXF file paths or a single directory to search for *.dxf",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Print a CSV summary (filename, area_per_polyline, total_area).",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="When a single input is a directory, search recursively for DXF files.",
    )
    args = parser.parse_args()

    # Resolve inputs to a list of DXF files
    dxf_files = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_file():
            if p.suffix.lower() == ".dxf":
                dxf_files.append(p)
        elif p.is_dir():
            pattern = "**/*.dxf" if args.recursive else "*.dxf"
            dxf_files.extend(sorted(p.glob(pattern)))

    if not dxf_files:
        print("No DXF files found.")
        return

    all_results = []
    for path in dxf_files:
        out = process_dxf_file(path)
        if out is None:
            continue
        if "error" in out:
            print(f"Error reading {out['path']}: {out['error']}")
            continue
        all_results.append(out)

    # Report
    if args.csv:
        print("filename,total_area")
        for r in all_results:
            print(f"{r['name']},{r['total_area']}")
        return

    for r in all_results:
        print(f"\n{r['path']}")
        print(f"  Polylines: {r['count']}, Total area: {r['total_area']}")
        for i, (etype, area) in enumerate(r["areas"]):
            print(f"    [{i+1}] {etype}: area = {area}")

    # Optional: one-line summary per file
    print("\n--- Summary ---")
    for r in all_results:
        print(f"  {r['name']}: total_area = {r['total_area']}")


if __name__ == "__main__":
    main()
