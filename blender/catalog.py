"""88 specification IDs plus one explicitly additional staircase variation."""
import math,re
from pathlib import Path
import bpy
from mathutils import Vector
from geometry import *
ROOT=Path(__file__).resolve().parents[1]
INVENTORY=[m.group(1).replace('\\_','_') for m in re.finditer(r'^\d+ (\S+)',(ROOT/'BRIEF.md').read_text(),re.M)]
VARIATION='STAIR_Straight_SlopingUnderside'
assert len(INVENTORY)==88
PILOT=['WALL_Flat_2x2','FLOOR_Tile_2x2','ARCH_Round','COLUMN_Round','PIPE_Straight_2m','PIPE_Elbow90','STAIR_Straight','BRIDGE_Flat_4m']
NOTES={}

def c(name,p,d,profile):return dict(name=name,position=list(p),direction=list(d),profile=profile,roll_reference=[1,0,0] if abs(d[2])>.99 else [0,0,1])
def ends(length,profile='linear',height=0):return [c('in',(0,0,0),(-1,0,0),profile),c('out',(length,0,height),(1,0,0),profile)]
def floor_connectors(size):return [c('west',(0,size/2,0),(-1,0,0),f'floor_edge_{size}m'),c('east',(size,size/2,0),(1,0,0),f'floor_edge_{size}m'),c('south',(size/2,0,0),(0,-1,0),f'floor_edge_{size}m'),c('north',(size/2,size,0),(0,1,0),f'floor_edge_{size}m')]

def arch(kind='round',width=2,spring=2,thickness=.3,depth=.3):
    r=width/2;n=16
    if kind=='point':
        half=[(r+width*math.cos(P-i*(P/3)/8),spring+width*math.sin(P-i*(P/3)/8)) for i in range(9)]
        curve=half+[(-x,z) for x,z in half[-2::-1]]
    else:
        rise=r if kind=='round' else .5
        curve=[(-r*math.cos(i*P/n),spring+rise*math.sin(i*P/n)) for i in range(n+1)]
    inner=[(-r,0)]+curve+[(r,0)]
    outer=[(-r-thickness,0)]+[(x*(1+thickness/r),spring+(z-spring)*(1+thickness/r)+thickness) for x,z in curve]+[(r+thickness,0)]
    # Outer spring shifted upward makes a thick lintel rather than coincident radial feet.
    return ring_frame(inner,outer,depth)

def sector(ri,ro,a0,a1,z0,z1,segments=2,mat='MAT_Concrete'):
    b=Mesh();angles=[a0+(a1-a0)*i/segments for i in range(segments+1)]
    def pt(r,a,z):return (r*math.cos(a),r*math.sin(a),z)
    for i in range(segments):
        a,t=angles[i:i+2]
        for z in [z0,z1]:b.face([pt(ri,a,z),pt(ro,a,z),pt(ro,t,z),pt(ri,t,z)],mat=mat)
        for r in [ri,ro]:
            chord=2*r*math.sin((a1-a0)/segments/2)
            b.face([pt(r,a,z0),pt(r,t,z0),pt(r,t,z1),pt(r,a,z1)],[(i*chord/2,z0/2),((i+1)*chord/2,z0/2),((i+1)*chord/2,z1/2),(i*chord/2,z1/2)],mat)
    for a in [a0,a1]:b.face([pt(ri,a,z0),pt(ro,a,z0),pt(ro,a,z1),pt(ri,a,z1)],mat=mat)
    return b.object('part')

def fluted_column():
    b=Mesh();n=32;radii=[.25 if i%2==0 else .21 for i in range(n)]
    profile=[(radii[i]*math.cos(2*P*i/n),radii[i]*math.sin(2*P*i/n)) for i in range(n)];distance=0
    for a,t in zip(profile,profile[1:]+profile[:1]):
        length=(Vector(t)-Vector(a)).length
        b.face([(a[0],a[1],0),(t[0],t[1],0),(t[0],t[1],2),(a[0],a[1],2)],[(distance/2,0),((distance+length)/2,0),((distance+length)/2,1),(distance/2,1)])
        distance+=length
    for z in [0,2]:b.face([(x,y,z) for x,y in profile])
    return b.object('part')

