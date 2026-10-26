"""Deterministic metre-based solids, sweeps and UVs. No network or domain access."""
import math
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
P=math.pi
MATERIALS={}

def metric_uv(points):
    """An orthonormal face basis, not dominant-axis flattening: slopes retain density."""
    pts=[Vector(p) for p in points]; normal=Vector((0,0,0))
    for a,b in zip(pts,pts[1:]+pts[:1]):normal+=a.cross(b)
    normal.normalize()
    # Project global X on non-X-facing planes, otherwise global Y; coplanar faces agree.
    axis=Vector((1,0,0)) if abs(normal.x)<.99 else Vector((0,1,0))
    u=(axis-normal*axis.dot(normal)).normalized()
    v=normal.cross(u)
    if abs(normal.z)<.99 and v.z<0:v=-v
    elif abs(normal.z)>=.99 and v.y<0:v=-v
    return [(p.dot(u)/2,p.dot(v)/2) for p in pts]

class Mesh:
    def __init__(self):self.vertices=[];self.faces=[];self.uv=[];self.mats=[];self.lookup={}
    def face(self,points,uv=None,mat='MAT_Concrete'):
        ids=[]
        for p in points:
            key=tuple(round(float(x),8) for x in p)
            if key not in self.lookup:self.lookup[key]=len(self.vertices);self.vertices.append(key)
            ids.append(self.lookup[key])
        if len(set(ids))!=len(ids):raise ValueError('Repeated face corner')
        self.faces.append(ids);self.uv.append(uv if uv is not None else metric_uv(points));self.mats.append(mat)
    def object(self,name,closed=True):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(self.vertices,[],self.faces);mesh.update()
        slots=list(dict.fromkeys(self.mats))
        for s in slots:mesh.materials.append(MATERIALS[s])
        uv=mesh.uv_layers.new(name='UVMap')
        for f,coords,mat in zip(mesh.polygons,self.uv,self.mats):
            f.material_index=slots.index(mat)
            for i,p in zip(f.loop_indices,coords):uv.data[i].uv=p
        if closed:
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj['closed']=closed
        return obj

def transform(obj,matrix):
    obj.data.transform(matrix);obj.data.update();return obj
def translate(obj,xyz):return transform(obj,Matrix.Translation(Vector(xyz)))
def rotate(obj,angle,axis='Z'):return transform(obj,Matrix.Rotation(angle,4,axis))
def box(bounds,mat='MAT_Concrete',name='part'):
    x0,y0,z0,x1,y1,z1=bounds
    p=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    b=Mesh()
    for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:b.face([p[i] for i in f],mat=mat)
    return b.object(name)

def combine(parts,name='part'):
    """Join spatially separated closed components without altering their UVs."""
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();parts[0].name=name
    return parts[0]

def boolean(a,b,operation='UNION'):
    bpy.context.view_layer.objects.active=a
    modifier=a.modifiers.new('constructive_'+operation,'BOOLEAN');modifier.operation=operation;modifier.solver='EXACT';modifier.object=b
    # Install shared slots before Boolean so incoming material identities are preserved.
    for mat in b.data.materials:
        if mat.name not in [m.name for m in a.data.materials]:a.data.materials.append(mat)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(b,do_unlink=True)
    return a
def union(parts):
    obj=parts[0]
    for part in parts[1:]:boolean(obj,part)
    return obj

def extrude(profile,depth,mat='MAT_Concrete',name='part'):
    """Closed x/z profile extruded symmetrically along Y; retains planar n-gon caps."""
    b=Mesh()
    for y in [-depth/2,depth/2]:b.face([(x,y,z) for x,z in profile],mat=mat)
    for a,c in zip(profile,profile[1:]+profile[:1]):b.face([(a[0],-depth/2,a[1]),(c[0],-depth/2,c[1]),(c[0],depth/2,c[1]),(a[0],depth/2,a[1])],mat=mat)
    return b.object(name)

def ring_frame(inner,outer,depth,mat='MAT_Concrete',closed_ring=False):
    b=Mesh();ends=len(inner) if closed_ring else len(inner)-1
    for i in range(ends):
        j=(i+1)%len(inner)
        for y in [-depth/2,depth/2]:b.face([(inner[i][0],y,inner[i][1]),(inner[j][0],y,inner[j][1]),(outer[j][0],y,outer[j][1]),(outer[i][0],y,outer[i][1])],mat=mat)
    for path in [inner,outer]:
        distance=0
        for i in range(ends):
            j=(i+1)%len(path);length=(Vector(path[j])-Vector(path[i])).length
            b.face([(path[i][0],-depth/2,path[i][1]),(path[j][0],-depth/2,path[j][1]),(path[j][0],depth/2,path[j][1]),(path[i][0],depth/2,path[i][1])],[(distance/2,0),((distance+length)/2,0),((distance+length)/2,depth/2),(distance/2,depth/2)],mat)
            distance+=length
    if not closed_ring:
        for i in [0,len(inner)-1]:b.face([(inner[i][0],-depth/2,inner[i][1]),(inner[i][0],depth/2,inner[i][1]),(outer[i][0],depth/2,outer[i][1]),(outer[i][0],-depth/2,outer[i][1])],mat=mat)
    return b.object('part')

