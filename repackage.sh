#!/bin/bash
# Repackage a crate at the exact version that it was packaged at.
#
# Usage: ./repackage.sh <CRATE> [<SEMVER>]

. ./vars.sh.frag

if ! shouldbuild "$BUILDDIR/debian/changelog" "$PKGDIR/debian/changelog" && \
   ! shouldbuild "$BUILDDIR/debian/changelog" "$DEBCARGO"; then
	exit 0
fi

REALVER="$(get_existing_version "$PKGDIR")"
run_debcargo --no-overlay-write-back --changelog-ready
check_or_add_tarball_hash
