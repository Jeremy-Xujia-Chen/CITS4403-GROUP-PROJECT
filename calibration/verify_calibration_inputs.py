"""Reject reuse of an exported calibration when its inputs or adapters changed."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    path=ROOT/'reliable-calibration/parameters.json'
    if not path.exists():
        print('No exported registry yet; calibration checkpoint guards remain active.')
    else:
        config=json.loads(path.read_text(encoding='utf-8'))
        for relative,expected in config['provenance']['source_sha256'].items():
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected, 'Input or adapter changed: '+relative+'; run -Fresh to avoid stale checkpoints.'
        print('Exported calibration input and adapter hashes verified.')
