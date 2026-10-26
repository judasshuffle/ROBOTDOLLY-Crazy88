"""Eight-asset offline pilot. Blender 4.5: --background --factory-startup --python generate.py
Optional script arguments: -- --no-render. No networking or domain operations.
"""
import bpy, bmesh, math, json, sys, hashlib
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).parent))
from validate import validate_assets
PI=math.pi
ASSETS=['WALL_Flat_2x2','FLOOR_Tile_2x2','ARCH_Round','COLUMN_Round','PIPE_Straight_2m','PIPE_Elbow90','STAIR_Straight','BRIDGE_Flat_4m']

class Builder:
    def __init__(self): self.v=[]; self.f=[]; self.uv=[]; self.lookup={}
    def face(self,points,uv=None):
        ids=[]
        for p in points:
            key=tuple(round(float(n),8) for n in p)
            if key not in self.lookup: self.lookup[key]=len(self.v); self.v.append(key)
            ids.append(self.lookup[key])
        self.f.append(ids)
        if uv is None:
            normal=(Vector(points[1])-Vector(points[0])).cross(Vector(points[2])-Vector(points[0]))
            axis=max(range(3),key=lambda i:abs(normal[i]))
            axes={0:(1,2),1:(0,2),2:(0,1)}[axis]
            uv=[(p[axes[0]]/2,p[axes[1]]/2) for p in points]
        self.uv.append(uv)
    def object(self,name,mat,closed=True):
        mesh=bpy.data.meshes.new(name); mesh.from_pydata(self.v,[],self.f); mesh.update()
        layer=mesh.uv_layers.new(name='UVMap')
        for poly,uvs in zip(mesh.polygons,self.uv):
            for i,uv in zip(poly.loop_indices,uvs): layer.data[i].uv=uv
        if closed:
            bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
        obj=bpy.data.objects.new(name,mesh); bpy.context.scene.collection.objects.link(obj)
        mesh.materials.append(materials[mat]); obj['asset_id']=name; obj['closed']=closed
        return obj

def box(name,x0,x1,y0,y1,z0,z1,mat):
    b=Builder(); p=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]: b.face([p[i] for i in f])
    return b.object(name,mat)

def arch():
    b=Builder(); steps=32
    inn=[(-1,0)]+[(math.cos(PI-i*PI/steps),2+math.sin(PI-i*PI/steps)) for i in range(steps+1)]+[(1,0)]
    outer=[(-1.3,0)]+[(1.3*math.cos(PI-i*PI/steps),2+1.3*math.sin(PI-i*PI/steps)) for i in range(steps+1)]+[(1.3,0)]
    def at(p,y):return (p[0],y,p[1])
    lengths=[0,0]
    for i in range(len(inn)-1):
        for y in [-.15,.15]:b.face([at(inn[i],y),at(inn[i+1],y),at(outer[i+1],y),at(outer[i],y)])
        for k,path in enumerate([inn,outer]):
            length=(Vector(path[i+1])-Vector(path[i])).length
            b.face([at(path[i],-.15),at(path[i+1],-.15),at(path[i+1],.15),at(path[i],.15)],[(lengths[k]/2,0),((lengths[k]+length)/2,0),((lengths[k]+length)/2,.15),(lengths[k]/2,.15)])
            lengths[k]+=length
    for i in [0,len(inn)-1]:b.face([at(inn[i],-.15),at(inn[i],.15),at(outer[i],.15),at(outer[i],-.15)])
    return b.object('ARCH_Round','MAT_Concrete')

def column():
    b=Builder(); n=32;r=.25; chord=2*r*math.sin(PI/n)
    for i in range(n):
        a=2*PI*i/n;c=2*PI*(i+1)/n
        b.face([(r*math.cos(a),r*math.sin(a),0),(r*math.cos(c),r*math.sin(c),0),(r*math.cos(c),r*math.sin(c),2),(r*math.cos(a),r*math.sin(a),2)],[(i*chord/2,0),((i+1)*chord/2,0),((i+1)*chord/2,1),(i*chord/2,1)])
    for z in [0,2]: b.face([(r*math.cos(2*PI*i/n),r*math.sin(2*PI*i/n),z) for i in range(n)])
    return b.object('COLUMN_Round','MAT_Concrete')

