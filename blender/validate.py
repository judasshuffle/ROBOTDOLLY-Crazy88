"""Executed mesh/UV, approval, snap, clearance and FBX round-trip validation."""
import json,math,hashlib,traceback
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from catalog import INVENTORY,VARIATION,PILOT

def bounds(obj):return [[min(v.co[i] for v in obj.data.vertices) for i in range(3)],[max(v.co[i] for v in obj.data.vertices) for i in range(3)]]
def fingerprint(obj):
    d=dict(vertices=[list(v.co) for v in obj.data.vertices],faces=[list(p.vertices) for p in obj.data.polygons],uv=[list(u.uv) for u in obj.data.uv_layers.active.data])
    return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
def inspect(obj,rec):
    mesh=obj.data;mesh.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(mesh)
    boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold and not e.is_boundary for e in bm.edges);inconsistent=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    volume=bm.calc_volume(signed=True);bm.free();density=[];degenerate=0
    uv=mesh.uv_layers.active
    for tri in mesh.loop_triangles:
        p=[mesh.vertices[i].co for i in tri.vertices];a=p[1]-p[0];b=p[2]-p[0]
        if a.cross(b).length<2e-10:degenerate+=1;continue
        if uv:
            u=[uv.data[i].uv for i in tri.loops];t=a.normalized();v=a.cross(b).normalized().cross(t)
            physical=np.array([[a.length,b.dot(t)],[0,b.dot(v)]]);tex=np.array([[u[1].x-u[0].x,u[2].x-u[0].x],[u[1].y-u[0].y,u[2].y-u[0].y]])
            if abs(np.linalg.det(physical))<1e-10:degenerate+=1;continue
            density.extend(np.linalg.svd(tex@np.linalg.inv(physical),compute_uv=False).tolist())
    bb=bounds(obj);expected=[rec['bounds']['min'],rec['bounds']['max']]
    checks=dict(nonempty=len(mesh.vertices)>0,finite_geometry=all(math.isfinite(n) for v in mesh.vertices for n in v.co),degenerate_triangles=degenerate==0,
       duplicate_faces=len(mesh.polygons)==len(set(tuple(sorted(p.vertices)) for p in mesh.polygons)),normals_consistent=inconsistent==0,
       positive_closed_volume=volume>1e-10 if rec['closed'] else True,
       topology=boundary==0 and nonmanifold==0 if rec['closed'] else boundary==4 and len(mesh.polygons)==1,
       uv_present=bool(uv),uv_density=bool(density) and min(density)>=.43 and max(density)<=.57,
       manifest_bounds=max(abs(a-b) for aa,cc in zip(bb,expected) for a,b in zip(aa,cc))<1e-6,
       material_slots=[m.name for m in mesh.materials]==rec['material_slots'] and all(m.name.startswith('MAT_') for m in mesh.materials),
       identity_transform=all(abs(x)<1e-8 for x in obj.location) and all(abs(x)<1e-8 for x in obj.rotation_euler) and all(abs(x-1)<1e-8 for x in obj.scale),
       fingerprint=fingerprint(obj)==rec['geometry_sha256'])
    if obj.name in ['WALL_Flat_2x2','FLOOR_Tile_2x2','CEILING_Flat_2x2']:
        checks['base_tile_exact_uv']=set(tuple(round(float(x),5) for x in u.uv) for u in uv.data)=={(0,0),(0,1),(1,0),(1,1)}
    if obj.name=='WALL_Flat_4x2':checks['large_wall_repeat']=set(tuple(round(float(x),5) for x in u.uv) for u in uv.data)=={(0,0),(0,1),(2,0),(2,1)}
    if obj.name=='STAIR_Straight':checks['approved_stair_area']=abs(sum(t.area for t in mesh.loop_triangles)-32.8)<1e-4
    if obj.name==VARIATION:
        # Independent volume = width * integral(tread-z_underside) = 2 * 4 * .3 = 2.4.
        checks['sloping_stair_volume']=abs(volume-2.4)<1e-4
        checks['sloping_stair_bounds']=max(abs(x-y) for x,y in zip(bb[0]+bb[1],[0,-1,-.2,4,1,2]))<1e-5
    return dict(passed=all(checks.values()),checks=checks,triangles=len(mesh.loop_triangles),quads=sum(len(p.vertices)==4 for p in mesh.polygons),ngons=sum(len(p.vertices)>4 for p in mesh.polygons),boundary_edges=boundary,nonmanifold_edges=nonmanifold,inconsistent_edges=inconsistent,signed_volume=volume,degenerate_triangles=degenerate,uv_scale_range=[min(density),max(density)] if density else [],max_uv_scale_error_percent=max([abs(x/.5-1)*100 for x in density] or [100]))

