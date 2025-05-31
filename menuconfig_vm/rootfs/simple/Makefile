
all: buildroot/output/images/rootfs.tar

buildroot/output/images/rootfs.tar: br-all

br-%: patches/busybox/embed.patch
	make -C buildroot $*

busybox-config: br-busybox-menuconfig\ busybox-update-config

patches/busybox/embed.patch: $(wildcard busybox_embed/embed/*)
	[[ -d empty_dir ]] || mkdir empty_dir
	diff -urN empty_dir busybox_embed > $@ || true

.PHONY: all br-% busybox-config
