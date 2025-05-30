Use cases:
* User provides a kconfig and target klipper revision (and possible upstream)
  * Build in a gvisor container, and cache based on commit+config
* User provides a version (or takes default), and creates a kconfig
  * Linux wasm with python and libkconfig
    * We do this on the browser to minimize latency when interacting with ncurses.
    * Maybe a minimal tinyemu environment. Gotta figure out how to pass out/back.
      * When root is virtio-9p, then fs_import_file will drop a file into /tmp
      * There's something that the guest can do (tbd) to call fs_export_file
    * Would prefer to native-compile something linux-compat
    * Client JS can handle server interaction
      * Server provides base FS and klipper sourcetree.
  * Options to:
    * Download
    * Send to build service
    * Save in browser
    * Save in ?? (cloud file store, maybe leverage gdrive &co)
