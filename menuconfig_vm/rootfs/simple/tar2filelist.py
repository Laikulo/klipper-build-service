#!/usr/bin/env python3
from tinyemu_filelist import VirtualFS
import tarfile
from pathlib import Path
from pprint import pprint as p

# TODO: Make this all argparse-y

in_tar = tarfile.open('buildroot/output/images/rootfs.tar')

vfs = VirtualFS()
vfs.from_tar(in_tar)
vfs.render_to_dir(Path('./tar-out-test-big'))