def rt_checks(original,obj,rec):
    obj.data.calc_loop_triangles();coords=[obj.matrix_world@v.co for v in obj.data.vertices]
    bb=[[min(v[i] for v in coords) for i in range(3)],[max(v[i] for v in coords) for i in range(3)]]
    error=max(abs(x-y) for a,b in zip(bb,bounds(original)) for x,y in zip(a,b))
    def pairs(mesh):return np.array(list(set(tuple(float(x) for x in (*mesh.vertices[l.vertex_index].co,*mesh.uv_layers.active.data[l.index].uv)) for l in mesh.loops)))
    # Compare unique position/UV pairs using numerical tolerance, avoiding decimal-boundary artefacts.
    a,b=pairs(original.data),pairs(obj.data);worst=0
    for src,dst in [(a,b),(b,a)]:
        for start in range(0,len(src),128):worst=max(worst,float(np.max(np.min(np.max(np.abs(src[start:start+128,None,:]-dst[None,:,:]),axis=2),axis=1))))
    bm=bmesh.new();bm.from_mesh(obj.data);volume=bm.calc_volume(signed=True);bm.free()
    original.data.calc_loop_triangles()
    original_area=sum(t.area for t in original.data.loop_triangles);import_area=sum(t.area for t in obj.data.loop_triangles)
    checks=dict(bounds_metres=error<1e-5,triangle_count=len(obj.data.loop_triangles)==rec['triangles'],uv_values=worst<1e-4,
       material_slots=[m.name.split('.')[0] for m in obj.data.materials]==rec['material_slots'],checker_images=all(any(n.type=='TEX_IMAGE' and n.image and n.image.has_data for n in m.node_tree.nodes) for m in obj.data.materials),
       closed_orientation=volume>0 if rec['closed'] else True,surface_area=abs(original_area-import_area)<max(1e-5,original_area*1e-5))
    return dict(checks=checks,passed=all(checks.values()),bounds_error_metres=error,max_position_uv_error=worst)

def roundtrip(out,objects,records):
    saved=bpy.context.window.scene;scene=bpy.data.scenes.new('temporary_FBX_test');bpy.context.window.scene=scene;reports=[]
    for rec in records:
        name=rec['asset_id'];before=set(bpy.data.objects)
        try:
            bpy.ops.import_scene.fbx(filepath=str(out/rec['filename']),use_anim=False,use_image_search=False)
            imported=[o for o in bpy.data.objects if o not in before];meshes=[o for o in imported if o.type=='MESH']
            if len(meshes)!=1:raise ValueError(f'Expected one mesh, received {len(meshes)}')
            result=rt_checks(objects[name],meshes[0],rec);result['asset_id']=name;reports.append(result)
        except Exception as exc:reports.append(dict(asset_id=name,passed=False,error=str(exc),traceback=traceback.format_exc()))
        for obj in list(bpy.data.objects):
            if obj not in before:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.window.scene=saved;bpy.data.scenes.remove(scene);return reports

