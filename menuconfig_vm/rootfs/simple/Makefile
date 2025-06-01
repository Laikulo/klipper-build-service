
all: buildroot/output/images/rootfs.tar

buildroot/output/images/rootfs.tar: br-all

br-%: patches/busybox/embed.patch root-overlay/bin/kbs_menuconfig root-overlay/bin/menuconfig_kcl buildroot/.config
	make -C buildroot $*

buildroot/.config:
	make -C buildroot DEFCONFIG=../buildroot.defconfig defconfig

busybox-config: br-busybox-menuconfig\ busybox-update-config

patches/busybox:
	mkdir $@

patches/busybox/embed.patch: $(wildcard busybox_embed/embed/*) patches/busybox
	[[ -d empty_dir ]] || mkdir empty_dir
	diff -urN empty_dir busybox_embed > $@ || true

root-overlay/bin:
	mkdir root-overlay/bin

root-overlay/bin/kbs_menuconfig: ../../../kbs_menuconfig/kbs_menuconfig.py root-overlay/bin
	cp $< $@

root-overlay/bin/menuconfig_kcl: ../../../kconfiglib/menuconfig_kcl root-overlay/bin
	cp $< $@

.PHONY: all br-% busybox-config
