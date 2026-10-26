"""Record immutable approval evidence before Phase 2. Never overwrites an existing lock."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];pilot=root/'approved_pilot'
lock=root/'reports/pilot_lock.json'
paths=['manifest.json','blender/generate.py','blender/validate.py','blender/crazy88.blend']
m=json.loads((pilot/'manifest.json').read_text())
paths += [a['filename'] for a in m['assets']]
data={'files':{p:hashlib.sha256((pilot/p).read_bytes()).hexdigest() for p in paths},'assets':m['assets']}
if lock.exists():assert json.loads(lock.read_text())==data,'Approved pilot was changed'
else:lock.write_text(json.dumps(data,indent=2))
if (root.parent/'manifest.json').exists():
    assert all(hashlib.sha256((root.parent/p).read_bytes()).hexdigest()==sha for p,sha in data['files'].items()),'Original pilot was changed'
print('Approved pilot lock verified')
