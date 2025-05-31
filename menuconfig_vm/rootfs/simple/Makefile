
all: buildroot/output/images/rootfs.tar

buildroot/output/images/rootfs.tar: br-all

br-%: patches/busybox/embed.patch root-overlay/bin/kbs_menuconfig root-overlay/bin/menuconfig_kcl
	make -C buildroot $*

busybox-config: br-busybox-menuconfig\ busybox-update-config

patches/busybox/embed.patch: $(wildcard busybox_embed/embed/*)
	[[ -d empty_dir ]] || mkdir empty_dir
	diff -urN empty_dir busybox_embed > $@ || true

root-overlay/bin/kbs_menuconfig: ../../../kbs_menuconfig/kbs_menuconfig.py
	cp $< $@

root-overlay/bin/menuconfig_kcl: ../../../kconfiglib/menuconfig_kcl
	cp $< $@

.PHONY: all br-% busybox-config
