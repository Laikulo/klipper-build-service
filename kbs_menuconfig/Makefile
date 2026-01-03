
kbs_menuconfig: kbs_menuconfig.d/__main__.py .deps-installed.stamp
	python3 -m zipapp -p python3 kbs_menuconfig.d --output $@

kbs_menuconfig.d:
	mkdir $@

kbs_menuconfig.d/__main__.py: kbs_menuconfig.d kbs_menuconfig.py
	cp kbs_menuconfig.py kbs_menuconfig.d/__main__.py

.deps-installed.stamp: kbs_menuconfig.d requirements.txt
	python3 -m pip install --target kbs_menuconfig.d -r requirements.txt
	touch $@

clean:
	rm -rf kbs_menuconfig.d
	rm kbs_menuconfig
	rm .*.stamp
