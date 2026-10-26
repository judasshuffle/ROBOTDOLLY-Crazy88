"""Complete offline kit. --no-render, --asset ID, --output PATH, --validate-only supported.
Single-asset mode defaults to individual/ID and never rewrites master or approved pilot.
"""
import argparse,hashlib,json,math,shutil,sys,traceback
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];PILOT_ROOT=ROOT/'approved_pilot'
sys.path.insert(0,str(Path(__file__).parent))
import geometry as g
import catalog

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(obj):
    data=dict(vertices=[list(v.co) for v in obj.data.vertices],faces=[list(p.vertices) for p in obj.data.polygons],uv=[list(u.uv) for u in obj.data.uv_layers.active.data])
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
def bounds(obj):return dict(min=[min(v.co[i] for v in obj.data.vertices) for i in range(3)],max=[max(v.co[i] for v in obj.data.vertices) for i in range(3)])
def verify_lock():
    lock=json.loads((ROOT/'reports/pilot_lock.json').read_text())
    for path,sha in lock['files'].items():
        if digest(PILOT_ROOT/path)!=sha:raise RuntimeError('Approved pilot changed: '+path)
        if (ROOT.parent/'manifest.json').exists() and digest(ROOT.parent/path)!=sha:raise RuntimeError('Original pilot changed: '+path)
    return lock
def setup(scene):
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new(scene.name+'_World');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.11,.15,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
    scene.view_settings.view_transform='AgX'