def cylinder(length=1,radius=.1,n=32,inner=0,radius_end=None,mat='MAT_Metal'):
    """Along +X. Tapered radii use developed conical UV sectors (no stretched trapezoids)."""
    end=radius if radius_end is None else radius_end;b=Mesh()
    def pt(x,j,r):return (x,r*math.cos(2*P*j/n),r*math.sin(2*P*j/n))
    radii=[(radius,end)] + ([(inner,inner*end/radius)] if inner else [])
    for r0,r1 in radii:
        for j in range(n):
            points=[pt(0,j,r0),pt(length,j,r1),pt(length,j+1,r1),pt(0,j+1,r0)]
            # These are planar trapezoids. Develop each facet; contiguous strips for cylinders.
            if abs(r0-r1)<1e-10:
                chord=2*r0*math.sin(P/n);uv=[(0,j*chord/2),(length/2,j*chord/2),(length/2,(j+1)*chord/2),(0,(j+1)*chord/2)]
            else:
                slant=math.sqrt(length**2+(r0-r1)**2);R0=slant*r0/abs(r0-r1);R1=slant*r1/abs(r0-r1)
                beta=2*math.asin(r0*math.sin(P/n)/R0)
                uv=[(R*math.cos(k*beta)/2,R*math.sin(k*beta)/2) for R,k in [(R0,j),(R1,j),(R1,j+1),(R0,j+1)]]
            b.face(points,uv,mat)
    for x,r0,ri in [(0,radius,inner),(length,end,inner*end/radius)]:
        if inner:
            for j in range(n):b.face([pt(x,j,ri),pt(x,j,r0),pt(x,j+1,r0),pt(x,j+1,ri)],mat=mat)
        else:b.face([pt(x,j,r0) for j in range(n)],mat=mat)
    return b.object('part')

def sweep(path,frames,radius=.1,inner=.08,n=32,mat='MAT_Metal',square=False):
    """Planar path with explicit cross-section normals. Length follows the centerline."""
    b=Mesh();distance=[0]
    for a,c in zip(path,path[1:]):distance.append(distance[-1]+(Vector(c)-Vector(a)).length)
    def pt(i,j,r):
        if square:
            a,z=[(-1,-1),(1,-1),(1,1),(-1,1)][j%4];return Vector(path[i])+Vector(frames[i])*(a*r)+Vector((0,0,z*r))
        angle=2*P*j/n;return Vector(path[i])+Vector(frames[i])*(r*math.cos(angle))+Vector((0,0,r*math.sin(angle)))
    if square:n=4
    for r in [radius,inner]:
        perimeter_step=2*r if square else 2*r*math.sin(P/n)
        for i in range(len(path)-1):
            for j in range(n):
                points=[pt(i,j,r),pt(i+1,j,r),pt(i+1,j+1,r),pt(i,j+1,r)]
                if square:uv=metric_uv(points)
                else:uv=[(distance[i]/2,j*perimeter_step/2),(distance[i+1]/2,j*perimeter_step/2),(distance[i+1]/2,(j+1)*perimeter_step/2),(distance[i]/2,(j+1)*perimeter_step/2)]
                b.face(points,uv,mat)
    for i in [0,len(path)-1]:
        for j in range(n):b.face([pt(i,j,inner),pt(i,j,radius),pt(i,j+1,radius),pt(i,j+1,inner)],mat=mat)
    return b.object('part')

def arc_tube(angle=P/2,radius=1,outer=.1,inner=.08,square=False,steps=None):
    count=steps or max(4,round(angle/(P/2)*12))
    angles=[angle*i/count for i in range(count+1)]
    return sweep([(radius*math.sin(t),radius*(1-math.cos(t)),0) for t in angles],[(-math.sin(t),math.cos(t),0) for t in angles],outer,inner,square=square)

def stair_sloped(count=10,width=2,run=.4,rise=.2,thickness=.2):
    b=Mesh()
    for i in range(count):
        x=i*run;h=i*rise;top=h+rise
        for y in [-width/2,width/2]:
            a=(x,y,h-thickness);c=(x+run,y,h+rise-thickness);d=(x+run,y,top);e=(x,y,top);f=(x,y,h)
            if abs(rise-thickness)<1e-8:
                b.face([a,c,d,f]) if (Vector(c)-Vector(d)).length>1e-8 else None
            else:b.face([a,c,d,f])
            b.face([f,d,e])
        b.face([(x,-width/2,h-thickness),(x+run,-width/2,h+rise-thickness),(x+run,width/2,h+rise-thickness),(x,width/2,h-thickness)])
        b.face([(x,-width/2,top),(x+run,-width/2,top),(x+run,width/2,top),(x,width/2,top)],mat='MAT_Floor')
        b.face([(x,-width/2,h),(x,-width/2,top),(x,width/2,top),(x,width/2,h)])
    b.face([(0,-width/2,-thickness),(0,width/2,-thickness),(0,width/2,0),(0,-width/2,0)])
    x=count*run;h=count*rise
    b.face([(x,-width/2,h-thickness),(x,width/2,h-thickness),(x,width/2,h),(x,-width/2,h)])
    return b.object('part')

