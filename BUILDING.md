# Building KBS

## kbs_menuconfig
A python fat zipapp that drives the in-VM UX.

Not noramlly manually invoked. Building the rootfs will call this make

(in kbs_menuconfig)
```
make
```

## Filesystem

### Buildroot

Make sure submodules have been init'd/update'd.

(in menuconfig_vm/rootfs/simple)

(Known to work in an bookworm container with  `patch gcc g++ file dc wget make perl cpio unzip rsync bc bzip2 git python3`)

```
make
```

To sync to web dir

```
make web
```

### Gitref

(in builder/gitref)

```
./make-gitref
```

## Static web

### Generate gitref
(in web)
```
./make-gitref
```

### Generate revdb from gitref (takes a bit)
(in revdb)
```
./bin/from-gitref ../builder/gitref/gitref.git
./bin/to-web
```

### Download xtermjs
(in web)
```
make
```

At this point, the `public` dir can be deployed with `npx wranger pages deploy public`
Not that wranger puts it's state in the working dir (grumble)
