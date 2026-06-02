from pathlib import Path
import sys

root = Path('argus')
missing = []
for d in root.rglob('*'):
    if d.is_dir():
        init = d / '__init__.py'
        if not init.exists():
            missing.append(d)
            # create init to make packages importable
            init.write_text('# package\n')

if missing:
    for m in missing:
        print('Created __init__.py in', m)
    sys.exit(0)
print('All directories now contain __init__.py')
