#!/usr/bin/env python3
"""Create a standalone, offline-friendly HTML benchmark report from output/results.csv.

Usage: ./generate-report.py [output/results.csv]
HTML is written alongside the CSV; PNGs are linked by relative filenames.
Uses only the Python 3 standard library.
"""
import csv
import html
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else ROOT / 'output' / 'results.csv'
if len(sys.argv) > 2:
    sys.exit('Usage: generate-report.py [path/to/results.csv]')
if not CSV_PATH.is_file():
    sys.exit(f'ERROR: CSV not found: {CSV_PATH}')

rows = []
with CSV_PATH.open(newline='', encoding='utf-8-sig') as file:
    reader = csv.DictReader(file)
    required = {'power_limit_w', 'seconds', 'image'}
    if not required.issubset(reader.fieldnames or []):
        sys.exit('ERROR: Expected CSV columns: power_limit_w,seconds,image')
    for line, item in enumerate(reader, start=2):
        try:
            watts = float(item['power_limit_w'].strip())
            seconds = float(item['seconds'].strip())
            if not (math.isfinite(watts) and math.isfinite(seconds) and watts > 0 and seconds > 0):
                raise ValueError('nonpositive or nonfinite number')
            image = Path(item['image']).name if item['image'] else ''
        except (ValueError, AttributeError) as err:
            sys.exit(f'ERROR: Invalid result on CSV line {line}: {err}')
        rows.append({'watts': watts, 'seconds': seconds, 'image': image})
if not rows:
    sys.exit('ERROR: CSV has no measurements')
rows.sort(key=lambda r: r['watts'])
base = rows[0]
fastest = min(rows, key=lambda r: r['seconds'])
max_row = rows[-1]
change = (1 - fastest['seconds'] / base['seconds']) * 100
# Deliberately use power limit as an input label, not measured consumption.
min_y = min(r['seconds'] for r in rows)
max_y = max(r['seconds'] for r in rows)
span = max(max_y - min_y, 0.25)
lo, hi = min_y - span * .16, max_y + span * .16
left, top, width, height = 74, 24, 880, 300
min_x, max_x = rows[0]['watts'], rows[-1]['watts']
def px(x):
    return left + (x - min_x) / (max_x - min_x or 1) * width
def py(y):
    return top + (hi - y) / (hi - lo) * height
svg = []
for n in range(5):
    y = lo + (hi - lo) * n / 4
    svg += [f'<line x1="{left}" y1="{py(y):.1f}" x2="{left+width}" y2="{py(y):.1f}" stroke="#e0e7ef"/>',
            f'<text x="{left-12}" y="{py(y)+4:.1f}" text-anchor="end" fill="#5c6b7c" font-size="13">{y:.1f}s</text>']
points = ' '.join(f'{px(r["watts"]):.1f},{py(r["seconds"]):.1f}' for r in rows)
svg.append(f'<polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linejoin="round"/>')
for r in rows:
    x, y = px(r['watts']), py(r['seconds'])
    is_fastest = r is fastest
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{6 if is_fastest else 4.5}" fill="{ "#059669" if is_fastest else "#2563eb" }"><title>{r["watts"]:g} W: {r["seconds"]:.3f} s</title></circle>')
    svg.append(f'<text x="{x:.1f}" y="{top+height+25}" transform="rotate(0 {x:.1f} {top+height+25})" text-anchor="middle" fill="#5c6b7c" font-size="12">{r["watts"]:g}</text>')
svg.append(f'<text x="{left+width/2}" y="{top+height+54}" text-anchor="middle" fill="#5c6b7c" font-size="14">Power limit (W)</text>')
svg_content = '\n'.join(svg)
tr = []
gallery = []
for r in rows:
    delta = (1 - r['seconds'] / base['seconds']) * 100
    img = r['image']
    has_img = bool(img) and (CSV_PATH.parent / img).is_file()
    link = f'<a href="{html.escape(img, quote=True)}">View image</a>' if has_img else '—'
    tr.append(f'<tr><td>{r["watts"]:g} W</td><td>{r["seconds"]:.3f} s</td><td>{delta:+.1f}%</td><td>{link}</td></tr>')
    if has_img:
        escaped = html.escape(img, quote=True)
        gallery.append(f'<a class="image" href="{escaped}"><img src="{escaped}" loading="lazy" alt="Output at {r["watts"]:g} W"><span>{r["watts"]:g} W · {r["seconds"]:.3f} s</span></a>')
report = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GPU Power Sweep Report</title>
<style>
:root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #182536; background: #f4f7fb; }}
* {{ box-sizing: border-box; }} body {{ margin: 0 auto; padding: 35px 18px 65px; max-width: 1100px; }}
h1 {{ margin: 0; font-size: 2rem; }} .muted {{ color: #58697c; }}
.card {{ background: white; border: 1px solid #e1e8f0; border-radius: 15px; padding: 22px; margin-top: 18px; box-shadow: 0 2px 15px #102a4408; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(175px,1fr)); gap: 14px; margin: 20px 0; }}
.metric {{ background: white; border-radius: 14px; border: 1px solid #e1e8f0; padding: 18px; }}
.metric strong {{ display: block; font-size: 1.65rem; margin-top: 5px; }}
svg {{ display: block; width: 100%; height: auto; }}
table {{ width:100%; border-collapse: collapse; }} th,td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e6edf5; }} th {{ background:#f4f7fb; }}
.scroll {{ overflow-x: auto; }} .gallery {{ display:grid; grid-template-columns: repeat(auto-fill,minmax(160px,1fr)); gap: 14px; }}
a.image {{ color:inherit; text-decoration:none; border:1px solid #e1e8f0; border-radius:10px; overflow:hidden; }}
a.image img {{ width:100%; aspect-ratio:1; object-fit:cover; display:block; }} a.image span {{ display:block; padding:9px; font-size:.85rem; }}
.note {{ border-left: 4px solid #2563eb; padding-left: 14px; line-height: 1.55; }}
</style></head><body>
<h1>GPU Power Sweep Report</h1>
<p class="muted">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(rows)} measurements · Based on {html.escape(CSV_PATH.name)}</p>
<div class="metrics">
<div class="metric"><span class="muted">Tested range</span><strong>{min_x:g}–{max_x:g} W</strong></div>
<div class="metric"><span class="muted">Fastest observed run</span><strong>{fastest['watts']:g} W</strong><span>{fastest['seconds']:.3f} seconds</span></div>
<div class="metric"><span class="muted">Time reduction vs first</span><strong>{change:.1f}%</strong><span>Single-run comparison</span></div>
<div class="metric"><span class="muted">Highest tested limit</span><strong>{max_row['watts']:g} W</strong><span>{max_row['seconds']:.3f} seconds</span></div>
</div>
<section class="card"><h2>Generation time by GPU power limit</h2>
<svg viewBox="0 0 1000 400" role="img" aria-label="Line chart of seconds by power limit">{svg_content}</svg></section>
<section class="card"><h2>Measurements</h2><div class="scroll"><table><thead><tr><th>Power limit</th><th>Time</th><th>Time reduction vs first</th><th>Image</th></tr></thead><tbody>{''.join(tr)}</tbody></table></div></section>
<section class="card"><h2>What these measurements mean</h2><p class="note">The chart shows <b>generation time at configured NVIDIA power limits</b>, not actual GPU watt draw or energy consumed. The fastest observed run is not necessarily the optimal setting. Single runs can vary due to caching, background load, GPU clocks and temperature. Repeat tests before drawing firm conclusions.</p></section>
{('<section class="card"><h2>Generated images</h2><div class="gallery">'+''.join(gallery)+'</div></section>') if gallery else ''}
</body></html>'''
DEST = CSV_PATH.parent / 'report.html'
DEST.write_text(report, encoding='utf-8')
print(f'Report created: {DEST} ({len(rows)} measurements)')
