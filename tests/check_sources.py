"""Run in Blender: each standalone source must contain the identical authoritative mesh."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from generate import fingerprint
manifest=json.loads((ROOT/'manifest.json').read_text());results=[]
for rec in manifest['assets']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT/rec['source']),link=False) as (src,dst):dst.objects=[rec['asset_id']]
    obj=dst.objects[0];passed=obj is not None and fingerprint(obj)==rec['geometry_sha256']
    results.append(dict(asset_id=rec['asset_id'],passed=passed))
(ROOT/'reports/standalone_sources.json').write_text(json.dumps(dict(passed=all(r['passed'] for r in results),assets=results),indent=2))
assert all(r['passed'] for r in results)
print('STANDALONE_SOURCES_PASS',len(results))
