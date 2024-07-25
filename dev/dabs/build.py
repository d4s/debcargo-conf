#!/usr/bin/env python3

"""
Dependency aware build system - build.sh
2024 Debian Rust team
2024 Federico Ceratto <federico@debian.org>
Released under AGPL
"""

import os
import logging
from os import getenv
import subprocess
import sys
import tempfile
from pathlib import Path

# TODO: better logging than print
# TODO: check for deps even when a .deb is passed
# TODO: turn into a library + CLI frontend

log = logging.getLogger()


def runc(q: list, *a, **kw) -> str:
    """Run command, check return value for success and return stdout"""
    print("running runc", repr(q), repr(a), repr(kw))
    print(" ".join(q), " ".join(a))
    p = subprocess.run(q, *a, **kw, check=True, capture_output=True, text=True)
    print("-- output --")
    if len(p.stdout) < 200:
        print(p.stdout)
    else:
        print(f"...skipping {len(p.stdout)} lines...")
    print("-- end --")
    return p.stdout


def runrv(q, *a, **kw) -> int:
    """Run command and extract return value"""
    print("running runrv", repr(q), repr(a), repr(kw))
    assert isinstance(a, list) or isinstance(a, tuple), repr(a)
    for x in a:
        assert isinstance(x, str), repr(a)
    print(" ".join(a))
    p = subprocess.run(q, *a, **kw, capture_output=True, text=True)
    print("retcode", p.returncode)
    print("-- output --")
    if len(p.stdout) < 200:
        print(p.stdout)
    else:
        print(f"...skipping {len(p.stdout)} lines...")
    print("-- end --")
    return p.returncode


def abort(*messages) -> None:
    for msg in messages:
        log.error(msg)
    sys.exit(1)


def report(*messages) -> None:
    for msg in messages:
        log.info("debcargo-conf builder: %s", msg)


def should_build(dst, src) -> bool:
    return not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst)


def locate_debcargo() -> str:
    debcargo = getenv("DEBCARGO")
    if not debcargo:
        debcargo = runc(["which", "debcargo"]).strip()

    if not debcargo:
        if Path.home().joinpath(".cargo/bin/debcargo").exists():
            log.debug("debcargo not in path. Using debcargo from .cargo/bin")
            debcargo = str(Path.home().joinpath(".cargo/bin/debcargo"))
        else:
            abort(
                "debcargo not found, run `cargo install debcargo` or set DEBCARGO to point to it",
            )

    return debcargo


