# ROBOTDOLLY Crazy 88

© 2026 ROBOTDOLLY / Judas. All rights reserved. Publicly viewable, proprietary assets. No reuse licence is granted. See [LICENSE.md](LICENSE.md).

**89 assets: the specified 88 plus `STAIR_Straight_SlopingUnderside`.** Offline validation passes. The eight approved pilot meshes, dimensions, pivots, connectors and FBX bytes are preserved exactly. The kit is ready for visual review and controlled testing in a separate DarkRide domain; viewer compatibility is not certified.

## Open and review

- `blender/crazy88_master.blend`: master scene with authoritative local-origin meshes, a labelled gallery and the previously generated offline atrium example.
- `previews/contact_sheet.png`: all 89 labelled assets. Seven category sheets offer larger views.
- `previews/uv_checks/`: 89 checker renders; `previews/stair_underside.png` shows the added closed underside.
- `sources/`: one editable `.blend` library per asset. Use Blender **File → Append → [asset].blend → Object** to load its object into a scene.
- `meshes/`: one FBX candidate per asset, with exported triangles and embedded checker textures.
- `manifest.json`: exact bounds, dimensions, local origins, connectors, profiles, material slots, UV scale, topology counts and hashes.
- `DELIVERY.md` and `reports/`: results, limits and machine-readable evidence.

The authoritative library scene intentionally keeps definitions at their original local origins, so meshes overlap there. The labelled gallery uses linked instances for inspection. Select an individual source or isolate an object for editing. Existing atrium content is only an offline demonstration; this finish pass generated no new world layout.

## Geometry, units and texture contract

Blender units are metres, Z up; exported FBX uses Y up and −Z forward. Mesh object transforms are identity. Connectors are local points with outward unit directions and named matching profiles. Joins meet with opposed directions; the tested tolerance is 1 mm. Architectural bays use 2 m modules and service routes use 1 m increments. Thicknesses and attachment offsets are explicit fractional dimensions, not a claim that every footprint is 2 m. All recorded attachment positions lie on a 5 mm subdivision.

UV scale is **2 m per texture repeat**, giving 256 px/m with the supplied original 512 px checker. The base square tiles use exactly 0–1; the 4 m wall uses 0–2 horizontally. Large triangles and sloping faces use orthonormal metric projections. Pipe/reducer surfaces use cylindrical strips or developed cone sectors. A single circumference seam and cap seams are intentional. Some Boolean cut faces have local projected seams; the manifest records their counts. This supports repeating PBR textures, not guaranteed invisible seams for every directional pattern.

Maximum measured UV scale deviation is 11.135% (rounded upward), on the unchanged approved elbow, within the existing ±14% curved-surface tolerance. The revised reducer is within 0.0011%. No tolerance was weakened to pass this delivery. Sources retain 8,251 quads; exports contain 19,204 triangles across the 89 unique definitions.

The additional straight stair retains the approved 4 m run, 2 m rise, 2 m width and tread/approach positions. Its underside is closed along `z = 0.5*x − 0.2`; the lower end extends 0.2 m below the approach datum. The spiral has 20 × 0.2 m rises, a 4 m turn and a 2 m outer radius. Sampled clearance to another copy stacked 4 m above is at least 3.663 m. That geometric check does not certify avatar movement, structural support or building regulations.

Named shared material slots accept replacement tileable PBR textures. `themes/backrooms.json` is an example mapping, not an applied copyrighted texture set. Normal, roughness, metallic and AO diagnostics are included. Glass and emissive slots deliberately show opaque checkers; transparency, emission, moving doors/fans and elevators need separate runtime work.

## Regenerate one asset safely

Tested with Blender **4.5.0**. Blender's bundled NumPy is used; no new dependency is needed for mesh generation/testing. Ordinary Python plus Pillow is only needed to compose contact sheets or recreate the checker. The checker/text-sheet scripts use Windows Arial fonts.

From this folder in PowerShell:

```powershell
$crazy88Blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
& $crazy88Blender --background --factory-startup --python-exit-code 1 --python .\blender\generate.py -- --asset PIPE_Reducer --no-render
```

Replace `PIPE_Reducer` with any manifest ID. Output goes to `individual/PIPE_Reducer/`, including its source, FBX, manifest, validation and isolated Blender scene. Omit `--no-render` for a checker preview. This does **not** alter the canonical master or approved pilot. Isolated results are not automatically promoted. The bundled `approved_pilot/` snapshot makes the package self-contained; leave it unchanged.

## Recheck without rebuilding

```powershell
python .\tests\freeze_pilot.py
python .\tests\contact_sheet.py
& $crazy88Blender --background --factory-startup .\blender\crazy88_master.blend --python-exit-code 1 --python .\blender\generate.py -- --validate-only
& $crazy88Blender --background --factory-startup --python-exit-code 1 --python .\tests\check_sources.py
& $crazy88Blender --background --factory-startup .\blender\crazy88_master.blend --python-exit-code 1 --python .\tests\focused_geometry.py
python .\tests\acceptance.py --blender $crazy88Blender
& $crazy88Blender --background --factory-startup .\approved_pilot\blender\crazy88.blend --python-exit-code 1 --python .\tests\pilot_regression.py
```

Determinism compares all 89 geometry/UV hashes against a separate prior factory-startup generation. Six additional fresh CLI cases test independence, including the revised reducer and spiral. Binary FBX/Blend files may contain timestamps; byte-for-byte deterministic export is not claimed for new assets. Approved pilot FBX bytes are preserved exactly.

Only when a future change warrants a full rebuild:

```powershell
& $crazy88Blender --background --factory-startup --python-exit-code 1 --python .\blender\generate.py -- --no-render
Copy-Item .\manifest.json .\reports\determinism_baseline.json
& $crazy88Blender --background --factory-startup --python-exit-code 1 --python .\blender\generate.py
python .\tests\contact_sheet.py
```

Re-run the verification commands and review the images before packaging a new revision. The original packaging helper is preserved for provenance; it expects the local handover documents omitted from this public copy. Use the repository files directly. No script uploads assets automatically.

## Manual review and DarkRide limits

There are no remaining failing offline checks. Manual review is still needed for spiral walk-line/inner tread width and railings, the new stair's lower underside clearance, the paired double arch's intentional 0.2 m center separation, and UV seams with the user's chosen materials.

The complete kit has **no certified collision-proxy set**. Original optional pilot proposals remain available in the approved snapshot. One-sided wall/floor/ceiling reference planes and open architectural passages need deliberate collision setup. Do not apply a convex hull to an arch and assume the opening remains usable.

DarkRide loading, normal-map handedness, PBR remapping, texture repeat/persistence, culling, collision, walking, FPS and memory remain unverified. Blender FBX round-trip success only establishes Blender behavior. Entity dimensions, registration points and coordinate conversion must be tested before placement. Start in an explicitly separate disposable domain; no live domain deployment is included or authorized by these files.

Public publication is authorized for this repository. No live Crompton Moor data was modified. Publication status and review scope are recorded in `PUBLICATION.md`.
