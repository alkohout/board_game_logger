"""Run every test script in this directory and summarise."""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PYTHON = HERE.parent / '.venv' / 'bin' / 'python'
if not PYTHON.exists():
    PYTHON = pathlib.Path(sys.executable)

total_ok = total_fail = 0
broken = []
for script in sorted(HERE.glob('*_test.py')):
    out = subprocess.run([str(PYTHON), str(script)], capture_output=True, text=True)
    tail = (out.stdout.strip().splitlines() or ['(no output)'])[-1]
    print(f'  {script.stem:<26} {tail}')
    if 'passed' in tail:
        passed, failed = (int(w) for w in tail.replace(',', '').split()
                          if w.isdigit())
        total_ok += passed
        total_fail += failed
        if failed:
            broken.append(script.stem)
    else:
        broken.append(script.stem)
        print('   ', (out.stderr.strip().splitlines() or ['(no error text)'])[-1])

print(f'\n  {total_ok} passed, {total_fail} failed'
      + (f' — see {", ".join(broken)}' if broken else ''))
sys.exit(1 if broken else 0)
