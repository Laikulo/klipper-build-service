all: kconfiglib/menuconfig_kcl menuconfig_vm/rootfs/simple/buildroot/output/images/rootfs.tar

kconfiglib/menuconfig_kcl:
	make -C kconfiglib menuconfig_kcl

menuconfig_vm/rootfs/simple/buildroot/output/images/rootfs.tar:
	make -C menuconfig_vm/rootfs/simple all

.PHONEY: all