def hollow_branch(cross=False):
    outer=translate(cylinder(2,.1),(-1,0,0))
    branch=rotate(cylinder(2 if cross else 1,.1),P/2)
    if cross:translate(branch,(0,-1,0))
    boolean(outer,branch)
    hole=translate(cylinder(2.04,.08),(-1.02,0,0));boolean(outer,hole,'DIFFERENCE')
    hole=rotate(cylinder(2.04 if cross else 1.02,.08),P/2)
    if cross:translate(hole,(0,-1.02,0))
    boolean(outer,hole,'DIFFERENCE');return outer

def grille(ceiling=False):
    frame=rectangle_frame(1,1,.06,.08,'MAT_Metal')
    bars=[box((-.445,-.02,i*.1-.012,.445,.02,i*.1+.012),'MAT_Metal') for i in range(1,10)]
    obj=union([frame]+bars)
    if ceiling:rotate(obj,P/2,'X')
    return obj

def rounded_housing():
    shell=box((0,-.15,0,2,.15,.12),'MAT_Metal')
    boolean(shell,box((.08,-.1,-.02,1.92,.1,.08),'MAT_Metal'),'DIFFERENCE')
    # Diffuser meets the cavity boundary, with an air gap to its rear surface.
    diffuser=box((.09,-.09,.005,1.91,.09,.025),'MAT_Emissive')
    return combine([shell,diffuser])

