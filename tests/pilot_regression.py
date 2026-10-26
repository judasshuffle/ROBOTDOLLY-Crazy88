"""Run with original pilot .blend loaded. Execute original validators into an isolated report folder."""
import bpy,importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PILOT=ROOT/'approved_pilot';out=ROOT/'reports/pilot_regression'
(out/'reports').mkdir(parents=True,exist_ok=True);(out/'meshes').mkdir(exist_ok=True)
manifest=json.loads((PILOT/'manifest.json').read_text())
for a in manifest['assets']:shutil.copy2(ROOT/a['filename'],out/a['filename'])
spec=importlib.util.spec_from_file_location('approved_pilot_validator',PILOT/'blender/validate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.validate_assets(out,[bpy.data.objects[a['asset_id']] for a in manifest['assets']],manifest,bpy.data.scenes['02_Assembly_Review'],json.loads((PILOT/'tests/assembly_joins.json').read_text()))
print('ORIGINAL_PILOT_REGRESSION_PASS')