def rectangle_frame(width,height,bar=.1,depth=.1,mat='MAT_Trim',bottom=True):
    if bottom:
        inner=[(-width/2+bar,bar),(-width/2+bar,height-bar),(width/2-bar,height-bar),(width/2-bar,bar)]
        outer=[(-width/2,0),(-width/2,height),(width/2,height),(width/2,0)]
        return ring_frame(inner,outer,depth,mat,True)
    inner=[(-width/2+bar,0),(-width/2+bar,height-bar),(width/2-bar,height-bar),(width/2-bar,0)]
    outer=[(-width/2,0),(-width/2,height),(width/2,height),(width/2,0)]
    return ring_frame(inner,outer,depth,mat)

def rail(length=4,height=1,slope=0):
    # Quad cell boundary of a 2D rail profile, sheared onto the stair slope.
    # Only external faces are emitted; no buried rail/post intersections.
    xs=[0,.07]
    for i in range(1,round(length)):xs.extend([i-.03,i+.03])
    xs.extend([length-.07,length]);zs=[0,.15,.21,height-.06,height]
    occupied={(i,j) for i in range(len(xs)-1) for j in range(4) if i%2==0 or j in [1,3]}
    b=Mesh()
    def q(x,y,z):return (x,y,z+slope*x/length)
    for i,j in occupied:
        x0,x1=xs[i:i+2];z0,z1=zs[j:j+2]
        for y in [-.04,.04]:b.face([q(x0,y,z0),q(x1,y,z0),q(x1,y,z1),q(x0,y,z1)],mat='MAT_Metal')
        if (i-1,j) not in occupied:b.face([q(x0,-.04,z0),q(x0,.04,z0),q(x0,.04,z1),q(x0,-.04,z1)],mat='MAT_Metal')
        if (i+1,j) not in occupied:b.face([q(x1,-.04,z0),q(x1,.04,z0),q(x1,.04,z1),q(x1,-.04,z1)],mat='MAT_Metal')
        if (i,j-1) not in occupied:b.face([q(x0,-.04,z0),q(x1,-.04,z0),q(x1,.04,z0),q(x0,.04,z0)],mat='MAT_Metal')
        if (i,j+1) not in occupied:b.face([q(x0,-.04,z1),q(x1,-.04,z1),q(x1,.04,z1),q(x0,.04,z1)],mat='MAT_Metal')
    return b.object('part')

def cleanup(obj):
    """Remove unused slots, recalculate normals. Preserve quads and UV seams."""
    bm=bmesh.new();bm.from_mesh(obj.data)
    for v in bm.verts:v.co=tuple(round(float(x),7) for x in v.co)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4],ngon_method='EAR_CLIP')
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    used=sorted(set(p.material_index for p in obj.data.polygons))
    mats=[obj.data.materials[i] for i in used];indices=[used.index(p.material_index) for p in obj.data.polygons]
    obj.data.materials.clear()
    for m in mats:obj.data.materials.append(m)
    for p,i in zip(obj.data.polygons,indices):p.material_index=i
    obj.data.update()
    # Exact Boolean interpolation can collapse UVs on new cut faces. Diagnose each
    # affected polygon and give that planar face a metre-based orthonormal projection.
    # Original cylindrical strips that meet density are retained. Count repairs in metadata.
    obj.data.calc_loop_triangles();uv=obj.data.uv_layers.active;bad=set()
    for tri in obj.data.loop_triangles:
        p=[obj.data.vertices[i].co for i in tri.vertices];a=p[1]-p[0];b=p[2]-p[0]
        if a.cross(b).length<1e-9:continue
        t=a.normalized();v=a.cross(b).normalized().cross(t)
        matrix=np.array([[a.length,b.dot(t)],[0,b.dot(v)]])
        if abs(np.linalg.det(matrix))<1e-10:continue
        u=[uv.data[i].uv for i in tri.loops];tex=np.array([[u[1].x-u[0].x,u[2].x-u[0].x],[u[1].y-u[0].y,u[2].y-u[0].y]])
        scales=np.linalg.svd(tex@np.linalg.inv(matrix),compute_uv=False)
        if min(scales)<.43 or max(scales)>.57:bad.add(tri.polygon_index)
    for i in bad:
        f=obj.data.polygons[i];coords=metric_uv([obj.data.vertices[j].co for j in f.vertices])
        for loop,coord in zip(f.loop_indices,coords):uv.data[loop].uv=coord
    obj['boolean_uv_reprojected_faces']=len(bad)
    return obj
