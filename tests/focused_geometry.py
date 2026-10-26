"""Read-only tests against the loaded master: reducer seams and actual spiral clearance."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'manifest.json').read_text())
spiral=bpy.data.objects['STAIR_Spiral'];mesh=spiral.data
verts=[v.co.copy() for v in mesh.vertices];faces=[list(f.vertices) for f in mesh.polygons]
tree=BVHTree.FromPolygons(verts,faces)
upper=BVHTree.FromPolygons([v+Vector((0,0,4)) for v in verts],faces)
samples=[]
for i in range(20):
    angle=(i+.5)*math.pi/10
    for radius in [.65,1.25,1.85]:
        x,y=radius*math.cos(angle),radius*math.sin(angle)
        hit=tree.ray_cast(Vector((x,y,5)),Vector((0,0,-1)),10)[0]
        if hit is None:raise AssertionError('Missing spiral tread')
        own=tree.ray_cast(hit+Vector((0,0,.0001)),Vector((0,0,1)),2.1)[0]
        overhead=upper.ray_cast(hit+Vector((0,0,.0001)),Vector((0,0,1)),5)[0]
        gap=overhead.z-hit.z if overhead else None
        samples.append(dict(step=i+1,radius=radius,tread_z=float(hit.z),expected_z=(i+1)*.2,stacked_clearance=gap,
          passed=abs(hit.z-(i+1)*.2)<1e-5 and own is None and gap is not None and gap>=3.6-1e-5))
# Count UV discontinuities between neighboring longitudinal cone facets; cap seams excluded.
cone=bpy.data.objects['PIPE_Reducer'].data;uv=cone.uv_layers.active
shells={}
for inner in [False,True]:
    selected=[]
    for f in cone.polygons:
        points=[cone.vertices[j].co for j in f.vertices]
        if max(p.x for p in points)-min(p.x for p in points)<.9:continue
        first=next(p for p in points if abs(p.x)<1e-5)
        if (math.hypot(first.y,first.z)<.09)==inner:selected.append(f)
    edges={}
    for f in selected:
        for k,loop in enumerate(f.loop_indices):
            nxt=f.loop_indices[(k+1)%len(f.loop_indices)];a=cone.loops[loop].vertex_index;b=cone.loops[nxt].vertex_index
            if abs(cone.vertices[a].co.x-cone.vertices[b].co.x)<.9:continue
            edges.setdefault(tuple(sorted((a,b))),[]).append({a:uv.data[loop].uv.copy(),b:uv.data[nxt].uv.copy()})
    seams=sum(any((entries[0][v]-entries[1][v]).length>1e-5 for v in edge) for edge,entries in edges.items() if len(entries)==2)
    shells['inner' if inner else 'outer']=dict(facets=len(selected),longitudinal_seams=seams,passed=len(selected)==32 and seams==1 and all(len(e)==2 for e in edges.values()))
grid_error=max(abs(x/.005-round(x/.005))*.005 for a in manifest['assets'] for c in a['connectors'] for x in c['position'])
report=dict(spiral_samples=samples,minimum_stacked_spiral_clearance_metres=min(s['stacked_clearance'] for s in samples),reducer_uv_shells=shells,
    attachment_grid_metres=.005,max_attachment_grid_error_metres=grid_error,
    notes=['Clearance sampled geometrically at 60 positions; no avatar/collision certification.',
           'Spiral treads narrow toward the inner radius; walk line, railings and viewer locomotion need manual review.',
           'UV continuity verified within reducer shells; cap seams and local Boolean cut seams are intentional.'])
report['passed']=all(s['passed'] for s in samples) and all(s['passed'] for s in shells.values()) and grid_error<1e-6
(ROOT/'reports/focused_geometry.json').write_text(json.dumps(report,indent=2))
assert report['passed'],report
print('FOCUSED_GEOMETRY_PASS',report['minimum_stacked_spiral_clearance_metres'])
