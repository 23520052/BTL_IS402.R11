"""Check the exported PBIX and its report definitions against the source project."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def normalize_definition(value):
    """Ignore Desktop schema stamps and empty, inherited formatting declarations."""
    value.pop('$schema', None)
    for field in ('objects', 'visualContainerObjects'):
        if field in value:
            value[field] = {name: entries for name, entries in value[field].items() if entries != []}
    return value


def main():
    path = ROOT / 'sales_dashboard.pbix'
    errors = []
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            errors.append(f'Corrupt ZIP member: {bad}')
        names = archive.namelist()
        if 'DataModel' not in names or archive.getinfo('DataModel').file_size == 0:
            errors.append('Missing semantic model')
        pages = [n for n in names if n.startswith('Report/definition/pages/') and n.endswith('/page.json')]
        mobile = [n for n in names if n.endswith('/mobile.json')]
        if len(pages) != 4 or len(mobile) != 44:
            errors.append('Expected four pages and 44 mobile definitions')
        for name in names:
            if name.startswith('Report/definition/') and name.endswith(('/visual.json','/mobile.json','/page.json')):
                source = ROOT / 'sales_dashboard.Report' / name.removeprefix('Report/')
                exported = json.loads(archive.read(name))
                expected = json.loads(source.read_text(encoding='utf-8'))
                # Desktop may stamp a newer schema version while preserving all settings.
                exported = normalize_definition(exported)
                expected = normalize_definition(expected)
                if exported != expected:
                    errors.append(f'Export differs from source: {name}')
        refresh = {}
        for name in pages:
            page = json.loads(archive.read(name))
            refresh[page['name']] = page.get('objects', {}).get('pageRefresh', [])
        for page in ('overview', 'monitoring'):
            if 'PT30S' not in json.dumps(refresh.get(page)):
                errors.append(f'{page}: missing APR 30 seconds')
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'bytes': path.stat().st_size, 'pages': len(pages), 'mobile_visuals': len(mobile),
              'report_definitions_match_source': not errors,
              'semantic_model_security_validation': 'See rls_validation.json from the reopened PBIX engine; binary DataModel is not decoded here.',
              'status': 'pass' if not errors else 'failed', 'errors': errors}
    output = ROOT / 'evidence/sprint2/artifact_validation.json'
    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
