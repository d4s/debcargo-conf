#!/bin/bash
# Package or update a new or existing crate.
#
# Usage: [REALVER=<EXACTVER>] ./release.sh <CRATE> [<SEMVER>]
#
# Envvars:
# See also ./vars.sh.frag for its envvars, which we pass through.

. ./vars.sh.frag

case "$(git rev-parse --abbrev-ref HEAD)" in
pending-*)	abort 1 "You are on a pending-release branch, $0 can only be run on another branch, like master";;
esac

if [ -n "$VER" ]; then
	if [ ! -d "$PWD/src/$PKGBASE" ]; then
		abort 1 "Using crate $CRATE with version $VER but default-version is not packaged." \
		"Package that first by running this script without the explicit version."
	fi
fi
if [ ! -d "$PKGDIR/debian" ]; then
	mkdir -p "$PKGDIR/debian"
	cat <<-eof > "$PKGCFG"
	overlay = "."
	uploaders = ["$DEBFULLNAME <$DEBEMAIL>"]
	eof
	git add "$PKGDIR"
fi
if [ ! -f "$PKGDIR/debian/copyright" ]; then
	cat <<-eof > "$PKGDIR/debian/copyright"
	FIXME fill me in using ./copyright.debcargo.hint as a guide
	eof
fi
if [ -n "$VER" -a "$(sed -ne 's/^semver_suffix\s*=\s*//p' "$PKGCFG")" != "true" ]; then
	if grep -q semver_suffix "$PKGCFG"; then
		sed -i -e 's/^\(semver_suffix\s*=\s*\).*/\1true/' "$PKGCFG"
	else
		sed -i -e '1isemver_suffix = true' "$PKGCFG"
	fi
fi

if ! grep -q uploaders "$PKGCFG"; then
	# try to auto-fill in uploaders if debcargo.toml doesn't have it
	uploader="$(grep -E -A1 "[0-9][0-9]*( Debian)? Rust Maintainers" "$PKGDIR/debian/copyright" | tail -n1 | sed -re 's/^\s*[0-9]+\s*//g')"
	uploader="${uploader:-$DEBFULLNAME <$DEBEMAIL>}"
	sed -i -e 's/^\(overlay.*\)$/\1\nuploaders = ["'"$uploader"'"]/' "$PKGCFG"
	echo >&2 "$0: Auto-added $uploader to uploaders in debcargo.toml, based on d/copyright"
	if [ "$uploader" != "$DEBFULLNAME <$DEBEMAIL>" ]; then
		read >&2 -p "$0: You may also want to add yourself; ctrl-c if you want to do that, or press enter to continue... " x
	fi
fi

run_debcargo
check_or_add_tarball_hash
git add -N "$PKGDIR"

if ! git diff --quiet -- "$PKGDIR_REL"; then
	read -p "Update wrote some changes to $PKGDIR_REL, press enter to git diff..." x || true
	git diff -- "$PKGDIR_REL"
	echo >&2 "-- end of git diff --"
fi

cat >&2 <<eof
Automatic update of $CRATE finished; now it's your turn to manually review it.

Deal with any FIXMEs mentioned above, by editing any corresponding source files
in $PKGDIR_REL. If a hint file is listed, indicated by (•), you should edit the
*NON*-hint file, without the suffix .debcargo.hint, and git-add the hint file
exactly as output by debcargo. So for example:

to deal with a FIXME in:
	    build/$PKGNAME/debian/copyright.debcargo.hint
you should edit (and git-add when ready):
	    src/$PKGNAME/debian/copyright
and directly git-add without editing:
	    src/$PKGNAME/debian/copyright.debcargo.hint

When done, git-add all your changes plus any unmodified hint files, and re-run
this command (\`./update.sh $*\`).

For issues with debian/control, edit src/$PKGNAME/debian/debcargo.toml instead.
You can find docs for that in debcargo.toml.example in the debcargo git repo.

Check that your fixes actually get rid of the FIXMEs. Of course, you can ignore
FIXMEs listed in hint files, assuming you actually fixed the issues in the
corresponding non-hint files. (We have no way to auto-detect this so you have
to be honest!) You should also ignore the FIXME in the Distribution field in
the top entry of debian/changelog, that will be dealt with in the next step.

If there was a \`git diff\` above, check it to see if debcargo made changes to
any auto-generated hint files. If so, you should make the equivalent changes to
the non-hint files, and git-add these too.

You can test-build your package by running:

  cd build && ./build.sh $CRATE $VER

This assumes that you have set up sbuild; see "Build environment" in README.rst
for details. Try to fix any lintian errors, but note that some errors are due
to lintian being out-of-date and/or are expected at this stage of the process
(e.g. bad-distribution-in-changes-file). Ask on IRC when in doubt.

If your update includes raising the semver level i.e. from 0.x.* to 0.y.* or
from x.*.* to y.*.*., then you should also check the reverse-deps of your
package, by running:

  dev/list-rdeps.sh $CRATE

If any of the reverse-dependencies depend on an older version of your crate,
please try to update those too, to depend on the newer version that you just
packaged. If this is impossible or too hard, you should retain the old version
of your crate by running \`./update.sh $CRATE <OLD SEMVER>\`, where <OLD
SEMVER> looks like 0.n or n - but you must have a good reason for this, which
you should document in src/$PKGNAME-<OLD SEMVER>/debian/debcargo.toml.

When satisfied with all of these outputs:

- of debcargo after running ./update.sh
- of lintian after running ./build.sh
- of dev/list-rdeps.sh $CRATE

then you can commit. For example:
git commit -m "$CRATE: new upstream release" src/$PKGNAME/
and push all your changes.

Then, ask a Debian Developer to run \`./release.sh $*\`. This finalises your
changes in the changelog, and allows them to build and upload the package. If
you're not a Debian Developer and are unable to upload, please don't run that
script or else you will need to revert the changes that it makes to your git.
Instead, add an empty RFS file inside the created debian directory. If there
are other issues that need to be addressed such as missing dependencies, they
can be addressed by adding a comment into the RFS file; see CONTRIBUTING.rst's
"Ready for upload" section for more details.
eof
if [ -n "$VER" ]; then
cat >&2 <<eof

You are packaging an older version of a crate. Please document why it's needed,
by adding comments to src/$PKGNAME/debian/debcargo.toml. For example because it
is a dependency of other crate(s), and it is not possible to update them to use
the latest version of $CRATE. Please also mention the names of these crate(s).
eof
fi
