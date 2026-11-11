# Australia Pin Map

A zoomable, pannable 3D terrain map of Australia. Paste GPS coordinates and they appear as numbered pins.

- The built page is `index.html` at the repo root. GitHub Pages serves it as the site home page.
- Self-contained. State boundaries, towns and elevation are embedded in the page, so the map works without tile servers. Only MapLibre GL JS 4.7.1 (unpkg) and Google Fonts load from the web. The optional Streets (OpenStreetMap) and Satellite (Esri) base maps load online tiles.

## Input formats (one per line)

```
-33.8568, 151.2153, Sydney Opera House
25°20'40"S 131°02'13"E, Uluru
153.0251, -27.4698, Brisbane          <- lon,lat is detected and swapped
Perth https://www.google.com/maps/@-31.95,115.86,12z
```

## Rebuild

```
python3 tools/australia-map/build.py [--fragment artifact.html] [--pops path/to/points_of_presence.yaml]
```

Needs Python 3 with Pillow (and PyYAML for `--pops`). `--pops` refreshes `data/pops.json` from the quoting plugin's `shared/points_of_presence.yaml`. Edit `tools/australia-map/template.html`, then rebuild.

## Points of Presence

The 65 Green Light Priority 1 PoPs (quoting plugin master list, v3.0, effective 2026-09-26) are drawn as diamonds coloured by casual availability: green High (4hr committed, 2hr stretch), amber Medium (NBD committed, 4hr stretch), red Low (NBD committed, no stretch). Rings show the Metro (50 km) and Regional (150 km) thresholds as straight-line distances; the plugin's thresholds are road km, so real coverage is smaller. Each pin lists its nearest PoP, the straight-line distance and the Metro / Regional / Remote band, and Copy as CSV includes them.

## Data sources

- `tools/australia-map/data/pops.json`: Green Light Priority 1 PoP master (quoting plugin), fields limited to location, casual level and SLA.

- `tools/australia-map/data/aus_states.json`, `data/cities.json`: Natural Earth 1:10m admin-1 and populated places (public domain), simplified.
- `tools/australia-map/data/dem/*.png`: Mapzen Terrarium elevation tiles (AWS Open Data, zoom 3-6), clamped at sea level, rounded to 4 m and re-compressed. All-ocean tiles are omitted and replaced by a flat tile.
- `tools/australia-map/data/maplibre-gl.css`: MapLibre GL JS 4.7.1 stylesheet (BSD-3-Clause).
