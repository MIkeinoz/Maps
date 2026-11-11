"""Build the self-contained Australia Pin Map page.

Outputs:
  ../../index.html                 full HTML document (site home page)
  argv[1] (optional)               page fragment for publishing as a Claude artifact
"""
import base64, glob, io, json, math, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")

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
            .replace("/*__FLAT__*/", flat))

full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n' + page + '\n</body>\n</html>\n')
out = os.path.join(HERE, "..", "..", "index.html")
open(out, "w").write(full)
print("wrote", os.path.normpath(out), len(full) // 1024, "KB;", len(cities), "towns;", len(dem), "elevation tiles")
if len(sys.argv) > 1:
    open(sys.argv[1], "w").write(page)
    print("wrote", sys.argv[1])
