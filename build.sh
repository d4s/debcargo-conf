#!/bin/bash
# Build a packaged crate.
#
# This script is not run directly, but linked into ./build/ when running one of
# the other scripts, so you should do that instead of running this directly.
#
# Usage: [REALVER=<EXACTVER>] ./build.sh <CRATE> [<SEMVER>] [<EXTRA DEPENDENCY DEB> ...]
#
# Envvars:
# IGNORE_MISSING_BUILD_DEPS=1
#     Don't abort on missing build deps. You'll need
#     this when giving extra dependency debs.
# SKIP_SIGN=1
#     Skip signing built packages.
# DISTRIBUTION=$suite
#     Release to something other than unstable, e.g. experimental
# CHROOT=$chroot
#     Build using another schroot than debcargo-unstable-amd64-sbuild
# SBUILD_OPTS=
#     will pass to sbuild; for example SBUILD_OPTS=--arch=i386
# EXTRA_DEBS
#     Include extra dependency debs, e.g. EXTRA_DEBS=librust*.deb.
# USE_PDEBUILD=1
#     Use pdebuild instead of sbuild
set -e

SCRIPTDIR="$(dirname $(readlink -f "$0"))"

abort() { local x=$1; shift; for i in "$@"; do echo >&2 "$0: abort: $i"; done; exit "$x"; }
report() { for i in "$@"; do echo >&2 "debcargo-conf builder: $i"; done; }

if [ "$(basename "$PWD")" != "build" ]; then
	abort 1 "This script is only meant to be run from the build/ directory."
fi

if [ -n "$DEBCARGO" ]; then
	true
elif type -p debcargo >/dev/null 2>&1; then
	DEBCARGO=$(type -p debcargo)
elif [ -f "$HOME/.cargo/bin/debcargo" ]; then
	DEBCARGO="$HOME/.cargo/bin/debcargo"
else
	abort 1 "debcargo not found, run \`cargo install debcargo\` or set DEBCARGO to point to it"
fi

CRATE="$1"
VER="$2"
if test -z "$VER" -o -f "$VER"; then
	VER=""
	shift
else
	shift 2
fi
DISTRIBUTION="${DISTRIBUTION:-unstable}"

PKGNAME=$($DEBCARGO deb-src-name "$CRATE" $VER || abort 1 "couldn't find crate $CRATE")
DEBVER=$(dpkg-parsechangelog -l $PKGNAME/debian/changelog -SVersion)
UPSVER="${DEBVER%-*}"
DEBSRC=$(dpkg-parsechangelog -l $PKGNAME/debian/changelog -SSource)
DEBDIST=$(dpkg-parsechangelog -l $PKGNAME/debian/changelog -SDistribution)
DEB_HOST_ARCH=$(dpkg-architecture -q DEB_HOST_ARCH)
SRCNAME="${DEBSRC}_${DEBVER}"
BUILDNAME="${DEBSRC}_${DEBVER}_${DEB_HOST_ARCH}"
if [ "$USE_PDEBUILD" != 1 ] ; then
	if [ -z "$CHROOT" ]; then
		if schroot -i -c "debcargo-unstable-${DEB_HOST_ARCH}-sbuild" >/dev/null 2>&1; then
			CHROOT="debcargo-unstable-${DEB_HOST_ARCH}-sbuild"
		elif schroot -i -c "unstable-${DEB_HOST_ARCH}-sbuild" >/dev/null 2>&1; then
			CHROOT="unstable-${DEB_HOST_ARCH}-sbuild"
			echo >&2 "Automatically using sbuild chroot unstable-${DEB_HOST_ARCH}-sbuild; however it's"
			echo >&2 "strongly recommended to create a separate chroot debcargo-unstable-${DEB_HOST_ARCH}-sbuild"
			echo >&2 "so your builds won't have to re-download & re-install cargo, rustc, and llvm every time."
			echo >&2 "See README.rst section \"Build environment\" for details."
			sleep 1
		elif [ "$SOURCEONLY" != 1 ]; then
			abort 1 "could not automatically find a suitable chroot; set CHROOT"
		fi
	fi
fi

shouldbuild() {
	local dst="$1"
	local src="$2"
	test ! -e "$dst" -o "$src" -nt "$dst"
}

