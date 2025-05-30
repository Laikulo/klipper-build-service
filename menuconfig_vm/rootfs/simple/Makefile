
all: buildroot/output/images/rootfs.tar

buildroot/output/images/rootfs.tar: br-all

br-%:
	make -C buildroot $*

busybox-config: br-busybox-menuconfig\ busybox-update-config


.PHONY: all br-% busybox-config