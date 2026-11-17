"""Export 16 actual pilot scenes, preserve hashes, and create a portable archive."""
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path
from common import ROOT, read, write, timestamp
from engine import Engine
from run_pilot import verify_freeze


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert read(ROOT/'development/summary.json')['completed']==8
    assert read(ROOT/'audit/results.json')['passed'];verify_freeze()
    engine=Engine();context=engine.context();assert context==read(ROOT/'development/started.json')['original_context']
    project=Path(read(ROOT/'config.json')['project']);cells=read(ROOT/'development/schedule.json')['cells']
    assets=[f"Assets/P2SCV1/Scenes/check_v3d_{c['run_id']}_{phase}.unity" for c in cells for phase in ['initial','final']]
    assert len(assets)==len(set(assets))==16
    assets += ['Assets/P2SCV1/P2SCV1Object.cs','Assets/P2SCV1/Editor/P2SCV1Bridge.cs']
    assert all((project/p).is_file() for p in assets)
    package=ROOT/'Unity_Check_V3_Development_Scenes.unitypackage'
    engine.evaluate('UnityEditor.AssetDatabase.ExportPackage(new string[]{'+','.join(json.dumps(p) for p in assets)+'},'+json.dumps(str(package))+',UnityEditor.ExportPackageOptions.IncludeDependencies);return true;')
    with tarfile.open(package,'r:gz') as tar:
        names={tar.extractfile(m).read().decode().strip() for m in tar.getmembers() if m.name.endswith('/pathname')}
    assert set(assets).issubset(names)
    assert engine.context()==context;verify_freeze()
    write(ROOT/'audit/unity_evidence_manifest.json',dict(time=timestamp(),scenes=16,package_sha256=sha(package),
        asset_sha256={str(project/p):sha(project/p) for p in assets},meta_sha256={str(project/(p+'.meta')):sha(project/(p+'.meta')) for p in assets}))
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['results_preservation_manifest.json','unity_execution.lock','cost_ledger.ndjson.lock'])
    write(ROOT/'results_preservation_manifest.json',dict(time=timestamp(),sha256={str(p.relative_to(ROOT)):sha(p) for p in files},scope='All V3 development implementation, preflight, actual API attempts, diagnostics, independent scores and final reports'))
    archive=ROOT.parent/'Unity_Check_V3_Development_20261116.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[ROOT/'results_preservation_manifest.json']:z.write(p,arcname=str(p.relative_to(ROOT.parent)))
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archive.with_suffix('.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    print('Saved',len(files),'files, 16 Unity scenes;',round(archive.stat().st_size/1e6,2),'MB')
    print(archive)


if __name__=='__main__':main()
