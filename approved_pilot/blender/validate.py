"""Offline geometry, physical UV density, joins, and Blender FBX round-trip checks.
Re-run: blender --background crazy88.blend --python validate.py
"""
import bpy,bmesh,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np
EXPECTED=['WALL_Flat_2x2','FLOOR_Tile_2x2','ARCH_Round','COLUMN_Round','PIPE_Straight_2m','PIPE_Elbow90','STAIR_Straight','BRIDGE_Flat_4m']
BOUNDS={
 'WALL_Flat_2x2':([0,0,0],[2,0,2]),'FLOOR_Tile_2x2':([0,0,0],[2,2,0]),
 'ARCH_Round':([-1.3,-.15,0],[1.3,.15,3.3]),'COLUMN_Round':([-.25,-.25,0],[.25,.25,2]),
 'PIPE_Straight_2m':([0,-.1,-.1],[2,.1,.1]),'PIPE_Elbow90':([0,-.1,-.1],[1.1,1,.1]),
 'STAIR_Straight':([0,-1,0],[4,1,2]),'BRIDGE_Flat_4m':([0,-1,-.2],[4,1,0])}

def bounds(obj):return [[min(v.co[i] for v in obj.data.vertices) for i in range(3)],[max(v.co[i] for v in obj.data.vertices) for i in range(3)]]
def inspect(obj,record):
    mesh=obj.data;mesh.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(mesh)
    boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold and not e.is_boundary for e in bm.edges)
    inconsistent=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    volume=bm.calc_volume(signed=True);bm.free()
    degenerate=0;density=[];uv=mesh.uv_layers.active
    for tri in mesh.loop_triangles:
        p=[Vector(mesh.vertices[i].co) for i in tri.vertices]
        e1=p[1]-p[0];e2=p[2]-p[0];area=e1.cross(e2).length/2
        if area<1e-10:degenerate+=1;continue
        if uv:
            u=[Vector(uv.data[i].uv) for i in tri.loops]
            # Jacobian maps a local metre basis to UV. Both singular values should be 0.5.
            tangent=e1.normalized();perp=e1.cross(e2).normalized().cross(tangent)
            physical=np.array([[e1.length,e2.dot(tangent)],[0,e2.dot(perp)]])
            tex=np.array([[u[1].x-u[0].x,u[2].x-u[0].x],[u[1].y-u[0].y,u[2].y-u[0].y]])
            density.extend(np.linalg.svd(tex@np.linalg.inv(physical),compute_uv=False).tolist())
    duplicate=len(mesh.polygons)-len(set(tuple(sorted(p.vertices)) for p in mesh.polygons))
    expected=BOUNDS[obj.name];actual=bounds(obj)
    checks=dict(nonempty=len(mesh.vertices)>0,degenerate_triangles=degenerate==0,duplicate_faces=duplicate==0,
       normals_consistent=inconsistent==0,positive_closed_volume=volume>0 if record['closed'] else True,
       topology=(boundary==0 and nonmanifold==0) if record['closed'] else (boundary==4 and len(mesh.polygons)==1),
       uv_present=bool(uv),uv_density=bool(density) and min(density)>=.43 and max(density)<=.57,
       expected_bounds=max(abs(a-b) for aa,bb in zip(actual,expected) for a,b in zip(aa,bb))<1e-5,
       manifest_bounds=max(abs(a-b) for aa,bb in zip(actual,[record['bounds']['min'],record['bounds']['max']]) for a,b in zip(aa,bb))<1e-5,
       material_slots=[m.name for m in mesh.materials]==record['material_slots'],
       identity_transform=all(abs(v)<1e-8 for v in obj.location) and all(abs(v)<1e-8 for v in obj.rotation_euler) and all(abs(v-1)<1e-8 for v in obj.scale))
    if obj.name in EXPECTED[:2]:
        values=[tuple(round(float(n),6) for n in d.uv) for d in uv.data]
        checks['base_unit_uv_exact']=set(values)=={(0,0),(1,0),(1,1),(0,1)}
        checks['plane_normal']=mesh.polygons[0].normal.dot(Vector((0,-1,0) if obj.name.startswith('WALL') else (0,0,1)))>.999
    if obj.name=='STAIR_Straight':
        # Two 4.4 m² sides, 8 m² bottom, 8 m² treads, 4 m² risers, 4 m² back.
        checks['surface_area_no_overlap']=abs(sum(t.area for t in mesh.loop_triangles)-32.8)<1e-4
    return dict(checks=checks,passed=all(checks.values()),triangles=len(mesh.loop_triangles),boundary_edges=boundary,nonmanifold_edges=nonmanifold,signed_volume=volume,uv_scale_range=density and [min(density),max(density)],max_uv_scale_error_percent=max([abs(x/.5-1)*100 for x in density] or [100]),degenerate_count=degenerate)

