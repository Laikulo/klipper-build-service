# K Build Service/System

!! WARNING: This project is mostly incomplete, and isn't usable right now.
!!          Some individual components are minimum viable, but the total is less than the sum of its parts

## Functional components

### Builder
A service that given a ref-ish and a kconfig, produces compiled binaries

Current Capabilities: Build in a networkless nonprivileged container.

```
mkdir inbox outbox
cp ~/Downloads/klipper.config inbox/Kconfig
podman run --rm -it --net=none --mount=type=image,src=ghcr.io/laikulo/klipper-build-service/kbs_gitref:latest,dst=/media/git -v $PWD/inbox:/media/inbox:ro,z -v $PWD/outbox:/media/outbox:rw,z --userns=keep-id:uid=1000 ghcr.io/laikulo/klipper-build-service/kbs_buildenv:latest klipper v0.13.0
```

Next steps: confirm that bugfixes in gvisor means that they now map properly when running nonprivileged gvisor

### Menuconfig in the browser
Provides a terminal-like experience for making configs.

Next steps: UI rework, probablt get rid of integrated selector, and pass throguh query parames form a dedicated chooser page.

Alternatley, make the chooser a modal hiding the terminal, though probably start the VM early since, its startup time is notable

## Data Bundles

### Gitref

A packed git repo distributed as an OCI image that contains objects from:
* Klipper
* Kalico
* THEOS's modified klipper

Used to quickly build a working tree for a specfic rev. 
The expectation is that a host will build many different configurations, so frontloading download is preferred.
Also allows us to run the build sandbox with no outbound network connectivity

Heads and Tags are prefxied with the name of their project, and `HEADS` are `REMOTE_HEAD`

For example:

|project|     upstream ref|bundled ref                   |
|------:|----------------:|:-----------------------------|
| kalico|refs/heads/main  |refs/heads/kalico/main        |
| kalico|HEAD             |refs/heads/kalico/REMOTE\_HEAD|
|klipper|refs/tags/v11.0.0|refs/tags/klipper/v11.0.0     |

Cadence: As needed during development, weekly after.

### Config Revdb
CSVs and compressed kconfigs used to duedupe kconfig-only operations.

Distributed as both an OCI image, via HTTP.

CSV contains git hash, git describe output, and a content hash of kconfig at that point.
kconfig bundles are named after their content hash, so they dedupe naturally.

Used by menuconfig-in-browser to retrieve a kconfig-only tree, to speed up the critical path.

Cadence: lockstep with gitref, future versions will be generated from the gitref