def pipe(elbow=False):
    b=Builder(); n=32; steps=24 if elbow else 1
    def p(i,j,r):
        t=(PI/2)*i/steps; a=2*PI*j/n
        if elbow:return (math.sin(t)-r*math.cos(a)*math.sin(t),1-math.cos(t)+r*math.cos(a)*math.cos(t),r*math.sin(a))
        return (2*i/steps,r*math.cos(a),r*math.sin(a))
    for r in [.1,.08]:
        for i in range(steps):
            for j in range(n):
                pts=[p(i,j,r),p(i+1,j,r),p(i+1,j+1,r),p(i,j+1,r)]
                # Centerline length avoids shear; inner/outer bend stretch is bounded to 11.2%.
                def uv(k,l):
                    u=(PI/2*k/steps) if elbow else 2*k/steps
                    return (u/2,l*2*r*math.sin(PI/n)/2)
                b.face(pts,[uv(i,j),uv(i+1,j),uv(i+1,j+1),uv(i,j+1)])
    for i in [0,steps]:
        for j in range(n):
            # Annular end caps close wall thickness, leaving the bore open.
            pts=[p(i,j,.08),p(i,j,.1),p(i,j+1,.1),p(i,j+1,.08)]
            t=PI/2*i/steps if elbow else 0
            b.face(pts,[((-q[0]*math.sin(t)+q[1]*math.cos(t))/2,q[2]/2) for q in pts])
    return b.object('PIPE_Elbow90' if elbow else 'PIPE_Straight_2m','MAT_Metal')

def stair():
    b=Builder()
    # Partition each side into non-overlapping vertical strips. Shared boundary vertices
    # match the neighboring strip and the tread/riser edges, avoiding T-junctions.
    for i in range(10):
        x=i*.4; h=i*.2; top=h+.2
        for y in [-1,1]:
            a=(x,y,0);c=(x+.4,y,0);d=(x+.4,y,top);e=(x,y,top);f=(x,y,h)
            b.face([a,c,d])
            if i: b.face([d,e,f]);b.face([d,f,a])
            else:b.face([d,e,a])
        b.face([(x,-1,0),(x+.4,-1,0),(x+.4,1,0),(x,1,0)])
        b.face([(x,-1,top),(x+.4,-1,top),(x+.4,1,top),(x,1,top)])
        b.face([(x,-1,h),(x,-1,top),(x,1,top),(x,1,h)])
    b.face([(4,-1,0),(4,1,0),(4,1,2),(4,-1,2)])
    return b.object('STAIR_Straight','MAT_Concrete')

def connector(name,pos,direction,profile):return dict(name=name,position=pos,direction=direction,profile=profile)
def bounds(obj):
    return dict(min=[min(v.co[i] for v in obj.data.vertices) for i in range(3)],max=[max(v.co[i] for v in obj.data.vertices) for i in range(3)])
