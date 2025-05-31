#!/usr/bin/env python3
import logging
import os
import sys
from typing import Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format=" - %(message)s")
logger = logging.getLogger()

def main():
    logger.info("KBS Menuconfig v0.0.0 starting up...")
    # We import this during startup, so that we don't have a delay in the user critical path
    import menuconfig
    import termios
    import tty
    import tarfile
    import shutil
    while True:
        proc_loop()

def proc_loop():
    import shutil
    logger.info("Menuconfig engine ready")
    # TODO: Indicate to the JS-side code that we are ready for input
    wait_for_char(chr(0x07))
    kconfig_tree = Path('klipper_kconfig')
    config_path = Path('klipper.config')
    src_config_path = Path('/media/inbox/klipper.config')
    if src_config_path.exists():
        shutil.copy(src_config_path, config_path)
    else:
        config_path.write_text("# Empty example config file")
    logger.info("Extracting Kconfig bundle...")
    kconfig_tree.mkdir()
    extract_kconfigs(f"/media/inbox/kconfig.tar", kconfig_tree)
    launch_menuconfig(str(kconfig_tree.resolve()), 'src/Kconfig')
    logger.info("Sending config to browser...")
    send_file(config_path)
    logger.info("Cleaning up...")
    shutil.rmtree(kconfig_tree)
    config_path.unlink()
    src_config_path.unlink(missing_ok=True)
    # We don't clean the source tar, because it is always there, and will get overwritten
    logger.info("Complete")

FSCMD_PATH = Path("/.fscmd")
def send_file(path: Path):
    FSCMD_PATH.write_text(f"export_file {path.resolve()}")

def wait_for_char(char):
    import termios
    import tty
    stdin_fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(stdin_fd)
    tty.setraw(stdin_fd)
    while True:
       if sys.stdin.read(1) == char:
            break
    termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_attr)

def extract_kconfigs(archive, path):
    import tarfile
    kconfig_tar = tarfile.TarFile(archive)
    kconfig_tar.extractall(path, filter="data")

def launch_menuconfig(srctree: Optional[str], kconfig_path: str):
    import menuconfig
    # menuconfig reads this from the environment, so we override it here
    os.environ["srctree"] = srctree
    os.environ['KCONFIG_CONFIG'] = "klipper.config"
    sys.argv = [ 'menuconfig', kconfig_path ]
    menuconfig._main()

main()
