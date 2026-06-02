import py_compile
from pathlib import Path
import sys

root = Path('argus')
files = list(root.rglob('*.py'))
errors = []
for f in files:
    try:
        py_compile.compile(str(f), doraise=True)
    except Exception as e:
        errors.append((f, str(e)))

if errors:
    print('Compilation errors:')
    for p, e in errors:
        print(p, '->', e)
    sys.exit(1)
print('\u2713 All Python files compile')