def fingerprint(obj):
    data=dict(vertices=[list(v.co) for v in obj.data.vertices],faces=[list(p.vertices) for p in obj.data.polygons],uv=[list(u.uv) for u in obj.data.uv_layers.active.data])
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
def select(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
def export(obj,path):
    select(obj)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,use_mesh_modifiers=True,use_triangles=True,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE',use_custom_props=True)
def instance(obj,name,loc,rotation=0):
    new=bpy.data.objects.new(name,obj.data);bpy.context.scene.collection.objects.link(new);new.matrix_world=Matrix.Translation(Vector(loc))@Matrix.Rotation(rotation,4,'Z');return new
def setup_scene(scene):
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new(scene.name+' World');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.11,.15,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
    scene.view_settings.view_transform='AgX'
def camera_at(target,size,direction=(1.25,-1.7,1.1)):
    scene=bpy.context.scene; data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam)
    cam.location=Vector(target)+Vector(direction).normalized()*size*2.8;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=size;scene.camera=cam
    ld=bpy.data.lights.new('Softbox','AREA');lo=bpy.data.objects.new('Softbox',ld);scene.collection.objects.link(lo);lo.location=Vector(target)+Vector((size,-size,size*2));lo.rotation_euler=(Vector(target)-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=150*size*size;ld.shape='DISK';ld.size=size*1.3
    return cam,lo
def render(path):bpy.context.scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name='01_Pilot_Library';setup_scene(scene)
    checker=bpy.data.images.load(str(ROOT/'textures/checker/labelled_checker.png'));checker.pack()
    materials={}
    for name in ['MAT_Wall','MAT_Floor','MAT_Ceiling','MAT_Concrete','MAT_Metal','MAT_Trim','MAT_Glass','MAT_Emissive']:
        mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.use_fake_user=True
        bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.65
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=checker;tex.extension='REPEAT';mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);materials[name]=mat
    b=Builder();b.face([(0,0,0),(2,0,0),(2,0,2),(0,0,2)],[(0,0),(1,0),(1,1),(0,1)])
    wall=b.object(ASSETS[0],'MAT_Wall',False)
    b=Builder();b.face([(0,0,0),(2,0,0),(2,2,0),(0,2,0)],[(0,0),(1,0),(1,1),(0,1)])
    floor=b.object(ASSETS[1],'MAT_Floor',False)
    objects=[wall,floor,arch(),column(),pipe(),pipe(True),stair(),box(ASSETS[7],0,4,-1,1,-.2,0,'MAT_Floor')]
    conn={
      ASSETS[0]:[connector('left',[0,0,0],[-1,0,0],'wall_edge_2m'),connector('right',[2,0,0],[1,0,0],'wall_edge_2m')],
      ASSETS[1]:[connector('west',[0,1,0],[-1,0,0],'floor_edge_2m'),connector('east',[2,1,0],[1,0,0],'floor_edge_2m'),connector('south',[1,0,0],[0,-1,0],'floor_edge_2m'),connector('north',[1,2,0],[0,1,0],'floor_edge_2m')],
      ASSETS[2]:[connector('left_foot',[-1.15,0,0],[0,0,-1],'arch_foot_0.3m'),connector('right_foot',[1.15,0,0],[0,0,-1],'arch_foot_0.3m')],
      ASSETS[3]:[connector('bottom',[0,0,0],[0,0,-1],'column_diameter_0.5m'),connector('top',[0,0,2],[0,0,1],'column_diameter_0.5m')],
      ASSETS[4]:[connector('in',[0,0,0],[-1,0,0],'pipe_od_0.2_id_0.16'),connector('out',[2,0,0],[1,0,0],'pipe_od_0.2_id_0.16')],
      ASSETS[5]:[connector('in',[0,0,0],[-1,0,0],'pipe_od_0.2_id_0.16'),connector('out',[1,1,0],[0,1,0],'pipe_od_0.2_id_0.16')],
      ASSETS[6]:[connector('bottom',[0,0,0],[-1,0,0],'walkway_width_2m'),connector('top',[4,0,2],[1,0,0],'walkway_width_2m')],
      ASSETS[7]:[connector('start',[0,0,0],[-1,0,0],'walkway_width_2m'),connector('end',[4,0,0],[1,0,0],'walkway_width_2m')]}
    records=[]
    for obj in objects:
        obj.data.calc_loop_triangles(); bb=bounds(obj)
        record=dict(asset_id=obj.name,filename='meshes/'+obj.name+'.fbx',export_status='candidate_not_viewer_validated',bounds=bb,dimensions=[bb['max'][i]-bb['min'][i] for i in range(3)],origin=[0,0,0],connectors=conn[obj.name],material_slots=[m.name for m in obj.data.materials],uv_metres_per_repeat=2,checker_pixels_per_metre=256,triangles=len(obj.data.loop_triangles),vertices=len(obj.data.vertices),closed=bool(obj['closed']),geometry_sha256=fingerprint(obj),collision=None)
        records.append(record);export(obj,ROOT/record['filename'])
    manifest=dict(schema_version=1,scope='eight_asset_pilot_only',units='metres',axes='Blender X right, Y forward, Z up; FBX -Z forward, Y up',snap_tolerance_metres=.001,assets=records)
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    # Library retains every definition at its authoritative local origin. Render isolated views.
    for obj in objects:obj.hide_render=True
    if '--no-render' not in sys.argv:
        for obj in objects:
            obj.hide_render=False;bb=bounds(obj);center=[(a+b)/2 for a,b in zip(bb['min'],bb['max'])]
            size=max(record for record in [max(bb['max'][i]-bb['min'][i] for i in range(3))*1.45, .7])
            cam,light=camera_at(center,size)
            render(ROOT/'previews/uv_checks'/f'{obj.name}.png')
            bpy.data.objects.remove(cam,do_unlink=True);bpy.data.objects.remove(light,do_unlink=True);obj.hide_render=True
    for obj in objects:obj.hide_render=False
    # Dedicated assembly scene uses linked mesh data; no additional asset definitions.
    assembly=bpy.data.scenes.new('02_Assembly_Review');bpy.context.window.scene=assembly;setup_scene(assembly)
    joins=[]
    def inst(index,name,loc,rot=0):return instance(objects[index],name,loc,rot)
    def join(a,ac,b,bc):joins.append(dict(a=a.name,a_connector=ac,b=b.name,b_connector=bc))
    w1=inst(0,'wall_A',(-3,3,0));w2=inst(0,'wall_B',(-1,3,0));join(w1,'right',w2,'left')
    for x in range(-2,4):
        for y in range(-2,2):inst(1,f'tile_{x}_{y}',(x*2,y*2,0))
    join(assembly.objects['tile_0_0'],'east',assembly.objects['tile_1_0'],'west')
    inst(2,'clearance_arch',(-2,1,0));inst(3,'column_A',(2.25,-.65,0));inst(3,'column_B',(5.75,-.65,0))
    st=inst(6,'stairs',(-2,-2,0));br=inst(7,'bridge',(2,-2,2));join(st,'top',br,'start')
    # Supports meet bridge underside (1.8m), so columns stand on a -0.2m datum.
    assembly.objects['column_A'].location=(2.25,-2,-.2);assembly.objects['column_B'].location=(5.75,-2,-.2)
    p1=inst(4,'pipe_A',(-2,2,3.6));el=inst(5,'elbow',(0,2,3.6));p2=inst(4,'pipe_B',(1,3,3.6),PI/2)
    join(p1,'out',el,'in');join(el,'out',p2,'in')
    (ROOT/'tests/assembly_joins.json').write_text(json.dumps(joins,indent=2))
    camera_at((1,0,1.1),17,(1,-1.6,1.3));assembly.render.resolution_x=1500;assembly.render.resolution_y=1000
    if '--no-render' not in sys.argv:render(ROOT/'previews/assembly.png')
    # Separate opt-in collision proposals: no assigned collision behavior or exports.
    collision=bpy.data.scenes.new('03_Collision_Proposals');bpy.context.window.scene=collision;setup_scene(collision)
    wall_proxy=box('COL_WALL_Flat_2x2',0,2,0,.05,0,2,'MAT_Concrete')
    floor_proxy=box('COL_FLOOR_Tile_2x2',0,2,0,2,-.05,0,'MAT_Concrete')
    bridge_proxy=box('COL_BRIDGE_Flat_4m',0,4,-1,1,-.2,0,'MAT_Concrete')
    # Walking ramp follows the stair noses; proposal only, not claimed equivalent to steps.
    b=Builder();profile=[(0,0),(4,0),(4,2),(0,.2)]
    for y in [-1,1]:b.face([(x,y,z) for x,z in profile])
    for a,c in zip(profile,profile[1:]+profile[:1]):b.face([(a[0],-1,a[1]),(c[0],-1,c[1]),(c[0],1,c[1]),(a[0],1,a[1])])
    b.object('COL_STAIR_Straight_Ramp_Proposal','MAT_Concrete')
    bpy.context.window.scene=assembly
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/crazy88.blend'))
    validate_assets(ROOT,objects,manifest,assembly,joins)
    print('CRAZY88_PILOT_COMPLETE')
