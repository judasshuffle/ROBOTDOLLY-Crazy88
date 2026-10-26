# ROBOTDOLLY — CRAZY 88

## Codex implementation brief — procedural modular architectural kit

### Mission

Create a reproducible, headless Blender Python (`bpy`) project that generates **exactly 88 distinct reusable modular architectural mesh assets** for future procedural placement in DarkRide. The first aesthetic test is a Backrooms-like liminal environment, but assets must remain theme-neutral and accept interchangeable tileable PBR materials.

**Do not alter, import into, or delete anything in the live Crompton Moor domain.** This task is asset generation and offline validation only. Use a disposable test scene/domain later, after approval.

### Key design principles

* Geometry only where needed: avoid buried faces, duplicate coplanar faces and gratuitous subdivisions. Keep visible two-sided surfaces where both sides can be visited; do not indiscriminately delete end caps on independently reusable pieces.
* Reuse a small mesh library and material palette. Export each unique mesh once; the future domain generator references asset URLs and transforms rather than baking repeated copies.
* Make topology appropriate for each form: planar walls can be two triangles; arches need true openings; stairs and bridges need navigable surfaces. Avoid paper-thin surfaces where wall thickness, backface culling, collision or sightlines require solids.
* Adopt a **2 m × 2 m reference tile**. A square wall panel uses the full 0–1 UV square. A 4 m × 2 m planar wall uses 0–2 horizontally and 0–1 vertically, where supported. Other surfaces preserve consistent texel density and material orientation. Do **not** force curved surfaces into square UV islands.
* Assign named, consistent PBR material slots (e.g. MAT\_Wall, MAT\_Floor, MAT\_Ceiling, MAT\_Concrete, MAT\_Metal, MAT\_Trim, MAT\_Glass, MAT\_Emissive). Material names are stable; placeholder checker materials may be used. Do not bake one-off textures into meshes.
* Distinguish **render meshes** from simplified **collision proxies**; collision behavior in DarkRide must be experimentally verified before deployment.
* Use consistent units (metres), coordinate axes, origins/pivots, outward normals, mesh naming and modular snap points. Record exact connectors, directions, dimensions and occupied bounds in machine-readable metadata.

### Inventory — exactly 88 unique asset definitions

**A. Walls, floors, ceilings (16)**
1 WALL\_Flat\_2x2
2 WALL\_Flat\_4x2
3 WALL\_Thick\_2x2
4 WALL\_InsideCorner
5 WALL\_OutsideCorner
6 WALL\_RecessedPanel
7 WALL\_LowPartition
8 WALL\_Curved90
9 FLOOR\_Tile\_2x2
10 FLOOR\_Tile\_4x4
11 FLOOR\_RaisedPlatform
12 FLOOR\_Ramp
13 CEILING\_Flat\_2x2
14 CEILING\_Grid\_2x2
15 CEILING\_Vaulted
16 CEILING\_Recessed

**B. Arches, columns, beams, trim (14)**
17 ARCH\_Round
18 ARCH\_Point
19 ARCH\_Segmental
20 ARCH\_WideSpan
21 ARCH\_Double
22 COLUMN\_Round
23 COLUMN\_Square
24 COLUMN\_Fluted
25 PILASTER\_Wall
26 BEAM\_Straight
27 BEAM\_Curved
28 CORNICE\_Straight
29 SKIRTING\_Straight
30 TRIM\_PanelFrame

**C. Doors and windows (12)**
31 DOORWAY\_Standard
32 DOORWAY\_Wide
33 DOORWAY\_Arched
34 DOOR\_Leaf\_Plain
35 DOOR\_Leaf\_Industrial
36 DOOR\_Frame
37 DOOR\_DoubleLeaf
38 WINDOW\_Rectangular
39 WINDOW\_Tall
40 WINDOW\_Arched
41 WINDOW\_InteriorObservation
42 WINDOW\_FrameAndSill

**D. Pipes and fittings (16)**
43 PIPE\_Straight\_1m
44 PIPE\_Straight\_2m
45 PIPE\_Straight\_4m
46 PIPE\_Elbow45
47 PIPE\_Elbow90
48 PIPE\_Tee
49 PIPE\_Cross
50 PIPE\_Reducer
51 PIPE\_Flange
52 PIPE\_EndCap
53 PIPE\_ValveWheel
54 PIPE\_ValveBody
55 PIPE\_Bracket
56 PIPE\_Ubend
57 PIPE\_Riser
58 PIPE\_Manifold

**E. Ventilation (10)**
59 DUCT\_Square\_1m
60 DUCT\_Square\_2m
61 DUCT\_Elbow90
62 DUCT\_Tee
63 DUCT\_Reducer
64 DUCT\_EndCap
65 VENT\_WallGrille
66 VENT\_CeilingGrille
67 VENT\_FanHousing
68 DUCT\_Hanger

**F. Stairs, bridges, elevators (10)**
69 STAIR\_Straight
70 STAIR\_Switchback
71 STAIR\_Spiral
72 STAIR\_Landing
73 STAIR\_Railing
74 BRIDGE\_Flat\_4m
75 BRIDGE\_Arched
76 BRIDGE\_Catwalk
77 ELEVATOR\_ShaftSegment
78 ELEVATOR\_CabShell