def build(name):
    """Return a new identity-transform mesh and design connectors for a single ID."""
    con=[];note='';closed=True
    if name=='WALL_Flat_4x2':
        b=Mesh();b.face([(0,0,0),(4,0,0),(4,0,2),(0,0,2)],[(0,0),(2,0),(2,1),(0,1)],'MAT_Wall');obj=b.object(name,False);closed=False;con=ends(4,'wall_edge_2m')
    elif name=='WALL_Thick_2x2':obj=box((0,0,0,2,.2,2),'MAT_Wall');con=ends(2,'wall_edge_2m')
    elif name in ['WALL_InsideCorner','WALL_OutsideCorner']:
        sign=1 if name=='WALL_InsideCorner' else -1
        obj=union([box((0,0,0,2,.2,2),'MAT_Wall'),box((0,min(0,sign*2),0,.2,max(.2,sign*2),2),'MAT_Wall')])
        con=[c('x_end',(2,0,0),(1,0,0),'wall_edge_2m'),c('y_end',(0,sign*2,0),(0,sign,0),'wall_edge_2m')]
    elif name=='WALL_RecessedPanel':
        obj=box((0,0,0,2,.25,2),'MAT_Wall');boolean(obj,box((.2,-.02,.2,1.8,.12,1.8),'MAT_Wall'),'DIFFERENCE');con=ends(2,'wall_edge_2m')
    elif name=='WALL_LowPartition':obj=box((0,0,0,2,.2,1),'MAT_Wall');con=ends(2,'partition_edge_1m')
    elif name=='WALL_Curved90':
        obj=sector(2,2.2,0,P/2,0,2,12,'MAT_Wall');con=[c('start',(2,0,0),(0,-1,0),'wall_edge_2m'),c('end',(0,2,0),(-1,0,0),'wall_edge_2m')]
    elif name=='FLOOR_Tile_4x4':
        b=Mesh();b.face([(0,0,0),(4,0,0),(4,4,0),(0,4,0)],[(0,0),(2,0),(2,2),(0,2)],'MAT_Floor');obj=b.object(name,False);closed=False;con=floor_connectors(4)
    elif name=='FLOOR_RaisedPlatform':obj=box((0,0,-.4,2,2,0),'MAT_Floor');con=floor_connectors(2)
    elif name=='FLOOR_Ramp':obj=extrude([(0,-.2),(4,-.2),(4,1),(0,0)],2,'MAT_Floor');con=ends(4,'walkway_width_2m',1)
    elif name=='CEILING_Flat_2x2':
        b=Mesh();b.face([(0,2,0),(2,2,0),(2,0,0),(0,0,0)],[(0,1),(1,1),(1,0),(0,0)],'MAT_Ceiling');obj=b.object(name,False);closed=False;con=floor_connectors(2)
    elif name=='CEILING_Grid_2x2':
        # Raised grid cut into a continuous closed slab; no hidden intersecting beams.
        obj=box((0,0,0,2,2,.12),'MAT_Ceiling')
        for x in [0,1]:
            for y in [0,1]:boolean(obj,box((x+.05,y+.05,-.02,x+.95,y+.95,.07),'MAT_Ceiling'),'DIFFERENCE')
        con=floor_connectors(2)
    elif name=='CEILING_Vaulted':
        obj=sector(2,2.15,0,P,0,2,16,'MAT_Ceiling');rotate(obj,P/2,'X');translate(obj,(0,2,0));con=[c('front',(0,0,0),(0,-1,0),'vault_span_4m'),c('rear',(0,2,0),(0,1,0),'vault_span_4m')]
    elif name=='CEILING_Recessed':
        obj=box((0,0,0,2,2,.3),'MAT_Ceiling');boolean(obj,box((.2,.2,-.05,1.8,1.8,.2),'MAT_Ceiling'),'DIFFERENCE');con=floor_connectors(2)
    elif name in ['ARCH_Point','ARCH_Segmental','ARCH_WideSpan','ARCH_Double']:
        if name=='ARCH_Double':obj=combine([translate(arch(width=1.6,thickness=.2),(-1.1,0,0)),translate(arch(width=1.6,thickness=.2),(1.1,0,0))]);width=4.2
        else:
            width=4 if name=='ARCH_WideSpan' else 2
            obj=arch('point' if name=='ARCH_Point' else 'segmental' if name=='ARCH_Segmental' else 'round',width=width)
        con=[c('datum',(0,0,0),(0,0,-1),'floor_mount')];note='True opening; clear spring height 2m. Double variant is two closed portals with a deliberate 0.2m central separation.' if name=='ARCH_Double' else 'True opening; clear spring height 2m.'
    elif name=='COLUMN_Square':obj=box((-.25,-.25,0,.25,.25,2));con=[c('base',(0,0,0),(0,0,-1),'column_square_0.5m'),c('top',(0,0,2),(0,0,1),'column_square_0.5m')]
    elif name=='COLUMN_Fluted':obj=fluted_column();con=[c('base',(0,0,0),(0,0,-1),'column_diameter_0.5m'),c('top',(0,0,2),(0,0,1),'column_diameter_0.5m')]
    elif name=='PILASTER_Wall':obj=box((-.2,0,0,.2,.15,2));con=[c('mount',(0,0,0),(0,-1,0),'wall_mount')]
    elif name=='BEAM_Straight':obj=box((0,-.15,-.3,4,.15,0));con=ends(4,'beam_0.3m')
    elif name=='BEAM_Curved':obj=sector(2,2.3,0,P/2,-.3,0,12);con=[c('in',(2,0,0),(0,-1,0),'beam_0.3m'),c('out',(0,2,0),(-1,0,0),'beam_0.3m')]
    elif name=='CORNICE_Straight':
        obj=extrude([(0,0),(.2,0),(.2,.06),(.12,.14),(.08,.2),(0,.2)],2,'MAT_Trim');rotate(obj,P/2);translate(obj,(1,0,0));con=ends(2,'cornice_profile')
    elif name=='SKIRTING_Straight':obj=extrude([(0,0),(.06,0),(.06,.12),(.04,.16),(0,.16)],2,'MAT_Trim');rotate(obj,P/2);translate(obj,(1,0,0));con=ends(2,'skirting_profile')
    elif name=='TRIM_PanelFrame':obj=rectangle_frame(2,2,.08,.06);translate(obj,(1,0,0));con=[c('mount',(1,0,1),(0,1,0),'wall_mount')]
    elif name in ['DOORWAY_Standard','DOORWAY_Wide']:
        width=2 if name.endswith('Standard') else 4;opening=1.2 if width==2 else 2.4
        obj=ring_frame([(-opening/2,0),(-opening/2,2),(opening/2,2),(opening/2,0)],[(-width/2,0),(-width/2,2.4),(width/2,2.4),(width/2,0)],.2,'MAT_Wall');translate(obj,(width/2,0,0));con=ends(width,'wall_edge_2m');note=f'Clear aperture {opening}m wide x 2m tall; lintel height 2.4m.'
    elif name=='DOORWAY_Arched':obj=arch(width=1.2,spring=1.6,thickness=.4,depth=.2);translate(obj,(1,0,0));con=ends(2,'wall_edge_2m')
    elif name=='DOOR_Leaf_Plain':obj=box((0,-.025,0,1.2,.025,2),'MAT_Trim');con=[c('hinge',(0,0,0),(0,0,1),'door_hinge_2m')]
    elif name=='DOOR_Leaf_Industrial':
        obj=box((0,-.04,0,1.2,.04,2),'MAT_Metal')
        for z in [.3,.8,1.3]:boolean(obj,box((.1,-.06,z,1.1,-.02,z+.25),'MAT_Metal'),'DIFFERENCE')
        con=[c('hinge',(0,0,0),(0,0,1),'door_hinge_2m')]
    elif name=='DOOR_Frame':obj=rectangle_frame(1.4,2.1,.1,.15,bottom=False);translate(obj,(.7,0,0));con=[c('opening_center',(.7,0,0),(0,-1,0),'door_width_1.2m')]
    elif name=='DOOR_DoubleLeaf':obj=combine([box((0,-.03,0,1.195,.03,2),'MAT_Trim'),box((1.205,-.03,0,2.4,.03,2),'MAT_Trim')]);con=[c('left_hinge',(0,0,0),(0,0,1),'door_hinge_2m'),c('right_hinge',(2.4,0,0),(0,0,1),'door_hinge_2m')];note='Static two-leaf assembly with 10mm seam; runtime hinge motion not supplied.'
    elif name in ['WINDOW_Rectangular','WINDOW_Tall','WINDOW_InteriorObservation','WINDOW_FrameAndSill']:
        width,height=(1,2) if name=='WINDOW_Tall' else (4,1.2) if name=='WINDOW_InteriorObservation' else (2,1.2)
        obj=rectangle_frame(width,height,.1,.15)
        if name=='WINDOW_FrameAndSill':boolean(obj,box((-width/2-.1,-.3,-.1,width/2+.1,.15,.03),'MAT_Trim'))
        else:
            glass=box((-width/2+.11,-.012,.11,width/2-.11,.012,height-.11),'MAT_Glass');obj=combine([obj,glass])
        con=[c('sill_center',(0,0,0),(0,0,-1),'window_mount')];note='Checker diagnostic is opaque even in MAT_Glass; transparency must be configured/tested separately.'
    elif name=='WINDOW_Arched':
        inner=[(-.8,.1),(-.8,1)]+[(-.8*math.cos(P*i/12),1+.8*math.sin(P*i/12)) for i in range(1,13)]+[(.8,.1)]
        outer=[(-1,0),(-1,1)]+[(-math.cos(P*i/12),1+math.sin(P*i/12)) for i in range(1,13)]+[(1,0)]
        obj=ring_frame(inner,outer,.15,'MAT_Trim',True);con=[c('sill_center',(0,0,0),(0,0,-1),'window_mount')]
    elif name in ['PIPE_Straight_1m','PIPE_Straight_4m']:
        length=1 if '1m' in name else 4;obj=cylinder(length,inner=.08);con=ends(length,'pipe_od_0.2_id_0.16')
    elif name=='PIPE_Elbow45':
        lead=2-math.sqrt(2);angles=[P/4*i/6 for i in range(7)]
        path=[(0,0,0)]+[(lead+math.sin(t),1-math.cos(t),0) for t in angles]+[(2,1,0)]
        frames=[(0,1,0)]+[(-math.sin(t),math.cos(t),0) for t in angles]+[(-2**-.5,2**-.5,0)]
        obj=sweep(path,frames);con=[c('in',(0,0,0),(-1,0,0),'pipe_od_0.2_id_0.16'),c('out',(2,1,0),(2**-.5,2**-.5,0),'pipe_od_0.2_id_0.16')];note='Lead/tail straights put outlet on (2m,1m) grid; outlet tangent 45 degrees.'
    elif name in ['PIPE_Tee','PIPE_Cross']:
        obj=hollow_branch(name=='PIPE_Cross');con=[c('west',(-1,0,0),(-1,0,0),'pipe_od_0.2_id_0.16'),c('east',(1,0,0),(1,0,0),'pipe_od_0.2_id_0.16'),c('north',(0,1,0),(0,1,0),'pipe_od_0.2_id_0.16')]
        if name=='PIPE_Cross':con.append(c('south',(0,-1,0),(0,-1,0),'pipe_od_0.2_id_0.16'))
    elif name=='PIPE_Reducer':obj=cylinder(1,.1,inner=.08,radius_end=.05);con=[c('in',(0,0,0),(-1,0,0),'pipe_od_0.2_id_0.16'),c('out',(1,0,0),(1,0,0),'pipe_od_0.1_id_0.08')];note='Developed conical-sector UVs with one circumference seam; exact facet lengths and matching 32-sided end profiles.'
    elif name=='PIPE_Flange':obj=cylinder(.1,.2,inner=.08);con=ends(.1,'pipe_od_0.2_id_0.16')
    elif name=='PIPE_EndCap':obj=cylinder(.1,.1);con=[c('in',(0,0,0),(-1,0,0),'pipe_od_0.2_id_0.16')]
    elif name=='PIPE_ValveWheel':
        obj=cylinder(.05,.3,inner=.25)
        for bounds in [(0,-.27,-.025,.05,.27,.025),(0,-.025,-.27,.05,.025,.27)]:boolean(obj,box(bounds,'MAT_Metal'))
        con=[c('spindle',(0,0,0),(-1,0,0),'valve_spindle')]
    elif name=='PIPE_ValveBody':
        obj=union([cylinder(1,.1),translate(cylinder(.4,.2),(.3,0,0))]);boolean(obj,translate(cylinder(1.04,.08),(-.02,0,0)),'DIFFERENCE')
        stem=rotate(cylinder(.25,.04),P/2);translate(stem,(.5,.16,0));boolean(obj,stem);con=ends(1,'pipe_od_0.2_id_0.16')+[c('spindle',(.5,.41,0),(0,1,0),'valve_spindle')]
    elif name=='PIPE_Bracket':
        obj=sector(.105,.14,0,P,0,.1,8,'MAT_Metal');rotate(obj,P/2,'Y');boolean(obj,box((-.02,-.2,-.03,.12,.2,.01),'MAT_Metal'));con=[c('mount',(0,0,0),(0,0,-1),'service_mount')]
    elif name=='PIPE_Ubend':obj=arc_tube(P);con=[c('in',(0,0,0),(-1,0,0),'pipe_od_0.2_id_0.16'),c('out',(0,2,0),(-1,0,0),'pipe_od_0.2_id_0.16')]
    elif name=='PIPE_Riser':obj=rotate(cylinder(2,inner=.08),-P/2,'Y');con=[c('bottom',(0,0,0),(0,0,-1),'pipe_od_0.2_id_0.16'),c('top',(0,0,2),(0,0,1),'pipe_od_0.2_id_0.16')]
    elif name=='PIPE_Manifold':
        obj=cylinder(4,.1)
        for x in [1,2,3]:boolean(obj,translate(rotate(cylinder(1,.1),P/2),(x,0,0)))
        boolean(obj,translate(cylinder(4.04,.08),(-.02,0,0)),'DIFFERENCE')
        for x in [1,2,3]:boolean(obj,translate(rotate(cylinder(1.02,.08),P/2),(x,0,0)),'DIFFERENCE')
        con=ends(4,'pipe_od_0.2_id_0.16')+[c(f'branch_{x}',(x,1,0),(0,1,0),'pipe_od_0.2_id_0.16') for x in [1,2,3]]
    elif name in ['DUCT_Square_1m','DUCT_Square_2m']:
        length=1 if '1m' in name else 2;obj=sweep([(0,0,0),(length,0,0)],[(0,1,0)]*2,.25,.22,square=True);con=ends(length,'duct_square_0.5m')
    elif name=='DUCT_Elbow90':obj=arc_tube(radius=1,outer=.25,inner=.22,square=True);con=[c('in',(0,0,0),(-1,0,0),'duct_square_0.5m'),c('out',(1,1,0),(0,1,0),'duct_square_0.5m')]
    elif name=='DUCT_Tee':
        obj=union([box((-1,-.25,-.25,1,.25,.25),'MAT_Metal'),box((-.25,0,-.25,.25,1,.25),'MAT_Metal')])
        boolean(obj,box((-1.02,-.22,-.22,1.02,.22,.22),'MAT_Metal'),'DIFFERENCE');boolean(obj,box((-.22,0,-.22,.22,1.02,.22),'MAT_Metal'),'DIFFERENCE')
        con=[c('west',(-1,0,0),(-1,0,0),'duct_square_0.5m'),c('east',(1,0,0),(1,0,0),'duct_square_0.5m'),c('north',(0,1,0),(0,1,0),'duct_square_0.5m')]
    elif name=='DUCT_Reducer':
        b=Mesh()
        def ring(x,r):return [(x,-r,-r),(x,r,-r),(x,r,r),(x,-r,r)]
        for ri in [0,.03]:
            a,t=ring(0,.25-ri),ring(1,.15-ri)
            for j in range(4):b.face([a[j],t[j],t[(j+1)%4],a[(j+1)%4]],mat='MAT_Metal')
        for x,r in [(0,.25),(1,.15)]:
            a,t=ring(x,r),ring(x,r-.03)
            for j in range(4):b.face([a[j],t[j],t[(j+1)%4],a[(j+1)%4]],mat='MAT_Metal')
        obj=b.object(name);con=[c('in',(0,0,0),(-1,0,0),'duct_square_0.5m'),c('out',(1,0,0),(1,0,0),'duct_square_0.3m')]
    elif name=='DUCT_EndCap':obj=box((0,-.25,-.25,.05,.25,.25),'MAT_Metal');con=[c('in',(0,0,0),(-1,0,0),'duct_square_0.5m')]
    elif name in ['VENT_WallGrille','VENT_CeilingGrille']:obj=grille(name=='VENT_CeilingGrille');con=[c('mount',(0,0,0),(0,-1,0) if name=='VENT_WallGrille' else (0,0,1),'vent_1m')]
    elif name=='VENT_FanHousing':
        obj=cylinder(.3,.5,inner=.43,n=24);blades=[cylinder(.3,.1)]
        for i in range(5):
            blade=box((.12,.06,-.04,.18,.44,.04),'MAT_Metal');rotate(blade,i*2*P/5,'X');blades.append(blade)
        obj=combine([obj,union(blades)]);con=ends(.3,'fan_diameter_1m');note='Static fan blades; moving component and motor not included.'
    elif name=='DUCT_Hanger':
        obj=union([box((-.05,-.35,-.05,.05,.35,0),'MAT_Metal'),box((-.025,-.35,-.02,.025,-.3,1),'MAT_Metal'),box((-.025,.3,-.02,.025,.35,1),'MAT_Metal')]);con=[c('ceiling_left',(0,-.325,1),(0,0,1),'service_mount'),c('ceiling_right',(0,.325,1),(0,0,1),'service_mount')]
    elif name==VARIATION:
        obj=stair_sloped();con=[c('bottom',(0,0,0),(-1,0,0),'walkway_width_2m'),c('top',(4,0,2),(1,0,0),'walkway_width_2m')];note='Same tread geometry/approach datums as approved straight stair. Closed underside z=0.5*x-0.2; 0.2m vertical waist at each tread nose. Bottom extends 0.2m below approach datum.'
    elif name=='STAIR_Switchback':
        first=stair_sloped(5);second=translate(rotate(stair_sloped(5),P),(2,3,1));b=Mesh()
        for part in [first,second]:
            for f in part.data.polygons:
                points=[tuple(part.data.vertices[v].co) for v in f.vertices]
                if all(abs(p[0]-2)<1e-6 for p in points) and (part==first or max(p[2] for p in points)<=1.000001):continue
                b.face(points,[tuple(part.data.uv_layers.active.data[i].uv) for i in f.loop_indices],part.data.materials[f.material_index].name)
            bpy.data.objects.remove(part,do_unlink=True)
        for i,(a,t) in enumerate([(-1,1),(1,2),(2,4)]):
            for z in [.8,1]:b.face([(2,a,z),(4,a,z),(4,t,z),(2,t,z)],mat='MAT_Floor')
            b.face([(4,a,.8),(4,t,.8),(4,t,1),(4,a,1)])
            if i==1:b.face([(2,a,.8),(2,t,.8),(2,t,1),(2,a,1)])
        for y in [-1,4]:b.face([(2,y,.8),(4,y,.8),(4,y,1),(2,y,1)])
        obj=b.object(name);con=[c('bottom',(0,0,0),(-1,0,0),'walkway_width_2m'),c('top',(0,3,2),(-1,0,0),'walkway_width_2m')];note='Two 2m-wide flights separated by 1m void; 5m-wide turning landing, 2m total rise. Welded boundary with internal end caps omitted.'
    elif name=='STAIR_Spiral':
        b=Mesh()
        def q(r,a,z):return (r*math.cos(a),r*math.sin(a),z)
        for i in range(20):
            a=i*P/10;t=(i+1)*P/10;h=i*.2
            for r in [.5,2]:
                A=q(r,a,h-.2);B=q(r,t,h);C=q(r,t,h+.2);D=q(r,a,h+.2);E=q(r,a,h)
                b.face([A,B,C,E]);b.face([E,C,D])
            A=q(.5,a,h-.2);B=q(2,a,h-.2);C=q(2,t,h);D=q(.5,t,h)
            b.face([A,B,C]);b.face([A,C,D])
            b.face([q(.5,a,h+.2),q(2,a,h+.2),q(2,t,h+.2),q(.5,t,h+.2)],mat='MAT_Floor')
            b.face([q(.5,a,h),q(2,a,h),q(2,a,h+.2),q(.5,a,h+.2)])
        b.face([q(.5,0,-.2),q(2,0,-.2),q(2,0,0),q(.5,0,0)])
        b.face([q(.5,2*P,3.8),q(2,2*P,3.8),q(2,2*P,4),q(.5,2*P,4)])
        obj=b.object(name);con=[c('bottom',(1.25,0,0),(0,-1,0),'spiral_walkway_1.5m'),c('top',(1.25,0,4),(0,1,0),'spiral_walkway_1.5m')];note='Closed stepped helical slab, 20 radial treads, 0.2m rise, full turn, 2m radius, 4m storey rise. Structural support and collision require review; no central post.'
    elif name=='STAIR_Landing':obj=box((0,-1,-.2,2,1,0),'MAT_Floor');con=ends(2,'walkway_width_2m')
    elif name=='STAIR_Railing':obj=rail(4,1,2);con=ends(4,'railing_1m',2)
    elif name=='BRIDGE_Arched':
        # Shallow parabolic deck; metric projections on each planar strip preserve density.
        profile=[(i*.5,.5*(1-((i*.5-2)/2)**2)) for i in range(9)]
        obj=extrude([(x,z-.2) for x,z in profile]+list(reversed(profile)),2,'MAT_Floor');con=ends(4,'walkway_width_2m');note='Shallow 0.5m crown, 4m span, 0.2m deck; ends at zero deck height.'
    elif name=='BRIDGE_Catwalk':obj=union([box((0,-1,-.2,4,1,0),'MAT_Floor'),translate(rail(),(0,-.96,0)),translate(rail(),(0,.96,0))]);con=ends(4,'walkway_width_2m')
    elif name=='ELEVATOR_ShaftSegment':
        obj=box((-2,-2,0,2,2,4));boolean(obj,box((-1.8,-1.8,-.02,1.8,1.8,4.02)),'DIFFERENCE');boolean(obj,box((-.7,-2.02,0,.7,-1.7,2.2)),'DIFFERENCE');con=[c('bottom',(0,0,0),(0,0,-1),'shaft_4m'),c('top',(0,0,4),(0,0,1),'shaft_4m')]
    elif name=='ELEVATOR_CabShell':
        obj=box((-1,-1,0,1,1,2.4),'MAT_Metal');boolean(obj,box((-.9,-.9,.1,.9,.9,2.3),'MAT_Metal'),'DIFFERENCE');boolean(obj,box((-.7,-1.02,.1,.7,-.85,2.2),'MAT_Metal'),'DIFFERENCE');con=[c('floor',(0,0,.1),(0,0,-1),'elevator_cab')];note='Static shell, open doorway, no elevator motion or door controller.'
    elif name=='LIGHT_FluorescentHousing':obj=rounded_housing();con=[c('mount',(1,0,.12),(0,0,1),'ceiling_mount')]
    elif name=='LIGHT_RecessedPanel':
        obj=box((0,0,0,1,1,.1),'MAT_Metal');boolean(obj,box((.05,.05,-.01,.95,.95,.06),'MAT_Metal'),'DIFFERENCE');obj=combine([obj,box((.06,.06,0,.94,.94,.02),'MAT_Emissive')]);con=[c('mount',(.5,.5,.1),(0,0,1),'ceiling_mount')]
    elif name=='LIGHT_WallSconce':obj=combine([box((-.15,0,0,.15,.05,.5),'MAT_Metal'),box((-.12,-.16,.1,.12,-.02,.4),'MAT_Emissive')]);con=[c('mount',(0,.05,.25),(0,1,0),'wall_mount')]
    elif name=='LIGHT_IndustrialCage':
        cage=rotate(cylinder(.05,.25),-P/2,'Y');parts=[cage,translate(rotate(cylinder(.05,.25),-P/2,'Y'),(0,0,.55))]
        for i in range(8):
            a=i*P/4;parts.append(translate(rotate(cylinder(.55,.015,n=6),-P/2,'Y'),(.23*math.cos(a),.23*math.sin(a),.025)))
        obj=combine([union(parts),translate(rotate(cylinder(.4,.12,n=12,mat='MAT_Emissive'),-P/2,'Y'),(0,0,.1))]);con=[c('mount',(0,0,.6),(0,0,1),'ceiling_mount')]
    elif name=='LIGHT_ExitSignHousing':
        obj=rectangle_frame(1,.4,.05,.1,'MAT_Metal');obj=combine([obj,box((-.44,-.02,.06,.44,.02,.34),'MAT_Emissive')]);con=[c('mount',(0,0,.4),(0,0,1),'ceiling_mount')];note='Blank sign housing. Lettering and emissive/runtime behavior intentionally separate.'
    elif name=='DETAIL_CableTray':
        obj=union([box((0,-.25,0,2,.25,.03),'MAT_Metal'),box((0,-.25,0,2,-.22,.15),'MAT_Metal'),box((0,.22,0,2,.25,.15),'MAT_Metal')]);con=ends(2,'tray_width_0.5m')
    elif name=='DETAIL_WallConduit':obj=cylinder(2,.025,n=8,inner=.018);con=ends(2,'conduit_od_0.05m')
    elif name=='DETAIL_ServiceHatch':
        obj=rectangle_frame(1,1,.08,.08,'MAT_Metal');obj=combine([obj,box((-.41,-.015,.09,.41,.015,.91),'MAT_Metal')]);con=[c('mount',(0,0,.5),(0,1,0),'wall_mount')]
    elif name=='DETAIL_BalconyRail':obj=rail(2,1.1);con=ends(2,'railing_1.1m')
    elif name=='DETAIL_ColumnBase':
        obj=union([box((-.4,-.4,0,.4,.4,.1)),translate(rotate(cylinder(.2,.3,n=16,mat='MAT_Concrete'),-P/2,'Y'),(0,0,.08))]);con=[c('bottom',(0,0,0),(0,0,-1),'floor_mount'),c('top',(0,0,.28),(0,0,1),'column_diameter_0.5m')]
    else:raise KeyError(name)
    obj.name=name;obj.data.name=name;obj['asset_id']=name;obj['closed']=closed
    if closed:cleanup(obj)
    NOTES[name]=note
    return obj,con,note
