#!/usr/bin/env python3

import csv
import os
import subprocess
import sys
from pathlib import Path
from pprint import pprint as p

project = sys.argv[1]

kconf_to_commit = {}

OUTPUT_PATH = Path('./bundles') / project

GIT_WORK_TREE = Path(f'./scratch/{project}')
GIT_ENV = {
    'GIT_WORK_TREE': GIT_WORK_TREE.resolve(),
    'GIT_DIR': (GIT_WORK_TREE / '.git').resolve()
}

with Path(f'./revisions-{project}.csv').open('r') as csv_file:
    rdr = csv.reader(csv_file)
    for entry in rdr:
        if entry[2] not in kconf_to_commit:
            kconf_to_commit[entry[2]] = entry[0]

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

for kconfig_hash, commit_hash in kconf_to_commit.items():
    target_path = OUTPUT_PATH / f"kconfig-{kconfig_hash}.tar"
    if target_path.exists():
        continue
    print(f"Making {kconfig_hash} from {commit_hash}")
    subprocess.run(['git', 'reset', '--hard', commit_hash], env={**os.environ, **GIT_ENV}, check=True)
    # tar -c --sort=name --owner=root:0 --group=root:0 --mtime="UTC 1970-01-01" -H ustar **/Kconfig | sha256sum | cut -f1 -d' '
    kconfigs = GIT_WORK_TREE.rglob('**/Kconfig')
    tar_args = ['tar', '-c', '-f', str(target_path.absolute()), '-C', str(GIT_WORK_TREE.absolute()),
                '--sort=name', '--owner=root:0', '--group=root:0', '--mtime=UTC 1970-01-01', '-H', 'ustar']
    tar_args += sorted((str(p.relative_to(GIT_WORK_TREE)) for p in kconfigs))
    subprocess.run(tar_args, check=True)