def camera(target,size,direction=(1.25,-1.7,1.1)):
    scene=bpy.context.scene;data=bpy.data.cameras.new('ReviewCamera');obj=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(obj)
    obj.location=Vector(target)+Vector(direction).normalized()*size*2.8;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=size;scene.camera=obj
    ld=bpy.data.lights.new('Softbox','AREA');lo=bpy.data.objects.new('Softbox',ld);scene.collection.objects.link(lo);lo.location=Vector(target)+Vector((size,-size,size*2*(1 if direction[2]>=0 else -1)));lo.rotation_euler=(Vector(target)-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=150*size*size;ld.shape='DISK';ld.size=size*1.3
    return obj,lo
def render(path):bpy.context.scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
def export(obj,path):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,use_mesh_modifiers=True,use_triangles=True,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE',use_custom_props=True)
def instance(obj,name,xyz,rotation=0):
    inst=bpy.data.objects.new(name,obj.data);bpy.context.scene.collection.objects.link(inst);inst.matrix_world=Matrix.Translation(Vector(xyz))@Matrix.Rotation(rotation,4,'Z');return inst

def load_pilot(name):
    with bpy.data.libraries.load(str(PILOT_ROOT/'blender/crazy88.blend'),link=False) as (src,dst):dst.objects=[name]
    obj=dst.objects[0];bpy.context.scene.collection.objects.link(obj)
    # Names are shared globally; relink to identical checker materials without changing mesh/UVs.
    for i,mat in enumerate(obj.data.materials):obj.data.materials[i]=g.MATERIALS[mat.name.split('.')[0]]
    obj.name=name;obj.data.name=name;return obj

def make_showcases(objects,out,do_render):
    gallery=bpy.data.scenes.new('02_Labelled_89_Asset_Gallery');bpy.context.window.scene=gallery;setup(gallery)
    for i,(name,obj) in enumerate(objects.items()):
        x=(i%10)*8;y=(i//10)*8
        instance(obj,'DISPLAY_'+name,(x,y,0))
        data=bpy.data.curves.new('Label','FONT');data.body=f'{i+1:02d}  {name}';data.size=.25;data.align_x='LEFT'
        label=bpy.data.objects.new('LABEL_'+name,data);gallery.collection.objects.link(label);label.location=(x-1,y-2,.01)
    camera((35,30,0),105,(.3,-1.5,1.7));gallery.render.resolution_x=2000;gallery.render.resolution_y=1600
    if do_render:render(out/'previews/gallery.png')
    scene=bpy.data.scenes.new('03_Offline_Multistorey_Atrium');bpy.context.window.scene=scene;setup(scene)
    placed={};joins=[]
    def put(asset,name,xyz,rotation=0):placed[name]=instance(objects[asset],name,xyz,rotation);return placed[name]
    def join(a,ac,b,bc):joins.append(dict(a=a,a_connector=ac,b=b,b_connector=bc))
    # 16x16m floor; central 8x8m reserved void on the upper level, avoiding a baked monolith.
    for x in range(-8,8,4):
        for y in range(-8,8,4):
            put('FLOOR_Tile_4x4',f'ground_{x}_{y}',(x,y,0))
            if x in [-8,4] or y in [-8,4]:put('FLOOR_Tile_4x4',f'upper_{x}_{y}',(x,y,4))
    # Two 2m rises give a route to the upper gallery; a landing joins the flights.
    put(catalog.VARIATION,'flight_1',(-6,-3,0));put('STAIR_Landing','landing',(-2,-3,2));put(catalog.VARIATION,'flight_2',(0,-3,2))
    join('flight_1','top','landing','in');join('landing','out','flight_2','bottom')
    put('BRIDGE_Flat_4m','bridge_A',(-4,1,4));put('BRIDGE_Flat_4m','bridge_B',(0,1,4));join('bridge_A','end','bridge_B','start')
    for x in [-4,0,4]:
        for z in [-.2,1.8]:put('COLUMN_Round',f'support_{x}_{z}',(x,1,z))
    for y in [-7,7]:
        for x in [-5,-1,3]:put('ARCH_Point',f'arch_{x}_{y}',(x,y,0))
    for x in range(-8,8,2):
        put('WALL_Thick_2x2',f'wall_{x}',(x,8,0));put('WALL_Thick_2x2',f'wallupper_{x}',(x,8,2))
    put('PIPE_Straight_4m','pipe_4',(-4,6,5));put('PIPE_Elbow90','pipe_elbow',(0,6,5));put('PIPE_Straight_2m','pipe_2',(1,7,5),math.pi/2)
    join('pipe_4','out','pipe_elbow','in');join('pipe_elbow','out','pipe_2','in')
    put('DUCT_Square_2m','duct_A',(-4,4,5));put('DUCT_Square_2m','duct_B',(-2,4,5));join('duct_A','out','duct_B','in')
    put('DUCT_Elbow90','duct_elbow',(0,4,5));join('duct_B','out','duct_elbow','in')
    put('ELEVATOR_ShaftSegment','shaft_lower',(7,-6,0));put('ELEVATOR_ShaftSegment','shaft_upper',(7,-6,4));join('shaft_lower','top','shaft_upper','bottom')
    # Separate 1m-scale diagnostic objects, not additional asset definitions.
    put('WALL_Flat_2x2','wall_join_A',(-4,10,0));put('WALL_Flat_2x2','wall_join_B',(-2,10,0));join('wall_join_A','right','wall_join_B','left')
    put('FLOOR_Tile_2x2','tile_join_A',(-4,10,0));put('FLOOR_Tile_2x2','tile_join_B',(-2,10,0));join('tile_join_A','east','tile_join_B','west')
    camera((0,1,2),28,(1,-1.5,1.2));scene.render.resolution_x=1800;scene.render.resolution_y=1400
    scene.view_layers[0].update()
    if do_render:render(out/'previews/atrium.png')
    (out/'tests/assembly_joins.json').write_text(json.dumps(joins,indent=2))
    return scene,joins

def main():
    p=argparse.ArgumentParser();p.add_argument('--asset',choices=catalog.INVENTORY+[catalog.VARIATION]);p.add_argument('--output',type=Path);p.add_argument('--no-render',action='store_true');p.add_argument('--validate-only',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    lock=verify_lock();out=args.output or (ROOT/'individual'/args.asset if args.asset else ROOT)
    out=out.resolve()
    if not out.is_relative_to(ROOT.resolve()) or out.is_relative_to(PILOT_ROOT.resolve()):raise ValueError('Output must remain in phase2 and outside approved_pilot')
    if args.asset and out==ROOT.resolve():raise ValueError('Single-asset regeneration must use an isolated output folder')
    for folder in ['meshes','sources','previews/uv_checks','reports','tests','blender']: (out/folder).mkdir(parents=True,exist_ok=True)
    from validate import validate
    if args.validate_only:
        manifest=json.loads((out/'manifest.json').read_text());objects={r['asset_id']:bpy.data.objects[r['asset_id']] for r in manifest['assets']};validate(out,objects,manifest,lock);return
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.name='01_Authoritative_Local_Origins';setup(scene)
    checker=bpy.data.images.load(str(ROOT/'textures/checker/labelled_checker.png'));checker.pack()
    for name in ['MAT_Wall','MAT_Floor','MAT_Ceiling','MAT_Concrete','MAT_Metal','MAT_Trim','MAT_Glass','MAT_Emissive']:
        mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.use_fake_user=True
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=checker;node.extension='REPEAT';bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.65
        mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color']);g.MATERIALS[name]=mat
    objects={};records=[];errors=[];locked={r['asset_id']:r for r in lock['assets']}
    for index,name in enumerate([args.asset] if args.asset else catalog.INVENTORY+[catalog.VARIATION]):
        print('BUILD',index+1,name,flush=True)
        try:
            if name in locked:obj=load_pilot(name);con=locked[name]['connectors'];note='Approved pilot; original geometry, UVs, connectors and FBX preserved.'
            else:obj,con,note=catalog.build(name)
            obj.data.calc_loop_triangles();bb=bounds(obj);fp=fingerprint(obj)
            if name in locked:assert fp==locked[name]['geometry_sha256'],f'Approved mesh changed: {name}'
            rec=dict(asset_id=name,inventory_number=catalog.INVENTORY.index(name)+1 if name in catalog.INVENTORY else None,additional_variation=name==catalog.VARIATION,filename=f'meshes/{name}.fbx',source=f'sources/{name}.blend',bounds=bb,dimensions=[bb['max'][i]-bb['min'][i] for i in range(3)],origin=[0,0,0],connectors=con,material_slots=[m.name for m in obj.data.materials],uv_metres_per_repeat=2,checker_pixels_per_metre=256,triangles=len(obj.data.loop_triangles),vertices=len(obj.data.vertices),quads=sum(len(f.vertices)==4 for f in obj.data.polygons),ngons=sum(len(f.vertices)>4 for f in obj.data.polygons),closed=bool(obj.get('closed',True)),geometry_sha256=fp,approved_pilot=name in locked,export_status='Blender_roundtrip_candidate_DarkRide_unverified',notes=note)
            rec['boolean_uv_reprojected_faces']=int(obj.get('boolean_uv_reprojected_faces',0))
            if name in locked:shutil.copy2(PILOT_ROOT/locked[name]['filename'],out/rec['filename'])
            else:export(obj,out/rec['filename'])
            bpy.data.libraries.write(str(out/rec['source']),{obj},fake_user=True,compress=True)
            rec['fbx_sha256']=digest(out/rec['filename']);records.append(rec);objects[name]=obj;obj.hide_render=True
        except Exception as e:errors.append(dict(asset_id=name,error=str(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
    manifest=dict(schema_version=2,scope='single_asset' if args.asset else '88_assets_plus_one_stair_variation',units='metres',axes='Blender Z up; FBX Y up, -Z forward',modular_grid='2m architectural bays; 1m service routes; documented fractional profiles and mounts',snap_tolerance_metres=.001,assets=records)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2));(out/'reports/generation_failures.json').write_text(json.dumps(errors,indent=2))
    if errors:raise RuntimeError(f'{len(errors)} asset generation failures; see generation_failures.json')
    if not args.no_render:
        for name,obj in objects.items():
            print('RENDER',name,flush=True);obj.hide_render=False;bb=bounds(obj);center=[(a+b)/2 for a,b in zip(bb['min'],bb['max'])]
            size=max(max(bb['max'][i]-bb['min'][i] for i in range(3))*1.45,.3)
            direction=(1.25,-1.7,1.1)
            if name.startswith('CEILING') or name in ['LIGHT_FluorescentHousing','LIGHT_RecessedPanel']:direction=(1.25,-1.7,-1.1)
            cam,light=camera(center,size,direction);render(out/'previews/uv_checks'/f'{name}.png');bpy.data.objects.remove(cam,do_unlink=True);bpy.data.objects.remove(light,do_unlink=True)
            if name==catalog.VARIATION:
                cam,light=camera(center,size,(1.25,-1.7,-1.1));render(out/'previews/stair_underside.png');bpy.data.objects.remove(cam,do_unlink=True);bpy.data.objects.remove(light,do_unlink=True)
            obj.hide_render=True
    for obj in objects.values():obj.hide_render=False
    if not args.asset:make_showcases(objects,out,not args.no_render)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'blender/crazy88_master.blend'),compress=True)
    validate(out,objects,manifest,lock)
    verify_lock();print('PHASE2_COMPLETE',len(objects),flush=True)

if __name__=='__main__':main()
