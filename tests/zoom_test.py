"""The photo viewer's zoom arithmetic, run in a JS engine against a stubbed DOM.

Needs dukpy (see requirements-dev.txt); skipped, loudly, without it — there is
no browser here, and the zoom-about-a-point maths is exactly the kind of thing
that is a sign error away from feeling wrong and looking fine.
"""
import sys
try:
    import dukpy
except ImportError:
    print('  SKIPPED — dukpy is not installed (pip install -r requirements-dev.txt)')
    print('0 passed, 0 failed')
    sys.exit(0)
import re, io

import os
HERE = os.path.dirname(os.path.abspath(__file__))
page = io.open(os.path.join(HERE, '..', 'docs', 'dashboard.html'), encoding='utf-8').read()
start = page.index("const shotStage = document.getElementById('shot-stage');")
end = page.index("const zoomStep = f => zoomAt")
code = page[start:end]

# Duktape is ES5, so two syntax forms have to be rewritten to run here. The
# counts are asserted: if the code changes shape, this fails loudly rather than
# quietly testing something that is no longer there.
code, n1 = re.subn(r'`translate\(\$\{zX\}px, \$\{zY\}px\) scale\(\$\{zScale\}\)`',
                   "'translate(' + zX + 'px, ' + zY + 'px) scale(' + zScale + ')'", code)
code, n2 = re.subn(r"Math\.round\(zScale \* 100\) \+ '%'", "Math.round(zScale * 100) + '%'", code)
assert n1 == 1, f'transform template literal not found ({n1})'
code = code.replace("const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));",
                    "function clamp(v, lo, hi){return Math.min(hi, Math.max(lo, v));}")
code = re.sub(r'const (\w+) = \(([^)]*)\) => \{', r'function \1(\2){', code)
code = code.replace('function applyZoom(', 'function applyZoom(')

STAGE_W, STAGE_H, IMG_W, IMG_H = 800, 600, 800, 450     # a fitted landscape photo
stub = """
var STAGE_W = %d, STAGE_H = %d, IMG_W = %d, IMG_H = %d;
var _level = '';
var shotStage = {
    clientWidth: %d, clientHeight: %d,
    classList: { toggle: function(){}, add: function(){}, remove: function(){} },
    getBoundingClientRect: function(){ return {left:0, top:0, width:%d, height:%d}; }
};
var shotImg = { offsetWidth: %d, offsetHeight: %d, style: {} };
var document = { getElementById: function(){ return {}; } };
""" % (STAGE_W, STAGE_H, IMG_W, IMG_H, STAGE_W, STAGE_H, STAGE_W, STAGE_H, IMG_W, IMG_H)
code = code.replace("const shotStage = document.getElementById('shot-stage');", "")
code = code.replace("const shotImg = document.getElementById('shot-viewer-img');", "")
code = code.replace("document.getElementById('shot-level').textContent = Math.round(zScale * 100) + '%';",
                    "_level = Math.round(zScale * 100) + '%';")
code = code.replace('let ', 'var ').replace('const ', 'var ')

harness = stub + code + """
// Where an image point lands on screen, given the current transform. The stage
// centre is the origin, matching transform-origin: center center.
function project(u, v) { return [zX + zScale * u, zY + zScale * v]; }
var out = [];
function t(name, got, want, tol) {
    var ok = Math.abs(got - want) <= (tol === undefined ? 1e-6 : tol);
    out.push([name, ok, got, want]);
}

// 1. Zooming about a point leaves that point where it was — unless holding it
//    there would need the image dragged past its own edge, in which case the
//    pan clamp wins and the offset sits exactly on the limit. Both halves are
//    wanted: the first is what makes pinch feel right, the second is what stops
//    the picture disappearing off the side.
function limit(size, stage) { return Math.max(0, (size * zScale - stage) / 2); }
for (var i = 0; i < 6; i++) {
    fitShot();
    var px = [-300, -150, 0, 120, 260, 399][i], py = [-200, 90, 0, -60, 150, 220][i];
    var u = (px - zX) / zScale, v = (py - zY) / zScale;    // image point under it
    zoomAt(px + 400, py + 300, 2.5);                       // client = centre + offset
    var p = project(u, v);
    var heldX = Math.abs(p[0] - px) <= 0.5 || Math.abs(Math.abs(zX) - limit(IMG_W, STAGE_W)) <= 0.5;
    var heldY = Math.abs(p[1] - py) <= 0.5 || Math.abs(Math.abs(zY) - limit(IMG_H, STAGE_H)) <= 0.5;
    out.push(['zoom about (' + px + ',' + py + ') holds x, or stops at the edge', heldX, p[0], px]);
    out.push(['zoom about (' + px + ',' + py + ') holds y, or stops at the edge', heldY, p[1], py]);
}

// 1b. With room to move on both axes, the point is held exactly.
fitShot();
var u0 = 100, v0 = 40;
zoomAt(400 + u0, 300 + v0, 1.5);
var pp = project(u0, v0);
t('a point with room to spare is held exactly, x', pp[0], u0, 0.5);
t('  and y', pp[1], v0, 0.5);

// 2. Scale is clamped both ways.
fitShot(); zoomAt(400, 300, 0.2);
t('cannot zoom below fit', zScale, 1);
fitShot(); for (var j = 0; j < 40; j++) zoomAt(400, 300, 2);
t('cannot zoom past zMax', zScale, zMax);

// 3. At fit, the image sits centred however hard it was dragged.
fitShot(); zX = 500; zY = -400; applyZoom();
t('no stray offset at fit x', zX, 0);
t('no stray offset at fit y', zY, 0);

// 4. Panning stops at the edge rather than flinging the image away.
fitShot(); zoomAt(400, 300, 4);
zX = 99999; zY = 99999; applyZoom();
t('pan clamps to the right edge', zX, (IMG_W * zScale - STAGE_W) / 2);
t('pan clamps to the bottom edge', zY, (IMG_H * zScale - STAGE_H) / 2);
zX = -99999; zY = -99999; applyZoom();
t('pan clamps to the left edge', zX, -(IMG_W * zScale - STAGE_W) / 2);

// 5. Fit really resets.
zoomAt(500, 400, 3); fitShot();
t('fit resets scale', zScale, 1); t('fit resets x', zX, 0); t('fit resets y', zY, 0);

// 6. The transform string is what gets written.
fitShot(); zoomAt(400, 300, 2);
out.push(['transform is written', shotImg.style.transform.indexOf('scale(2)') > -1,
          shotImg.style.transform, 'contains scale(2)']);
out.push(['zoom level is shown', _level === '200%', _level, '200%']);
JSON.stringify(out);
"""
res = dukpy.evaljs(harness)
import json
rows = json.loads(res)
ok = sum(1 for r in rows if r[1] is True)
print(f'zoom maths, run in a JS engine against a {IMG_W}x{IMG_H} image in a {STAGE_W}x{STAGE_H} stage\n')
for name, good, got, want in rows:
    print(f'  {"ok  " if good else "FAIL"} {name}: {got}' + ('' if good else f'  (expected {want})'))
print(f'\n{ok} passed, {len(rows)-ok} failed')
