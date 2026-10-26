"""Run with ordinary Python after generation. Exercises real single-asset CLI in fresh Blender processes."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--blender',default='C:/Program Files/Blender Foundation/Blender 4.5/blender.exe');args=p.parse_args()
m=json.loads((ROOT/'manifest.json').read_text());baseline=json.loads((ROOT/'reports/determinism_baseline.json').read_text());by={a['asset_id']:a for a in m['assets']}
deterministic={a['asset_id']:a['geometry_sha256'] for a in m['assets']}=={a['asset_id']:a['geometry_sha256'] for a in baseline['assets']}
def protected():
    paths=[ROOT/'manifest.json',ROOT/'blender/crazy88_master.blend']+list((ROOT/'meshes').glob('*.fbx'))+list((ROOT/'sources').glob('*.blend'))
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=protected();cases=[]
for name in ['STAIR_Straight','FLOOR_Ramp','PIPE_Tee','PIPE_Reducer','STAIR_Spiral','STAIR_Straight_SlopingUnderside']:
    log=ROOT/'reports'/f'independent_{name}.log'
    with log.open('w') as stream:
        result=subprocess.run([args.blender,'--background','--factory-startup','--python-exit-code','1','--python',str(ROOT/'blender/generate.py'),'--','--asset',name,'--no-render'],stdout=stream,stderr=subprocess.STDOUT)
    path=ROOT/'individual'/name/'manifest.json'
    actual=json.loads(path.read_text())['assets'][0] if path.exists() else {}
    cases.append(dict(asset_id=name,exit_code=result.returncode,identical_geometry=actual.get('geometry_sha256')==by[name]['geometry_sha256'],identical_connectors=actual.get('connectors')==by[name]['connectors']))
unchanged=before==protected()
report=dict(deterministic_all_89=deterministic,canonical_files_unchanged_by_single_asset_commands=unchanged,independent_regeneration=cases)
report['passed']=deterministic and unchanged and all(c['exit_code']==0 and c['identical_geometry'] and c['identical_connectors'] for c in cases)
(ROOT/'reports/regeneration.json').write_text(json.dumps(report,indent=2))
assert report['passed'],report
print(json.dumps(report,indent=2))