# maintain an apt cache in ./build/aptroot
mkdir -p "./aptroot/etc/apt/apt.conf.d" "./aptroot/var/lib/apt/lists/" "./aptroot/etc/apt/preferences.d"
cat << END > "./aptroot/apt.conf"
Apt::Architecture "$DEB_HOST_ARCH";
Apt::Architectures "$DEB_HOST_ARCH";
Dir "$PWD/aptroot";
Acquire::Languages "none";
Dir::Etc::Trusted "$(eval "$(apt-config shell v Dir::Etc::Trusted/f)"; printf "$v")";
Dir::Etc::TrustedParts "$(eval "$(apt-config shell v Dir::Etc::TrustedParts/d)"; printf "$v")";
END
{
echo "deb http://deb.debian.org/debian/ $DISTRIBUTION main";
case $DISTRIBUTION in
	experimental|rc-buggy)
		echo "deb http://deb.debian.org/debian/ unstable main"
		;;
	unstable|sid|testing) : ;;
	*-backports)
		echo "deb http://deb.debian.org/debian/ ${DISTRIBUTION%-backports} main";
		echo "deb http://deb.debian.org/debian/ ${DISTRIBUTION%-backports}-updates main";
		echo "deb http://security.debian.org/debian-security/ ${DISTRIBUTION%-backports}-security main";
		;;
	*)
		# assume stable release
		echo "deb http://deb.debian.org/debian/ $DISTRIBUTION-updates main";
		echo "deb http://security.debian.org/debian-security/ $DISTRIBUTION-security main";
		;;
esac;
} > "./aptroot/etc/apt/sources.list"
APT_CONFIG="$PWD/aptroot/apt.conf"
export APT_CONFIG
apt-get update

if shouldbuild "$SRCNAME.dsc" "$PKGNAME/debian/changelog" ]; then
	if [ "$REUSE_EXISTING_ORIG_TARBALL" = 1 ]; then
		mv "${DEBSRC}_${UPSVER}.orig.tar.gz" "${DEBSRC}_${UPSVER}.orig.tar.gz.new"
		apt-get -t unstable source --download-only "${DEBSRC}" # "=${DEBVER}"
		# check that old tarball contains same contents as new tarball
		if ! diff -ru \
			  --label "${DEBSRC}_${UPSVER}.orig.tar.gz.new" \
			  <(zcat  "${DEBSRC}_${UPSVER}.orig.tar.gz.new" | tar -tvvf-) \
			  --label "${DEBSRC}_${UPSVER}.orig.tar.gz" \
			  <(zcat  "${DEBSRC}_${UPSVER}.orig.tar.gz" | tar -tvvf-); then
			read -p "contents differ, continue with old tarball or abort? [y/N] " x
			if [ "$x" != "y" ]; then exit 1; fi
		fi
		# extract old tarball into new directory, to avoid "modified files" problems with dpkg-source later
		( cd "$PKGNAME" && dpkg-source --after-build . && tar --strip-components=1 -xf "../${DEBSRC}_${UPSVER}.orig.tar.gz" )
	fi
	( cd "$PKGNAME" && dpkg-buildpackage -d -S --no-sign )
	# sign if not UNRELEASED
	if echo "$DEBDIST" | grep -qv UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO; then
		if [ "$SKIP_SIGN" != 1 ]; then
			debsign ${DEBSIGN_KEYID:+-k $DEBSIGN_KEYID} "${SRCNAME}_source.changes"
		fi
	fi
fi

