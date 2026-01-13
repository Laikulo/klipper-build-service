# KBS GitRef
A compressed archive of git history for klipper and common forks.

This is published as an OCI artifact, and can be used as an image volume in kubernetes, or with other container tooling.

This image is always one layer.

The image is the root of a bare git repo, where refs have been prefixed by the name of the project they come from.

The repo has both refs and objs packed.
