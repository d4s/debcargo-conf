#!/usr/bin/env python3

"""
Dependency aware build system - experimental shell
2024 Debian Rust team
2024 Federico Ceratto <federico@debian.org>
Released under AGPL
"""

from typing import Dict
import os
import subprocess
from enum import Enum

import cmd2  # debdeps: python3-cmd2

BuildStatus = Enum("BuildStatus", ["Unknown", "OK", "Failed"])


GREEN = "\033[92m"
RESET = "\033[0m"


class Pkg:
    def __init__(self, pkg_name: str) -> None:
        self.name = pkg_name
        self.deps: Dict[str, Pkg] = {}
        self.status: BuildStatus = BuildStatus.Unknown

    def status_icon(self) -> str:
        """Show simple status icon."""
        if self.status is BuildStatus.Unknown:
            return "○"

        if self.status == BuildStatus.OK:
            return "\033[92m\U0001F7E2\033[0m"

        return ""

    def summary(self) -> str:
        """Show package name and status"""
        return self.name + " " + self.status_icon()


class DabsShell(cmd2.Cmd):
    intro = "Welcome to the DABS Shell. Type help or ? to list commands.\n"

    def __init__(self):
        # super().__init__(persistent_history_file="dabs_history.dat"),
        super().__init__(
            persistent_history_file="dev/dabs/dabs_history.dat",
            startup_script="dev/dabs/startup",
        ),
        self.current_package = None
        self.target_package = None

    @property
    def prompt(self):
        current = (
            "unset" if self.current_package is None else self.current_package.summary()
        )
        target = self.target_package.summary() if self.target_package else "unset"
        return f"({target} {current}) "

    def do_set_current(self, pkg_name):
        """Set current package name"""
        if not pkg_name:
            print("Please provide a package name.")
            return

        self.current_package = Pkg(pkg_name)

    def do_set_target(self, pname):
        """Set target package name"""
        if not pname:
            print("Please provide a package name.")
            return
        pkg = self.search_pkg_in_tree(pname)
        if pkg:
            self.target_package = pkg
        else:
            self.target_package = Pkg(pname)

        if self.current_package is None:
            self.current_package = self.target_package

    def do_status(self, _):
        """Show the current build status"""
        sa = os.getenv("SKIP_AUTOPKGTEST", "0")
        print("Autopkgtest", "enabled" if sa == "0" else "disabled")
        dso = os.getenv("DEB_SIGN_OPTS", "") == "--no-sign"
        print("Signing", "disabled" if dso else "enabled")

    def do_toggle_autopkgtest(self, _):
        """Toggle autopkgtest as part of the build"""
        disabled = os.getenv("SKIP_AUTOPKGTEST", "0")
        disabled = bool(int(disabled))
        if disabled:
            print("Enabling autopkgtest")
            os.environ["SKIP_AUTOPKGTEST"] = "0"
        else:
            print("Disabling autopkgtest")
            os.environ["SKIP_AUTOPKGTEST"] = "1"

    def do_toggle_signing(self, _):
        """Toggle signing as part of the build"""
        # TODO handle unexpected values
        dso = os.getenv("DEB_SIGN_OPTS", "")
        if dso:
            print("Enabling signing")
            os.environ["DEB_SIGN_OPTS"] = ""
        else:
            print("Disabling signing")
            os.environ["DEB_SIGN_OPTS"] = "--no-sign"

    def do_build(self, _):
        """Build the current package."""
        if not self.target_package:
            print("No target package set. Please set a target package first.")
            return

        # TODO: do repackage if needed

        os.environ["CHROOT_MODE"] = "unshare"
        os.environ["CHROOT"] = "debcargo-unstable-amd64"
        r = subprocess.run(
            ["./build.sh", self.target_package.name],
            check=False,
            cwd="build",
        )
        if r.returncode == 0:
            self.target_package.status = BuildStatus.OK
        else:
            self.target_package.status = BuildStatus.Failed

    def do_diff(self, _):
        """Show git diff"""
        subprocess.run(["git", "diff"], check=False)

    def search_pkg_in_tree(self, name: str):
        if not self.target_package:
            return

        def lookup(p, name):
            if p.name == name:
                return p
            for dep in p.deps.values():
                found = lookup(dep, name)
                if found:
                    return found

        return lookup(self.target_package, name)

    def do_tree(self, _):
        """Print package tree"""
        if not self.target_package:
            return

        def f(p, level):
            print("  " * level, p.name, p.status_icon())
            for dname, dep in sorted(p.deps.items()):
                f(dep, level + 1)

        f(self.target_package, 0)

    def do_update(self, _):
        """Update the current package."""
        if not self.current_package:
            print("Please set a current package first.")
            return

        r = subprocess.run(
            ["./update.sh", self.current_package.name],
            check=False,
        )

    def do_repackage(self, _):
        """Repackage the current package."""
        if not self.current_package:
            print("Please set a current package first.")
            return

        r = subprocess.run(
            ["./repackage.sh", self.current_package.name],
            check=False,
        )

    def do_release(self, _):
        """Release the current package."""
        if not self.current_package:
            print("Please set a current package first.")
            return

        r = subprocess.run(
            ["./release.sh", self.current_package.name],
            check=False,
        )

    def do_upload(self, _):
        """Upload the current package."""
        if not self.current_package:
            print("Please set a current package first.")
            return

        raise NotImplementedError

    def do_exit(self, _):
        """Exit the shell."""
        print("Exiting...")
        return True


if __name__ == "__main__":
    DabsShell().cmdloop()