def build() -> None:
    script_dir = Path(__file__).resolve().parent

    if Path.cwd().name != "build":
        abort("This script is only meant to be run from the build/ directory.")

    debcargo = locate_debcargo()

    if len(sys.argv) < 2:
        abort(
            "Usage: [REALVER=<EXACTVER>] ./build.sh <CRATE> [<SEMVER>] [<EXTRA DEPENDENCY DEB> ...]",
        )

    # TODO: argparse
    crate = sys.argv[1]
    ver = sys.argv[2] if len(sys.argv) > 2 and not os.path.isfile(sys.argv[2]) else None
    if ver:
        extra_debs = sys.argv[3:]
    else:
        extra_debs = sys.argv[2:]

    distribution = getenv("DISTRIBUTION", "unstable")

    if ver is None:
        pkgname = runc([debcargo, "deb-src-name", crate]).strip()
    else:
        pkgname = runc([debcargo, "deb-src-name", crate, ver]).strip()
    del ver
    if not pkgname:
        abort(f"couldn't find crate {crate}")

    # TODO: replace with Python lib
    log.debug("Name: %s", pkgname)
    debver = runc(
        ["dpkg-parsechangelog", "-l", f"{pkgname}/debian/changelog", "-SVersion"]
    ).strip()

    debsrc = runc(
        ["dpkg-parsechangelog", "-l", f"{pkgname}/debian/changelog", "-SSource"]
    ).strip()

    debdist = runc(
        ["dpkg-parsechangelog", "-l", f"{pkgname}/debian/changelog", "-SDistribution"]
    ).strip()

    deb_host_arch = runc(["dpkg-architecture", "-q", "DEB_HOST_ARCH"]).strip()

    srcname = f"{debsrc}_{debver}"
    buildname = f"{debsrc}_{debver}_{deb_host_arch}"

    chroot = getenv("CHROOT")
    if not chroot:
        if getenv("CHROOT_MODE") == "unshare":
            chroot = next(Path("~/.cache/sbuild").expanduser().glob("debcargo-*"), None)
            if not chroot:
                chroot = f"unstable-{deb_host_arch}"
                print(
                    f"Automatically using sbuild tarball unstable-{deb_host_arch}; however it's strongly recommended to create a separate tarball debcargo-unstable-{deb_host_arch} so your builds won't have to re-download & re-install cargo, rustc, and llvm every time. See README.rst section \"Build environment\" for details.",
                    file=sys.stderr,
                )
        elif (
            runrv(["schroot", "-i", "-c", f"debcargo-unstable-{deb_host_arch}-sbuild"])
            == 0
        ):
            chroot = f"debcargo-unstable-{deb_host_arch}-sbuild"
        elif runrv(["schroot", "-i", "-c", f"unstable-{deb_host_arch}-sbuild"]) == 0:
            chroot = f"unstable-{deb_host_arch}-sbuild"
            print(
                f"Automatically using sbuild chroot unstable-{deb_host_arch}-sbuild; however it's strongly recommended to create a separate chroot debcargo-unstable-{deb_host_arch}-sbuild so your builds won't have to re-download & re-install cargo, rustc, and llvm every time. See README.rst section \"Build environment\" for details.",
                file=sys.stderr,
            )

        elif getenv("SOURCEONLY") != "1":
            abort("could not automatically find a suitable chroot; set CHROOT")

    os.makedirs("./aptroot/etc/apt/apt.conf.d", exist_ok=True)
    os.makedirs("./aptroot/var/lib/apt/lists/", exist_ok=True)
    os.makedirs("./aptroot/etc/apt/preferences.d", exist_ok=True)

    apt_conf = f"""\
# generated by build.py
Apt::Architecture "{deb_host_arch}";
Apt::Architectures "{deb_host_arch}";
Dir "{os.getcwd()}/aptroot";
Acquire::Languages "none";
"""
    with open("./aptroot/apt.conf", "w") as f:
        f.write(apt_conf)

    sources_list = f"""\
# generated by build.py
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian/ {distribution} main
deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian/ {distribution} main
"""
    if distribution in {"experimental", "rc-buggy"}:
        sources_list += f"""
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian/ unstable main
"""
    elif distribution.endswith("-backports"):
        sources_list += f"""
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian/ {distribution[:-10]} main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian/ {distribution[:-10]}-updates main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://security.debian.org/debian-security/ {distribution[:-10]}-security main
"""
    elif distribution in {"unstable", "sid", "testing"}:
        pass
    else:
        assert distribution == "stable"
        sources_list += f"""
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian/ {distribution}-updates main
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://security.debian.org/debian-security/ {distribution}-security main
"""
    with open("./aptroot/etc/apt/sources.list", "w") as f:
        f.write(sources_list)

    os.environ["APT_CONFIG"] = f"{os.getcwd()}/aptroot/apt.conf"
    subprocess.run(["apt-get", "update"], check=True)

    if should_build(f"{srcname}.dsc", f"{pkgname}/debian/changelog"):
        if getenv("REUSE_EXISTING_ORIG_TARBALL") == "1":
            upsver = debver.rsplit("-", 1)[0]
            old_tarball = Path(f"{debsrc}_{upsver}.orig.tar.gz")
            new_tarball = Path(f"{debsrc}_{upsver}.orig.tar.gz.new")
            old_tarball.rename(new_tarball)
            subprocess.run(
                ["apt-get", "-t", "unstable", "source", "--download-only", debsrc],
                check=True,
            )
            if (
                subprocess.run(
                    [
                        "diff",
                        "-ru",
                        "--label",
                        new_tarball,
                        "<(zcat " + str(new_tarball) + " | tar -tvvf-)",
                        "--label",
                        old_tarball,
                        "<(zcat " + str(old_tarball) + " | tar -tvvf-)",
                    ],
                    shell=True,
                ).returncode
                != 0
            ):
                if (
                    input("contents differ, continue with old tarball or abort? [y/N] ")
                    != "y"
                ):
                    sys.exit(1)
            subprocess.run(
                ["tar", "--strip-components=1", "-xf", str(old_tarball)], cwd=pkgname
            )
        runc(["dpkg-source", "--after-build", "."], cwd=pkgname)
        runc(["dpkg-buildpackage", "-d", "-S", "--no-sign"], cwd=pkgname)
        if (
            "UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO" not in debdist
            and getenv("SKIP_SIGN") != "1"
        ):
            runc(["debsign", getenv("DEBSIGN_KEYID", ""), f"{srcname}_source.changes"])

    extra_debs_list = getenv("EXTRA_DEBS", "").split() + extra_debs
    if extra_debs_list:
        os.environ["IGNORE_MISSING_BUILD_DEPS"] = "1"
        print(
            "Given non-empty extra debs; defaulting IGNORE_MISSING_BUILD_DEPS=1",
            file=sys.stderr,
        )

    def check_build_deps_are_ok() -> bool:
        """Returns True if the build deps are satisfied"""
        # TODO: support checking build deps even when some .deb are passed
        os.makedirs("dpkg-dummy", exist_ok=True)
        # Dir::State::Lists is /var/lib/apt/lists by default.
        # Since apt replaces the files in that directory instead of rewriting
        # existing inodes, we can rely on the directory mtime.

        apt_lists_dir = runc(
            ["apt-config", "shell", "v", "Dir::State::Lists/d"]
        ).strip()
        assert apt_lists_dir.startswith("v='/")
        assert apt_lists_dir.endswith("/'")
        apt_lists_dir = apt_lists_dir[3:-1]

        if should_build("dpkg-dummy/status", apt_lists_dir):
            # pretend dpkg status file that marks all packages as installed
            # this is because dpkg-checkbuilddeps only works on installed pkgs
            apt_cache = runc(
                [
                    "apt-cache",
                    "dumpavail",
                    "-o",
                    f"APT::Default-Release={distribution}",
                ]
            )
            extra_deb_cache = "\n".join(
                runc(["apt-cache", "show", deb.split("_")[0]])
                for deb in extra_debs_list
            )
            with open("dpkg-dummy/status.tmp", "w") as f:
                f.write(
                    apt_cache.replace(
                        "Package: ", "Package: \nStatus: install ok installed\n"
                    )
                    + extra_deb_cache
                )
            if not Path("dpkg-dummy/status.tmp").stat().st_size:
                abort(
                    "couldn't generate dpkg-dummy/status, is Debian unstable in your APT sources?",
                )
            Path("dpkg-dummy/status.tmp").rename("dpkg-dummy/status")

        retval = runrv(["dpkg-checkbuilddeps", "--admindir=../dpkg-dummy"], cwd=pkgname)
        success = retval == 0
        log.debug("Build dependencies are satisfied")
        return success

    if not check_build_deps_are_ok() and getenv("IGNORE_MISSING_BUILD_DEPS") != "1":
        abort("Missing build-dependencies, but maybe try '{apt,cargo} update'")

    if getenv("SOURCEONLY") == "1":
        # ??
        sys.exit()

    extra_debs_sbuild = []
    if extra_debs_list:
        extra_debs_sbuild = [f"--extra-package={deb}" for deb in extra_debs_list]
        with tempfile.TemporaryDirectory(
            prefix=f"{srcname}_REPO_"
        ) as extra_debs_repo_tmp:
            # TODO review this:

            # EXTRA_DEBS_SBUILD=("${EXTRA_DEBS[@]/#/--extra-package=}")
            # EXTRA_DEBS_REPO_TMP=$(mktemp -d "${SRCNAME}_REPO_XXXXXXXX")
            # # trap cleans up even if user does Ctrl-C
            # # https://stackoverflow.com/a/14812383 inside "trap" avoids running handler twice
            # trap 'excode=$?; rm -rf "'"$EXTRA_DEBS_REPO_TMP"'"; trap - EXIT' EXIT HUP INT QUIT PIPE TERM
            # # symlinks don't work here
            # ln -f "${EXTRA_DEBS[@]}" "$EXTRA_DEBS_REPO_TMP/"
            # ( cd "$EXTRA_DEBS_REPO_TMP"; apt-ftparchive packages . > Packages )
            # EXTRA_DEBS_AUTOPKGTEST_OPTS=([0]=--autopkgtest-opt=--copy="$PWD/$EXTRA_DEBS_REPO_TMP/:/tmp/$EXTRA_DEBS_REPO_TMP/" [1]=--autopkgtest-opt=--add-apt-source="deb [trusted=yes] file:///tmp/$EXTRA_DEBS_REPO_TMP ./")

            for deb in extra_debs_list:
                Path(extra_debs_repo_tmp).joinpath(deb).symlink_to(deb)
            runc(["apt-ftparchive", "packages", "."], cwd=extra_debs_repo_tmp)
            extra_debs_autopkgtest_opts = [
                f"--autopkgtest-opt=--copy={Path(extra_debs_repo_tmp)}:/tmp/{Path(extra_debs_repo_tmp)}",
                f"--autopkgtest-opt=--add-apt-source=deb [trusted=yes] file:///tmp/{Path(extra_debs_repo_tmp)} ./",
            ]
    else:
        extra_debs_autopkgtest_opts = []

    autopkgtest_opts = ["--run-autopkgtest", "--autopkgtest-root-arg="]
    if getenv("CHROOT_MODE") == "unshare":
        autopkgtest_opts.append(
            f"--autopkgtest-opts=--apt-upgrade -- unshare -t {chroot} {distribution and f'-r {distribution}'}"
        )
    else:
        autopkgtest_opts.append(f"--autopkgtest-opts=-- schroot {chroot}")

    if getenv("SKIP_AUTOPKGTEST") == "1":
        autopkgtest_opts = []
        extra_debs_autopkgtest_opts = []

    lintian_opts = []
    if "UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO" in debdist:
        log.debug("Package version UNRELEASED: configuring lintian accordingly")
        lintian_opts = [
            "--lintian-opt=--suppress-tags",
            "--lintian-opt=bad-distribution-in-changes-file",
        ]

    log.info("Starting sbuild")
    sbuild_cmd = [
        "sbuild",
        "--no-source",
        "--arch-any",
        "--arch-all",
        *(chroot and ["-c", chroot] or []),
        *(getenv("CHROOT_MODE") and ["--chroot-mode", getenv("CHROOT_MODE")] or []),
        *(distribution and ["-d", distribution] or []),
        *extra_debs_sbuild,
        *extra_debs_autopkgtest_opts,
        *autopkgtest_opts,
        *lintian_opts,
        getenv("SBUILD_OPTS", ""),
        f"{srcname}.dsc",
    ]
    runc(sbuild_cmd)

    if getenv("SKIP_AUTOPKGTEST") != "1":
        report(f"analyzing autopkgtest log: {buildname}.test.log")
        with open(f"{buildname.test.log}", "w") as f:
            # TODO replace this
            subprocess.run(
                [
                    "sed",
                    "-ne",
                    "/autopkgtest .*: testing package .* version .*/,$p",
                    f"{buildname}.build",
                ],
                stdout=f,
            )
        runc([str(script_dir / "dev/rust-regressions.sh"), f"{buildname}.test.log"])

    runc(["changestool", f"{buildname}.changes", "adddsc", f"{srcname}.dsc"])
    report(f"build complete: {buildname}.changes")

    if "unknown-section FIXME" in open(f"{buildname}.build").read():
        abort("Please fix the SECTION, found FIXME")

    if (
        "UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO" not in debdist
        and getenv("SKIP_SIGN") != "1"
    ):
        runc(
            [
                "debsign",
                getenv("DEBSIGN_KEYID", ""),
                "--no-re-sign",
                f"{buildname}.changes",
            ]
        )


if __name__ == "__main__":
    build()