**G. Lighting and environmental details (10)**
79 LIGHT\_FluorescentHousing
80 LIGHT\_RecessedPanel
81 LIGHT\_WallSconce
82 LIGHT\_IndustrialCage
83 LIGHT\_ExitSignHousing
84 DETAIL\_CableTray
85 DETAIL\_WallConduit
86 DETAIL\_ServiceHatch
87 DETAIL\_BalconyRail
88 DETAIL\_ColumnBase

These are proposed initial variants. Maintain the count of 88; document any substitutions rather than silently changing the inventory. Moving doors, elevator operation, light emission and sound will require separate runtime components or scripts; the Blender kit supplies static meshes only.

### UV/PBR contract

* Each material-bearing face gets an explicit, deterministic UV map. For square 2×2 m wall/floor/ceiling tiles, use UV (0,0)–(1,1), oriented consistently across modules.
* Longer planar pieces tile proportionally. Verify no stretching using a labelled checkerboard and directional arrows.
* Pipes use cylindrical UVs with sensible seams; elbows follow the bend; arches and trims use proportional strips/planar projections as appropriate.
* Support common PBR maps: base color, normal, roughness, metallic, AO where compatible. Height/displacement is optional and must not be assumed supported by DarkRide.
* Avoid reliance on a single giant texture atlas if it would prevent freely swapping tileable PBR textures. Material count and texture memory should be benchmarked.
* Test texture repeat behavior, normal-map handedness and material import in the actual DarkRide viewer before full production. Export UVs even when the placeholder material is flat.

### Export and deliverables

Create:

```
ROBOTDOLLY-Crazy88/
  README.md
  blender/generate.py
  blender/validate.py
  blender/crazy88.blend
  meshes/                 # one named export per unique asset
  collision/              # simplified optional collision meshes
  textures/checker/       # diagnostic checker and normal-map tests
  themes/backrooms.json   # example PBR material mapping, no copyrighted textures
  previews/contact\_sheet.png
  previews/uv\_checks/
  manifest.json           # asset ID, filename, bounds, origin, connectors, slots, UV scale, triangles
  reports/validation.json
  tests/
```

Export GLB and/or FBX as indicated by **real DarkRide importer compatibility testing**, not assumptions. Do not pretend a format is validated until it loads in the viewer with correct normals, UVs, materials and collision. Keep source .blend and scripts authoritative.

### Generator workflow

1. Inspect existing DarkRide/WorldBridge asset and entity conventions read-only if accessible. Record findings and unknowns.
2. Build an initial **8-asset pilot**: WALL\_Flat\_2x2, FLOOR\_Tile\_2x2, ARCH\_Round, COLUMN\_Round, PIPE\_Straight\_2m, PIPE\_Elbow90, STAIR\_Straight, BRIDGE\_Flat\_4m.
3. Export and produce checkerboard renders plus a small assembled Blender test scene showing joins, arch clearance, pipe elbows, stairs and a bridge.
4. Run automated checks: mesh counts, degenerate triangles, normals, UV presence, texel density, connector alignment, material names, bounding boxes and file existence.
5. **Stop for review** before generating the remaining 80 assets. Do not touch the live domain.
6. After approval, generate the full 88 and a separate offline multistorey atrium showcase with arches, bridges, corridors, pipes and ventilation. Reuse asset definitions; avoid accidental duplicates.

### Procedural-domain readiness

The future domain generator should work from a deterministic seed and a layout graph. Reserve volumes for atriums, shafts and large halls before placing rooms. Validate traversability, doorway clearance, bridge support and multilevel connectivity. Divide large scenes into manageable chunks rather than one giant mesh. The ultimate proposed site is an **approximately 805 m × 805 m** *empty, verified* area in Crompton Moor, but no coordinates have been approved. Never infer the site is empty; require a backup and an explicit import/rollback plan.

### Acceptance criteria

* 8 pilot meshes exported and visibly inspected before mass generation.
* Full batch, when authorized, contains exactly 88 unique, deterministically regenerated named assets.
* Square base units have exactly 0–1 UV mapping and shared physical texel density; curved surfaces do not visibly stretch.
* Snap connections meet within a documented tolerance (suggest 1 mm), with no accidental gaps, overlap, inverted normals or blocked openings.
* Shared PBR material slots can be remapped through a theme manifest without editing mesh geometry.
* Triangle and entity counts are recorded, not assumed; render/collision tradeoffs documented.
* The first DarkRide import is into a disposable test environment with FPS, loading, texture persistence and collision observations recorded.

### Reference image direction

Use references as **visual inspiration only**, not as literal topology or measured geometry:

1. Modular game-environment construction kits showing walls, corners, floor tiles and arches.
2. Monumental brutalist atriums with elevated bridges and staircases.
3. Roman/Gothic arches and vaulted interiors.
4. Industrial pipe/duct modular kits showing standardized elbows, tees, flanges and brackets.
5. Liminal yellow-wallpaper office corridors (Backrooms atmosphere only).
6. UV checkerboard previews showing directional, undistorted tile alignment.

**Important:** The user will supply their own tileable PBR textures. Do not download or redistribute third-party reference imagery or texture sets without permission/licence review.

