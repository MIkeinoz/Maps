"""Build the self-contained Australia Pin Map page.

Outputs:
  ../../index.html                 full HTML document (site home page)
  --fragment PATH (optional)       page fragment for publishing as a Claude artifact

Refresh the Points of Presence from the quoting plugin's master list with
  --pops path/to/points_of_presence.yaml   (needs PyYAML; rewrites data/pops.json)
"""
import argparse, base64, glob, io, json, math, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")

ap = argparse.ArgumentParser()
ap.add_argument("--fragment")
ap.add_argument("--pops")
args = ap.parse_args()

POP_FIELDS = ["id", "name", "region", "state", "postcode", "lat", "lng",
              "casual_level", "sla_committed_bh", "sla_stretch", "stretch_condition"]
if args.pops:
    import yaml
    src = yaml.safe_load(open(args.pops))
    meta = src.get("metadata", {})
    pops = {"version": meta.get("version"), "effective_date": str(meta.get("effective_date", "")),
            "metro_km": meta.get("metro_threshold_road_km", 50), "regional_km": meta.get("regional_threshold_road_km", 150),
            "points": [{k: x.get(k) for k in POP_FIELDS} for x in src["points_of_presence"]]}
    json.dump(pops, open(os.path.join(D, "pops.json"), "w"), indent=1)
    print("refreshed data/pops.json:", len(pops["points"]), "PoPs, version", pops["version"])
pops = json.load(open(os.path.join(D, "pops.json")))

CODES = {"Western Australia": "WA", "Northern Territory": "NT", "South Australia": "SA", "Queensland": "QLD",
         "New South Wales": "NSW", "Victoria": "VIC", "Tasmania": "TAS", "Australian Capital Territory": "ACT"}
CAPITALS = {"Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Hobart", "Darwin", "Canberra"}

states = json.load(open(os.path.join(D, "aus_states.json")))
for f in states["features"]:
    f["properties"]["code"] = CODES.get(f["properties"]["name"], "")

def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[2], a[1], b[2], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

cities = []
for c in json.load(open(os.path.join(D, "cities.json"))):  # sorted by population, largest first
    if any(km(c, k) < 45 for k in cities):
        continue  # drop suburbs that sit on top of a bigger city
    cities.append(c)
cities = [c + [1 if c[0] in CAPITALS else 0] for c in cities]

dem = {}
for f in sorted(glob.glob(os.path.join(D, "dem", "*.png"))):
    dem[os.path.basename(f)[:-4]] = base64.b64encode(open(f, "rb").read()).decode()

buf = io.BytesIO()  # sea-level terrarium tile: 128*256 - 32768 = 0 m
Image.new("RGB", (256, 256), (128, 0, 0)).save(buf, "PNG", optimize=True)
flat = base64.b64encode(buf.getvalue()).decode()

page = open(os.path.join(HERE, "template.html")).read()
page = (page.replace("/*__MAPLIBRE_CSS__*/", open(os.path.join(D, "maplibre-gl.css")).read())
            .replace("/*__STATES__*/", json.dumps(states, separators=(",", ":")))
            .replace("/*__CITIES__*/", json.dumps(cities, separators=(",", ":")))
            .replace("/*__DEM__*/", json.dumps(dem, separators=(",", ":")))
            .replace("/*__FLAT__*/", flat)
            .replace("/*__POPS__*/", json.dumps(pops, separators=(",", ":"))))

full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n' + page + '\n</body>\n</html>\n')
out = os.path.join(HERE, "..", "..", "index.html")
open(out, "w").write(full)
print("wrote", os.path.normpath(out), len(full) // 1024, "KB;", len(cities), "towns;", len(dem), "elevation tiles")
if args.fragment:
    open(args.fragment, "w").write(page)
    print("wrote", args.fragment)
