#!/usr/bin/env python3

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger()

def main():
    logger.info("KBS Menuconfig v0.0.0")
    logger.info("Starting Up...")
    # We delay imports here, so that the startup message prints earlier.
    import pyinotify
    if '/bin/menuconfig_kcl' not in sys.path:
        sys.path.append('/bin/menuconfig_kcl')
    import menuconfig
    logger.info("Waiting on kconfig bundle...")
    foo = input()
    launch_menuconfig(foo, 'src/Kconfig')

def launch_menuconfig(srctree: Optional[str], kconfig_path: str):
    # menuconfig reads this from the environment, so we override it here
    os.environ["srctree"] = srctree
    os.environ['KCONFIG_CONFIG'] = "klipper.config"
    menuconfig.menuconfig(kconfig_path)

main()