def roundtrip(root,objects,manifest):
    saved=bpy.context.window.scene;scene=bpy.data.scenes.new('temporary_roundtrip');bpy.context.window.scene=scene
    results=[]
    for original,record in zip(objects,manifest['assets']):
        before=set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(root/record['filename']),use_anim=False,use_image_search=False)
        imported=[o for o in bpy.data.objects if o not in before];meshes=[o for o in imported if o.type=='MESH']
        checks=dict(one_mesh=len(meshes)==1)
        if len(meshes)==1:
            obj=meshes[0];obj.data.calc_loop_triangles()
            coords=[obj.matrix_world@v.co for v in obj.data.vertices]
            bb=[[min(v[i] for v in coords) for i in range(3)],[max(v[i] for v in coords) for i in range(3)]]
            error=max(abs(a-b) for aa,cc in zip(bb,bounds(original)) for a,b in zip(aa,cc))
            checks.update(bounds_metres=error<1e-5,triangles=len(obj.data.loop_triangles)==record['triangles'],uv_present=bool(obj.data.uv_layers.active),materials=[m.name.split('.')[0] for m in obj.data.materials]==record['material_slots'])
            def uv_corners(mesh):
                # Triangulation may choose a different diagonal; compare unique position/UV pairs.
                return sorted(set(tuple(round(float(n),4) for n in (*mesh.vertices[loop.vertex_index].co,*mesh.uv_layers.active.data[loop.index].uv)) for loop in mesh.loops))
            checks['uv_values']=uv_corners(original.data)==uv_corners(obj.data)
            checks['checker_image']=all(any(n.type=='TEX_IMAGE' and n.image and n.image.has_data for n in m.node_tree.nodes) for m in obj.data.materials)
            bm=bmesh.new();bm.from_mesh(obj.data);checks['closed_normals']=bm.calc_volume(signed=True)>0 if record['closed'] else True;bm.free()
        results.append(dict(asset_id=original.name,passed=all(checks.values()),checks=checks))
        for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.window.scene=saved;bpy.data.scenes.remove(scene)
    return results

def validate_assets(root,objects,manifest,assembly,joins):
    assembly.frame_set(1)
    assembly.view_layers[0].update()
    records={r['asset_id']:r for r in manifest['assets']};reports={o.name:inspect(o,records[o.name]) for o in objects}
    snap=[]
    for pair in joins:
        endpoints=[]
        for key in ['a','b']:
            obj=assembly.objects[pair[key]];r=records[obj.data.name]
            con=next(c for c in r['connectors'] if c['name']==pair[key+'_connector'])
            endpoints.append((obj.matrix_world@Vector(con['position']),obj.matrix_world.to_3x3()@Vector(con['direction']),con['profile']))
        error=(endpoints[0][0]-endpoints[1][0]).length;dot=endpoints[0][1].dot(endpoints[1][1])
        snap.append(dict(**pair,error_metres=error,direction_dot=dot,passed=error<=.001 and dot<-.99999 and endpoints[0][2]==endpoints[1][2]))
    # Actual mesh ray tests: pass through the arch's 2m-wide, 2m-high rectangular clear region.
    arch=next(o for o in objects if o.name=='ARCH_Round')
    tree=BVHTree.FromPolygons([v.co for v in arch.data.vertices],[list(p.vertices) for p in arch.data.polygons])
    clear=all(tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)[0] is None for x in [-.95,0,.95] for z in [.05,1,1.95])
    solid=tree.ray_cast(Vector((1.15,-1,1)),Vector((0,1,0)),2)[0] is not None
    file_checks={r['filename']:(root/r['filename']).is_file() and (root/r['filename']).stat().st_size>0 for r in manifest['assets']}
    rt=roundtrip(root,objects,manifest)
    report=dict(scope='8 assets; offline Blender checks only',blender_version=bpy.app.version_string,
        inventory_pass=sorted(records)==sorted(EXPECTED) and len(objects)==8,assets=reports,joins=snap,arch_clearance_pass=clear and solid,
        exported_files=file_checks,fbx_blender_roundtrip=rt,viewer_compatibility='NOT TESTED; no domain connection or import attempted',
        collision='Four optional proposals in separate Blender scene. No viewer collision claims.',
        uv_tolerance='0.5 UV/metre; +/-14% singular-value tolerance on curved surfaces, exact base-tile corners',
        deferred=['DarkRide loading and normals','texture repeat and persistence','normal map +Y/-Y','PBR import and material replacement','collision and walking','FPS/load time/texture memory'])
    report['offline_pass']=report['inventory_pass'] and all(v['passed'] for v in reports.values()) and all(v['passed'] for v in snap) and clear and solid and all(file_checks.values()) and all(v['passed'] for v in rt)
    (root/'reports/validation.json').write_text(json.dumps(report,indent=2))
    print('OFFLINE_VALIDATION',report['offline_pass'])
    if not report['offline_pass']:raise RuntimeError('Validation failed: inspect reports/validation.json')
    return report

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];manifest=json.loads((root/'manifest.json').read_text())
    objects=[bpy.data.objects[name] for name in EXPECTED];assembly=bpy.data.scenes['02_Assembly_Review'];bpy.context.window.scene=assembly
    bpy.context.view_layer.update()
    validate_assets(root,objects,manifest,assembly,json.loads((root/'tests/assembly_joins.json').read_text()))
