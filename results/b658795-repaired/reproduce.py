"""Bounded known-answer rerun; not the general DESIGN section 7 comparator.
Run from repository root: python3 results/b658795-repaired/reproduce.py NEW_OUTPUT
Requires inputs fetched with scripts/fetch_kit_at.sh at KIT below.
"""
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

KIT = 'b6587950986eb4ec501e080cc9730fd21dcb69fa'
ROOT = Path(__file__).resolve().parents[2]


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT / 'results/b658795/inputs.sha256.json').read_text())
    for name, digest in manifest.items():
        if hashlib.sha256((ROOT / 'inputs' / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Input digest mismatch: ' + name)
    kit = ROOT / 'inputs' / ('test-kit-' + KIT)
    expected_root = ROOT / 'inputs' / ('expected-' + KIT)
    cases = sorted(p.name for p in (kit / 'cases').iterdir() if p.is_dir())
    pinned_cases = sorted({Path(n).parts[2] for n in manifest if '/cases/' in n})
    if cases != pinned_cases or len(cases) != 6:
        raise ValueError('Case population differs from pinned six cases')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    paths = ['aaif_reader', 'mappings', 'scripts', 'results/b658795-repaired/reproduce.py', 'results/b658795/inputs.sha256.json']
    if subprocess.check_output(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, text=True).strip():
        raise ValueError('Commit execution sources before measuring')
    def run(cmd):
        return subprocess.check_output(cmd, cwd=ROOT, text=True)
    commands = []
    for case in cases:
        rel = 'inputs/test-kit-' + KIT + '/cases/' + case
        cmd = [sys.executable, '-m', 'aaif_reader', '--mapping', 'mappings/test-kit-b658795.json',
               '--basis', rel + '/basis.json', '--out', str(out / case), rel + '/records.otlp.json']
        run(cmd)
        commands.append(['python3', '-m', 'aaif_reader', '--mapping', 'mappings/test-kit-b658795.json',
                         '--basis', rel + '/basis.json', '--out', '<OUTPUT>/' + case, rel + '/records.otlp.json'])
    signatures = json.loads(run([sys.executable, 'scripts/signature_rows.py', KIT]))
    (out / 'signatures.json').write_text(json.dumps(signatures, indent=2) + '\n')
    rows = []
    for case in cases:
        report = json.loads((out / case / 'report.json').read_text())
        q = report['query']
        expected = json.loads((expected_root / case / 'expected.json').read_text())
        actual = {'action': q['context']['action'],
                  'effect': {'established': 'confirmed', 'unknown': 'unconfirmed'}.get(q['status'], q['status']),
                  'confirmed_tickets': q['ticket_ids']}
        sigs = [r['signature_valid'] for r in signatures['rows'] if r['case'] == case and 'signature_valid' in r]
        if sigs:
            if len(sigs) != 1:
                raise ValueError('Expected one signature observation for ' + case)
            actual['receipt_signature_verified'] = sigs[0]
        fields = {k: {'actual': actual.get(k), 'expected': expected.get(k),
                      'match': k in actual and k in expected and actual[k] == expected[k]}
                  for k in sorted(set(actual) | set(expected))}
        rows.append({'case': case, 'processing_complete': report['processing'] == 'complete',
                     'execution_observation': q['execution'], 'fields': fields})
    result = {'kit': KIT, 'reader_and_runner_commit': head, 'python': platform.python_version(),
              'answer_blind': False, 'kind': 'known-answer repair validation', 'rows': rows,
              'limits': ['Action echoes evaluation_context; not independent action inference.',
                         'Signatures are separate checks under a synthetic key; do not authenticate tenant metadata.',
                         'Not the general DESIGN comparator or completion of Task 7.']}
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'inputs.sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    ok = all(r['processing_complete'] and all(f['match'] for f in r['fields'].values()) for r in rows)
    print(json.dumps({'cases': len(rows), 'all_compared_fields_match': ok}))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
