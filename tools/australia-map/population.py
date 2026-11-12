"""Add ABS population figures to each Point of Presence.

Writes data/pop_population.json with, per PoP id:
  town      the ABS Significant Urban Area (SUA) the PoP sits in, with its
            Estimated Resident Population (ERP) at 30 June 2025 (preliminary);
            for a PoP outside every SUA, the 2021 Census count of the Urban
            Centre / Locality (UCL) it sits in (from ABS QuickStats)
  ring50    people within 50 km (straight line) of the PoP
  ring150   people within 150 km (straight line) of the PoP
Ring totals sum the ABS Australian Population Grid 2025 (1 km cells, ERP),
counting each cell whose centre lies within the distance.

Usage: python3 population.py [cache_dir]
Needs: openpyxl, pyshp, shapely, tifffile, pyproj, numpy.
"""
import glob, html, json, os, re, sys, urllib.request, zipfile
import numpy as np, openpyxl, pyproj, shapefile, tifffile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, ".abs-cache")
os.makedirs(CACHE, exist_ok=True)
RP = "https://www.abs.gov.au/statistics/people/population/regional-population/2024-25/"
DBF = ("https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/"
       "edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/")
SOURCES = {
    "erp": RP + "32180DS0004_2001-25.xlsx",          # Regional population 2024-25, Table 2: ERP by SUA
    "grid": RP + "GEOTIFF.zip",                       # Australian population grid 2025
    "sua": DBF + "SUA_2021_AUST_GDA2020.zip",         # ASGS Ed. 3 SUA boundaries
    "ucl": DBF + "UCL_2021_AUST_GDA2020_SHP.zip",     # ASGS Ed. 3 UCL boundaries
}

def fetch(key):
    url = SOURCES[key]; path = os.path.join(CACHE, os.path.basename(url))
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as r, open(path, "wb") as f: f.write(r.read())
    if path.endswith(".zip"):
        out = path[:-4]
        if not os.path.isdir(out): zipfile.ZipFile(path).extractall(out)
        return out
    return path

def polygons(folder):
    r = shapefile.Reader(glob.glob(os.path.join(folder, "**", "*.shp"), recursive=True)[0])
    g, rec = [], []
    for sr in r.iterShapeRecords():
        if sr.shape.points: g.append(shape(sr.shape.__geo_interface__)); rec.append(sr.record.as_dict())
    return STRtree(g), g, rec

def containing(index, pt):
    tree, g, rec = index
    return next((rec[i] for i in tree.query(pt) if g[i].contains(pt)), None)

pops = json.load(open(os.path.join(HERE, "data", "pops.json")))["points"]

# SUA ERP at 30 June 2025
ws = openpyxl.load_workbook(fetch("erp"), read_only=True, data_only=True)["Table 2"]
rows = list(ws.iter_rows(values_only=True)); hdr = list(rows[4]); i25 = hdr.index(2025)
erp = {str(r[0]): (r[1], int(r[i25])) for r in rows if r and isinstance(r[0], (int, float))}
sua, ucl = polygons(fetch("sua")), polygons(fetch("ucl"))

# Population grid (EPSG:3577, 1 km cells; geo-reference read from the file)
tif = glob.glob(os.path.join(fetch("grid"), "**", "*.tif"), recursive=True)[0]
page = tifffile.TiffFile(tif).pages[0]
sx, sy = page.tags["ModelPixelScaleTag"].value[:2]; tie = page.tags["ModelTiepointTag"].value
a = page.asarray().astype(np.float64)
rr, cc = np.nonzero(a > 0); val = a[rr, cc]
lon, lat = pyproj.Transformer.from_crs(3577, 4326, always_xy=True).transform(tie[3] + (cc + 0.5) * sx, tie[4] - (rr + 0.5) * sy)

def within(la, lo, km):
    r = np.pi / 180
    d = 12742 * np.arcsin(np.sqrt(np.sin((lat - la) * r / 2) ** 2 + np.cos(la * r) * np.cos(lat * r) * np.sin((lon - lo) * r / 2) ** 2))
    return int(round(val[d <= km].sum()))

out = {"sources": {
    "town_sua": "ABS Regional population 2024-25, Table 2: ERP by Significant Urban Area, 30 June 2025 (preliminary)",
    "town_ucl": "ABS 2021 Census QuickStats, Urban Centre/Locality (all persons)",
    "rings": "ABS Australian population grid 2025 (1 km, ERP 30 June 2025), straight-line distance from the PoP"},
    "pops": {}}
for p in pops:
    pt = Point(p["lng"], p["lat"]); s = containing(sua, pt)
    rec = {"ring50": within(p["lat"], p["lng"], 50), "ring150": within(p["lat"], p["lng"], 150)}
    if s and not str(s["SUA_CODE21"]).endswith("000") and str(s["SUA_CODE21"]) in erp:
        name, n = erp[str(s["SUA_CODE21"])]
        rec["town"] = {"name": name, "population": n, "measure": "ERP 30 June 2025", "kind": "Significant Urban Area"}
    else:
        u = containing(ucl, pt)
        if u:
            q = urllib.request.Request(f"https://www.abs.gov.au/census/find-census-data/quickstats/2021/UCL{u['UCL_CODE21']}", headers={"User-Agent": "Mozilla/5.0"})
            text = html.unescape(re.sub(r"<[^>]+>", " ", urllib.request.urlopen(q).read().decode("utf-8", "replace")))
            m = re.search(r"People\s+([\d,]+)", text)
            if m:
                rec["town"] = {"name": u["UCL_NAME21"], "population": int(m.group(1).replace(",", "")), "measure": "2021 Census", "kind": "Urban Centre/Locality"}
    out["pops"][p["id"]] = rec
    print(f"{p['name']:<28} {rec.get('town', {}).get('name', '-'):<28} {rec.get('town', {}).get('population', ''):>9} {rec['ring50']:>9} {rec['ring150']:>9}")
json.dump(out, open(os.path.join(HERE, "data", "pop_population.json"), "w"), indent=1)
print("wrote data/pop_population.json")
