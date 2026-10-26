"""Finalize metadata and create/verify a local review ZIP. No network operations."""
import hashlib,json,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=read('manifest.json');v=read('reports/validation.json');s=read('reports/standalone_sources.json');r=read('reports/regeneration.json');f=read('reports/focused_geometry.json');pilot=read('reports/pilot_regression/reports/validation.json');lock=read('reports/pilot_lock.json')
assert len(m['assets'])==89 and v['offline_pass'] and s['passed'] and r['passed'] and f['passed'] and pilot['offline_pass']
assert all(sha(ROOT/'approved_pilot'/p)==value for p,value in lock['files'].items())
if (ROOT.parent/'manifest.json').exists():assert all(sha(ROOT.parent/p)==value for p,value in lock['files'].items())
for a in m['assets']:
    assert sha(ROOT/a['filename'])==a['fbx_sha256']
    assert (ROOT/'previews/uv_checks'/f"{a['asset_id']}.png").is_file()
    a['source_sha256']=sha(ROOT/a['source'])
assert len(list((ROOT/'meshes').glob('*.fbx')))==89 and len(list((ROOT/'sources').glob('*.blend')))==89
evidence=['reports/validation.json','reports/standalone_sources.json','reports/regeneration.json','reports/focused_geometry.json','reports/pilot_regression/reports/validation.json']
m['delivery']=dict(status='offline_validated_ready_for_visual_review_and_isolated_viewer_testing',asset_count=89,base_inventory_count=88,additional_variations=1,master_scene='blender/crazy88_master.blend',contact_sheet='previews/contact_sheet.png',evidence=evidence,darkride_viewer='unverified',collision='not_certified',attachment_grid_metres=.005)
(ROOT/'manifest.json').write_text(json.dumps(m,indent=2))
summary=dict(status=m['delivery']['status'],completed_utc=datetime.now(timezone.utc).isoformat(),assets=89,export_triangles=sum(a['triangles'] for a in m['assets']),source_quads=sum(a['quads'] for a in m['assets']),fbx_roundtrips_passed=len(v['fbx_roundtrip']),standalone_sources_passed=len(s['assets']),deterministic_geometry_all_89=r['deterministic_all_89'],independent_cli_cases=len(r['independent_regeneration']),approved_pilot_unchanged=True,joins_passed=len(v['joins']),pipe_profiles_passed=len(v['pipe_mating_profiles']),spiral_minimum_sampled_clearance_metres=f['minimum_stacked_spiral_clearance_metres'],reducer_uv_seams=f['reducer_uv_shells'],contact_sheets_refreshed=True,visual_review='Seven category sheets and revised underside view inspected; no new regeneration defect identified',all_available_offline_checks_passed=True,manual_review=['Spiral walk line, inner treads and railings','Sloping stair lower datum clearance','Intentional UV seams with final materials','Double arch central separation'],darkride_viewer_compatibility='unverified',deployment='none',evidence_sha256={p:sha(ROOT/p) for p in evidence})
(ROOT/'reports/final_delivery.json').write_text(json.dumps(summary,indent=2))
# Selected deliverable tree; omit temporary independent outputs, backups and large render logs.
folders=['blender','sources','meshes','textures','themes','previews','tests','approved_pilot']
files=[]
for folder in folders:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.blend1','.pyc'])
files.extend(ROOT/p for p in ['README.md','DELIVERY.md','PROGRESS.md','BRIEF.md','manifest.json'])
files.extend(p for p in (ROOT/'reports').glob('*') if p.is_file() and p.suffix in ['.json','.md'] and p.name!='package_contents_sha256.json')
files.append(ROOT/'reports/pilot_regression/reports/validation.json')
files=sorted(set(files));checksums={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files}
(ROOT/'reports/package_contents_sha256.json').write_text(json.dumps(checksums,indent=2))
# The checksum document is included, but does not try to hash itself.
files.append(ROOT/'reports/package_contents_sha256.json')
archive=ROOT.parent/'ROBOTDOLLY-Crazy88-Phase2-Review.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,'Crazy88-Phase2/'+str(p.relative_to(ROOT)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for p,value in checksums.items():assert hashlib.sha256(z.read('Crazy88-Phase2/'+p)).hexdigest()==value
archive.with_suffix('.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,files=len(files),verified=True),indent=2))
