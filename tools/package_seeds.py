"""Build the versioned MIT seed ZIP from the public source allowlist."""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import VERSION
from tools.package import source_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New archive path; existing files are never overwritten')
    args = parser.parse_args()
    library = ROOT / 'seed_library'
    manifest = json.loads((library / 'seed_manifest.json').read_text(encoding='utf-8'))
    assert manifest == json.loads((ROOT / 'docs/seed_manifest.json').read_text(encoding='utf-8'))
    assert manifest['compatible_server_version'] == VERSION
    assert (library / 'LICENSE').read_bytes() == (ROOT / 'LICENSE').read_bytes()
    for entry in manifest['seeds']:
        path = (library / entry['relative_path']).resolve()
        assert path.is_relative_to(library.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], entry['name']
    files = [path for path in source_files() if path.is_relative_to(library)]
    archive = (args.output or ROOT.parent / f'MCP_CREO_MechDog-{VERSION}-seed-library.zip').resolve()
    if archive.exists():
        raise ValueError('Archive already exists; choose a new output path')
    prefix = f'MCP_CREO_MechDog-{VERSION}-seed-library/'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
        for path in files:
            entry = zipfile.ZipInfo(prefix + path.relative_to(library).as_posix(), (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, path.read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(f'Seed archive: {archive}; {len(files)} files; {len(manifest["seeds"])} seeds; SHA256 {digest}')
    print('For a new release, set seeds.py expected_digest to this archive SHA256 before packaging source.')


if __name__ == '__main__':
    main()