def validate(out,objects,manifest,lock):
    records={r['asset_id']:r for r in manifest['assets']};assets={n:inspect(o,records[n]) for n,o in objects.items()}
    approval={}
    for old in lock['assets']:
        n=old['asset_id']
        if n not in records:continue
        r=records[n]
        approval[n]=all(r[k]==old[k] for k in ['bounds','dimensions','origin','connectors','geometry_sha256','material_slots']) and hashlib.sha256((out/r['filename']).read_bytes()).hexdigest()==lock['files'][old['filename']]
    snaps=[]
    if (out/'tests/assembly_joins.json').exists():
        scene=bpy.data.scenes['03_Offline_Multistorey_Atrium'];scene.view_layers[0].update()
        for pair in json.loads((out/'tests/assembly_joins.json').read_text()):
            endpoints=[]
            for key in ['a','b']:
                o=scene.objects[pair[key]];r=records[o.data.name];con=next(c for c in r['connectors'] if c['name']==pair[key+'_connector'])
                endpoints.append((o.matrix_world@Vector(con['position']),o.matrix_world.to_3x3()@Vector(con['direction']),con['profile']))
            error=(endpoints[0][0]-endpoints[1][0]).length;dot=endpoints[0][1].dot(endpoints[1][1])
            snaps.append(dict(**pair,error_metres=error,direction_dot=dot,passed=error<=.001 and dot<-.99999 and endpoints[0][2]==endpoints[1][2]))
    connector_checks={}
    for n,r in records.items():
        cs=r['connectors'];connector_checks[n]=bool(cs) and len({c['name'] for c in cs})==len(cs) and all(abs(Vector(c['direction']).length-1)<1e-6 and all(math.isfinite(x) for x in c['position']) for c in cs)
    clearance={}
    for n in ['ARCH_Round','ARCH_Point','ARCH_Segmental','ARCH_WideSpan','DOORWAY_Standard','DOORWAY_Wide','DOORWAY_Arched']:
        if n not in objects:continue
        o=objects[n];tree=BVHTree.FromPolygons([v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
        x=1 if n in ['DOORWAY_Standard','DOORWAY_Arched'] else 2 if n=='DOORWAY_Wide' else 0
        clearance[n]=all(tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)[0] is None for z in [.1,1,1.5])
    pipe_profiles={}
    for name in ['PIPE_Straight_1m','PIPE_Straight_2m','PIPE_Straight_4m','PIPE_Elbow45','PIPE_Elbow90','PIPE_Tee','PIPE_Cross','PIPE_Reducer','PIPE_ValveBody','PIPE_Ubend','PIPE_Riser','PIPE_Manifold']:
        if name not in objects:continue
        for con in records[name]['connectors']:
            if con['profile']!='pipe_od_0.2_id_0.16':continue
            center=Vector(con['position']);direction=Vector(con['direction']);points=[v.co-center for v in objects[name].data.vertices if abs((v.co-center).dot(direction))<1e-5 and (v.co-center).length<.101]
            counts=[sum(abs(p.length-r)<1e-5 for p in points) for r in [.1,.08]]
            # Confirm the polygonal silhouette itself, not just mean radius/count.
            ref=Vector((0,0,1)) if abs(direction.z)<.99 else Vector((0,1,0));u=ref.cross(direction).normalized();v=direction.cross(u)
            deviations=[]
            for r in [.1,.08]:
                ring=[p for p in points if abs(p.length-r)<1e-5]
                for j in range(32):
                    ideal=r*(u*math.cos(j*math.pi/16)+v*math.sin(j*math.pi/16));deviations.append(min([(ideal-p).length for p in ring] or [999]))
            pipe_profiles[name+':'+con['name']]=dict(passed=counts==[32,32] and max(deviations)<1e-5,outer_inner_vertices=counts,max_profile_error_metres=max(deviations))
    stair_match=None
    if VARIATION in objects and 'STAIR_Straight' in objects:
        def treads(obj):
            return sorted(set(tuple(round(float(n),6) for n in obj.data.vertices[i].co) for f in obj.data.polygons if f.normal.z>.999 for i in f.vertices))
        stair_match=treads(objects[VARIATION])==treads(objects['STAIR_Straight']) and records[VARIATION]['connectors'][0]['position']==[0,0,0] and records[VARIATION]['connectors'][1]['position']==[4,0,2]
    rt=roundtrip(out,objects,manifest['assets'])
    unique=len({r['geometry_sha256'] for r in records.values()})==len(records)
    inventory=set(records)==set(INVENTORY+[VARIATION]) if manifest['scope']!='single_asset' else len(records)==1
    file_checks={n:(out/r['source']).is_file() and (out/r['filename']).is_file() for n,r in records.items()}
    report=dict(scope=manifest['scope'],blender_version=bpy.app.version_string,inventory_pass=inventory,unique_geometry_pass=unique,assets=assets,approved_pilot_unchanged=approval,connectors=connector_checks,joins=snaps,opening_clearance=clearance,pipe_mating_profiles=pipe_profiles,stair_variation_treads_match_approved=stair_match,files=file_checks,fbx_roundtrip=rt,
        viewer_compatibility='UNVERIFIED; no viewer/domain access or uploads',uv_contract='2m/repeat; singular-value density tolerance +/-14%, exact base tile corners',collision='No collision certification. Separate pilot proposals unchanged; full collision set deferred.',limitations=['FBX importer is Blender, not DarkRide','No exhaustive self-intersection proof','Runtime materials, collision, FPS, texture persistence, loading and normal handedness untested'])
    report['offline_pass']=inventory and unique and all(v['passed'] for v in assets.values()) and all(approval.values()) and all(connector_checks.values()) and all(v['passed'] for v in snaps) and all(clearance.values()) and all(file_checks.values()) and all(v['passed'] for v in rt) and all(v['passed'] for v in pipe_profiles.values()) and stair_match is not False
    (out/'reports/validation.json').write_text(json.dumps(report,indent=2))
    failures=[n for n,v in assets.items() if not v['passed']]+['FBX:'+v['asset_id'] for v in rt if not v['passed']]
    print('OFFLINE_VALIDATION',report['offline_pass'],'FAILURES',failures,flush=True)
    if not report['offline_pass']:raise RuntimeError('Validation failed; reports/validation.json contains explicit failures')
    return report