# allow tab, comma, space as separators
IFS='	, ' read -r -a EXTRA_DEBS <<< "$EXTRA_DEBS"
if [ ${#EXTRA_DEBS[@]} -eq 0 ]; then
	EXTRA_DEBS=( "$@" )
fi
if [ ${#EXTRA_DEBS[@]} -ne 0 ]; then
	IGNORE_MISSING_BUILD_DEPS=1
	echo >&2 "Given non-empty extra debs; defaulting IGNORE_MISSING_BUILD_DEPS=1"
fi

check_build_deps() {
	if [ "USE_PDEBUILD" != 1 ] ; then
		true
		return
	fi
	mkdir -p dpkg-dummy
	# Dir::State::Lists is /var/lib/apt/lists by default.
	# Since apt replaces the files in that directory instead of rewriting
	# existing inodes, we can rely on the directory mtime.
	if shouldbuild dpkg-dummy/status "$(eval "$(apt-config shell v Dir::State::Lists/d)"; printf "$v")"; then
		# pretend dpkg status file that marks all packages as installed
		# this is because dpkg-checkbuilddeps only works on installed pkgs
		( apt-cache dumpavail -o APT::Default-Release=$DISTRIBUTION && \
			for i in ${EXTRA_DEBS[*]}; do apt-cache show $(echo $i | cut -d_ -f1); done ) | \
		sed -e 's/Package: .*/\0\nStatus: install ok installed/g' > dpkg-dummy/status.tmp
		if ! test -s dpkg-dummy/status.tmp; then
			abort 1 "couldn't generate dpkg-dummy/status, is Debian unstable in your APT sources?"
		fi
		mv dpkg-dummy/status{.tmp,}
	fi
	( cd "$PKGNAME" && dpkg-checkbuilddeps --admindir=../dpkg-dummy )
}

if ! check_build_deps; then
	if [ "$IGNORE_MISSING_BUILD_DEPS" != 1 ]; then
		abort 1 "Missing build-dependencies, but maybe try '{apt,cargo} update'"
	fi
fi

if [ "$SOURCEONLY" = 1 ]; then
	exit
fi

if [ -n "${EXTRA_DEBS[*]}" ]; then
    EXTRA_DEBS_SBUILD=("${EXTRA_DEBS[@]/#/--extra-package=}")
    EXTRA_DEBS_REPO_TMP=$(mktemp -d "${SRCNAME}_REPO_XXXXXXXX")
    # trap cleans up even if user does Ctrl-C
    # https://stackoverflow.com/a/14812383 inside "trap" avoids running handler twice
    trap 'excode=$?; rm -rf "'"$EXTRA_DEBS_REPO_TMP"'"; trap - EXIT' EXIT HUP INT QUIT PIPE TERM
    # symlinks don't work here
    ln -f "${EXTRA_DEBS[@]}" "$EXTRA_DEBS_REPO_TMP/"
    ( cd "$EXTRA_DEBS_REPO_TMP"; apt-ftparchive packages . > Packages )
    EXTRA_DEBS_AUTOPKGTEST_OPTS=([0]=--autopkgtest-opt=--copy="$PWD/$EXTRA_DEBS_REPO_TMP/:/tmp/$EXTRA_DEBS_REPO_TMP/" [1]=--autopkgtest-opt=--add-apt-source="deb [trusted=yes] file:///tmp/$EXTRA_DEBS_REPO_TMP ./")
fi

AUTOPKGTEST_OPTS=("--run-autopkgtest" "--autopkgtest-root-arg=" "--autopkgtest-opts=-- schroot ${CHROOT}")
if [ "$SKIP_AUTOPKGTEST" = 1 ]; then
	AUTOPKGTEST_OPTS=()
	EXTRA_DEBS_AUTOPKGTEST_OPTS=()
fi

LINTIAN_OPTS=()
if echo "$DEBDIST" | grep -q UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO; then
	LINTIAN_OPTS=([0]="--lintian-opt=--suppress-tags" [1]="--lintian-opt=bad-distribution-in-changes-file")
fi

if [ "$USE_PDEBUILD" != 1 ] ; then
	SBUILD_CONFIG="$SCRIPTDIR/dev/sbuildrc" sbuild --no-source --arch-any --arch-all \
		     ${CHROOT:+-c $CHROOT} \
		     ${DISTRIBUTION:+-d $DISTRIBUTION} \
		     "${EXTRA_DEBS_SBUILD[@]}" \
		     "${EXTRA_DEBS_AUTOPKGTEST_OPTS[@]}" \
		     "${AUTOPKGTEST_OPTS[@]}" \
		     "${LINTIAN_OPTS[@]}" \
		     ${SBUILD_OPTS} \
		     "$SRCNAME.dsc"
else
	fulldsc=$(realpath "$SRCNAME.dsc")
	builddir=$(pwd)
	d=$(mktemp -d)
	pushd "$d"
	dpkg-source -x "$fulldsc"
	ls
	cd "${DEBSRC}-${UPSVER}"
	pdebuild --buildresult "$builddir"
	cd ..
	cp *.build "$builddir"
	ls
	popd
	rm -r "$d"
fi
if [ "$SKIP_AUTOPKGTEST" != 1 ]; then
	report "analyzing autopkgtest log: $BUILDNAME.test.log"
	# this is a bit of a hack but works OK for now, until sbuild supports %SBUILD_BUILD_DIR in --autopkgtest-opt
	sed -ne '/autopkgtest .*: testing package .* version .*/,$p' "$BUILDNAME.build" > "$BUILDNAME.test.log"
	"$SCRIPTDIR/dev/rust-regressions.sh" "$BUILDNAME.test.log"
fi

if [ "$USE_PDEBUILD" != 1 ] ; then
	changestool "$BUILDNAME.changes" adddsc "$SRCNAME.dsc"
fi
report "build complete: $BUILDNAME.changes"

if grep -q "unknown-section FIXME" "$BUILDNAME.build"; then
    abort 1 "Please fix the SECTION, found FIXME"
fi

# sign if not UNRELEASED
if echo "$DEBDIST" | grep -qv UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO; then
	if [ "$SKIP_SIGN" != 1 ]; then
		debsign ${DEBSIGN_KEYID:+-k $DEBSIGN_KEYID} --no-re-sign "$BUILDNAME.changes"
	fi
fi
