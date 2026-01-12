
all: buildroot/output/images/rootfs.tar httpfs/head

buildroot/output/images/rootfs.tar: br-all

br-%: patches/busybox/embed.patch root-overlay/bin/kbs_menuconfig buildroot/.config
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

root-overlay/bin/kbs_menuconfig: root-overlay/bin
	make -C ../../../kbs_menuconfig
	cp ../../../kbs_menuconfig/kbs_menuconfig $@

web:
	rsync -r --delete httpfs/ ../../../web/public/fs/tartest/

httpfs/head: buildroot/output/images/rootfs.tar
	python3.11 ./tar2filelist.py

.PHONY: all br-% busybox-config
