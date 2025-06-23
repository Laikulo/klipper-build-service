#!/usr/bin/env python3
import logging
import os
import sys
from typing import Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format=" - %(message)s")
logger = logging.getLogger()

KBS_VER = "0.0.0"

BANNER = rf"""
o  o o--o   o-o
| /  |   | |
OO   O--o   o-o
| \  |   |     |  v{KBS_VER}
o  o o--o  o--o
"""

GO_PROMPT = """
 ~*~ READY ~*~

Please select a version to configure from above,
  then optionally select a config to start with.

When you are ready, press [Go!]
"""


def main():
    logger.info(f"KBS Menuconfig v{KBS_VER} starting up...")
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

    # Clear the terminal, since this only lives in a web VM, we can assume xterm compatability
    logger.info("Menuconfig engine ready")
    send_immediate("\x1bc")
    print(BANNER)
    print(GO_PROMPT)
    # Inform the JS side that we are ready
    send_immediate(chr(0x02))
    # Wait for the JS side to "say go"
    wait_for_char(chr(0x07))
    # Acknowledge that request
    send_immediate(chr(0x06))
    send_immediate("\x1bc")
    print(BANNER)
    kconfig_tree = Path("klipper_kconfig")
    config_path = Path("klipper.config")
    kconfig_archive = Path("/media/inbox/kconfig.tar")
    src_config_path = Path("/media/inbox/klipper.config")
    if src_config_path.exists():
        shutil.copy(src_config_path, config_path)
    else:
        config_path.write_text("# Empty example config file")
    logger.info("Extracting Kconfig bundle...")
    kconfig_tree.mkdir()
    extract_kconfigs(kconfig_archive, kconfig_tree)
    launch_menuconfig(str(kconfig_tree.resolve()), "src/Kconfig")
    logger.info("Sending config to browser...")
    send_file(config_path)
    logger.info("Cleaning up...")
    shutil.rmtree(kconfig_tree)
    config_path.unlink()
    src_config_path.unlink(missing_ok=True)
    kconfig_archive.unlink()
    logger.info("Complete")
    # Indicate completion of cycle
    send_immediate(chr(0x03))


FSCMD_PATH = Path("/.fscmd")


def send_file(path: Path):
    FSCMD_PATH.write_text(f"export_file {path.resolve()}")


def send_immediate(in_data):
    sys.stdout.write(in_data)
    sys.stdout.flush()


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
    # Kalico gathers "firmware extras" into makefiles and Kconfig.
    # The following is to keep that from being breaking us
    if is_kalico(path):
        logger.info("Kalico detected, creating empty firmware-extras config")
        extras_path = path / "src" / "extras" / "Kconfig"
        extras_path.parent.mkdir(parents=True, exist_ok=True)
        extras_path.touch(exist_ok=True)


def is_kalico(path):
    # We detect kalico by checking for the extras source line in the root Kconfig
    # Because the directory won't be in the kconfig bundle.
    with (path / "src" / "Kconfig").open("r") as root_kconfig:
        for line in root_kconfig:
            if line == 'source "src/extras/Kconfig"\n':
                return True
        return False


def launch_menuconfig(srctree: Optional[str], kconfig_path: str):
    import menuconfig

    # menuconfig reads this from the environment, so we override it here
    os.environ["srctree"] = srctree
    os.environ["KCONFIG_CONFIG"] = "klipper.config"
    sys.argv = ["menuconfig", kconfig_path]
    menuconfig._main()


main()
