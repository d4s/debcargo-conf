.. contents::

Packaging a crate for Debian
============================

To get set up, run at Debian unstable (recommended)::

  apt update && apt install debcargo

Then for each new package:

To package a new crate, or to update an existing crate
------------------------------------------------------

::

  ./new-package.sh <rust-crate-name>  # or
  ./update.sh      <rust-crate-name>

and follow its instructions.

Note that ``new-package.sh`` is just a symlink to ``update.sh``, to help newcomers.

To package a co-installable older version of a crate
----------------------------------------------------

To maintain an old version of a crate alongside the latest one, first make sure
the latest version is packaged by doing all of the above, then run::

  ./new-package.sh <rust-crate-name> <old-version>  # or
  ./update.sh      <rust-crate-name> <old-version>

and follow its instructions. To save time, you can first copy anything relevant
from ``src/<rust-crate-name>`` to ``src/<rust-crate-name>-<old-version>``, then
adapt it as needed.

You will need excellent reasons to do this. It should be done only for core crates
used by many other crates or programs for which the upgrade path is complex.
For example, if the API significantly changed and requires a lot of work.

Instead, please consider:
* Downgrading or upgrading the dependency.
* If it doesn't exist, open an issue on the upstream issue tracker to
  encourage them to upgrade.
* If possible/relevant, disable a feature if it uses it.
* Wait until upstream upgraded.

To prepare a release
--------------------

::

  ./release.sh <rust-crate-name>                     # or
  ./release.sh <rust-crate-name> <old-version>       # as appropriate
  DISTRO=experimental ./release.sh <rust-crate-name> # to target another distro
  EXTRA_DEBS=build/*.deb ./release.sh <rust-crate-name> # use local dependencies

This prepares the necessary Debian files in ``build/``, and creates a git
branch to manage the packaging until it is accepted in Debian itself. You need
to run additional commands after this - more specific instructions are given to
you about this, by the script after you run it.

Holding packages at old versions
--------------------------------

If you need to keep the latest version in Debian at an older version than is
released on crates.io, e.g. to upload an important bugfix without being blocked
on having to package all the dependencies of the newest version, you can::

  REALVER=<old-version> ./update.sh  <rust-crate-name>  # then
  REALVER=<old-version> ./release.sh <rust-crate-name>

Repackaging the existing revision
---------------------------------

In order to build a package A already in ``debcargo-conf/src``
in the exact version which is present here, do the following::

  $ ./repackage.sh A
  $ cd build
  $ ./build.sh A

If this package is already in the archive and you want to recreate that
exactly, you will need to use the exact same version of debcargo that was
used previously. This version is mentioned in ``debian/changelog``.


Build environment
=================

To set up a suitable build environment for ``./build.sh``::

With schroot::

  $ sudo apt-get install devscripts reprepro debootstrap sbuild dh-cargo schroot autopkgtest quilt
  $ sudo sbuild-createchroot --include=eatmydata,ccache,gnupg,dh-cargo,cargo,lintian,perl-openssl-defaults \
      --chroot-prefix debcargo-unstable unstable \
      /srv/chroot/debcargo-unstable-amd64-sbuild http://deb.debian.org/debian

With sbuild + unshare::

$ sudo apt install devscripts mmdebstrap sbuild uidmap dh-cargo autopkgtest quilt
$ mkdir -p ~/.cache/sbuild
$ mmdebstrap --variant=buildd --include ccache,gnupg,dh-cargo,cargo,lintian,perl-openssl-defaults unstable ~/.cache/sbuild/debcargo-unstable-amd64.tar.xz

In case you run out of space on /tmp::

$ sudo mount -o remount,size=5G /tmp/


Note that you need to set CHROOT_MODE=unshare to use ./build.sh with unshare.

An explanation of this, plus more recipes, can be found on the `sbuild wiki
page <https://wiki.debian.org/sbuild>`_.

If you need to pass additional options to sbuild, like "--arch=i386", then set
the SBUILD_OPTS environment variable.

Normally, ``./build.sh`` will fail early if not all the build dependencies are
available in your local apt cache. If you are packaging a large dependency tree
however, to avoid many round-trips through NEW it is possible to bypass this
check and build all the packages together. Suppose package B depends on package
A, then you can run something like::

  $ export IGNORE_MISSING_BUILD_DEPS=1
  $ ./release.sh A
  $ ( cd build && ./build.sh A )
  # push pending and checkout master
  $ ./release.sh B
  $ ( cd build && ./build.sh B librust-A*.deb )

Or you can use the ``EXTRA_DEBS`` environment variable, which ``build.sh`` will
inhert, like::

  $ EXTRA_DEBS=build/*.deb ./release.sh A

The extra arguments after ``./build.sh B <args>`` is extra deb files to pass to
sbuild to use as dependencies. In this case, ``librust-A*.deb`` should have
been built by the previous step. Alternatively, use the environment variable
``EXTRA_DEBS``, like so: ::

  $ EXTRA_DEBS=librust-A*.deb ./build.sh B
  $ EXTRA_DEBS=librust-A.deb,librust-B.deb ./build.sh C

After everything is built successfully, you can ``dput`` all of them and then
push all the ``pending-*`` branches as normal.


Repository structure
====================

``pending-*`` branches are managed by ``./release.sh``, so please don't manage
them yourself as you will interfere with the working of that script. The
intention is that they should only differ from the master branch by 1 commit,
i.e. the ``dch -r`` commit created by ``./release.sh``.

If you want to create separate non-master branches, that is fine - just don't
call them ``pending-*`` and don't run ``./release.sh`` on those branches. If you
want to test your crate, instead run::

  cd build && [SOURCEONLY=1] ./build.sh <rust-crate-name> [<old-version>]

omitting or not omitting the stuff in [] as needed.

Like many other Debian git repositories, we don't follow "feature branch"
practises here. We generally don't package just 1 or 2 rust crates at a time,
but all of its dependencies and sometimes some reverse-dependencies too. So
normally we'll be touching a few dozen packages at once. In this context, it's
good to merge often, to avoid conflicts with someone else that might also need
to touch those too in the next few days.

To match a release (i.e. a ``.deb`` or a ``.dsc`` file) to a commit, find the
commit message that actually says "Release package X". This will usually be a
merge commit.


Expert mode & packaging multiple packages
=========================================

You should get used to the single-packaging workflow a bit first, including
doing a few `test builds <#build-environment>`_ of your package. Otherwise the
instructions below may seem a bit opaque.

1. ``rm -rf build/* && sbuild-update -udr debcargo-unstable-amd64-sbuild`` -
   clears out your build directory, making the subsequent steps a bit faster.
2. ``./update.sh <CRATE>`` for all your relevant packages
3. Do any manual updates.
4. ``cd build`` then ``IGNORE_MISSING_BUILD_DEPS=1 ./build.sh <CRATE> *.deb``
   for all your relevant packages, in dependency order.
5. Deal with any issues that come up.
6. Push your updates to our git.
7. Run ``dev/list-rdeps <CRATE> [<CRATE> ...]`` on all the crates you updated.
   Any reverse-dependencies that are affected, also need to be updated and you
   should repeat steps 1-7 (including this step) for them as well, until this
   step lists no new packages that are affected.
8. ``./release.sh <CRATE>`` for all the packages you updated, running the build
   again if necessary. It may be possible to do this out of dependency order,
   assuming you didn't have to make significant changes in step (5). If you
   did, then this step also has to be done in dependency order.
9. Push your ``pending-*`` branches to our git.

I like to have 4 shell windows open for this:

1. To do the manual updates.
2. To explore git, to remember what step you're on and to lookup previous
   reference material.
3. To explore the build directory, e.g. logs and crate source code.
4. To run a build. Try to have one running here at all times, for the next
   package you didn't look at yet, to save time waiting.

There are also various scripts in ``dev/*`` that might help you. They should
have a couple lines at the top of the source code describing their
functionality and some brief usage instructions.

Whew, thanks for all your work!


General packaging tips
======================

Dependencies on clippy
----------------------

Patch away dependencies on "clippy" unless it is a "real" dependency. Usually
crates only use clippy to lint themselves and it is not a "real" dependency
in the sense that they actually import clippy's code for what they do.

If you want to be sure, ``rg clippy`` and check that all the usages of it are
inside ``cfg_attr`` declarations. If so, then just get rid of it.

OS-specific crates
------------------

See redox-syscall for examples on how to deal with these.

If this is unclear, ask on IRC.

Architecture-specific crates
----------------------------

This is a bit harder. Usually there are two options:

1. The crate should build a dummy/no-op version of itself "out-of-the-box"
   on the architectures it doesn't work on.
2. Dependent crates should depend on it with a platform-specific dependency,
   see https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#platform-specific-dependencies

(1) involves less burden for others, both for dependent crates and for us
packagers, since we don't have to override d/rules to ignore test failures on
non-working architectures. You should communicate to upstream that this is
the preferred approach.

In the case of (2), the crate should document exactly what conditional should
be used, and keep this documentation up-to-date. This allows us to easily
determine if dependent crates are using the correct conditional. You will then
have to override d/rules for this crate, see src/simd for an example.

You should file a bug upstream if the crate does neither (1) nor document the
conditions for (2), e.g. https://github.com/hsivonen/simd/issues/25

(Actually the above applies even for "OS-specific crates" but then (2) is
obvious so documentation is less necessary, and dependent crates all do it
correctly already.)

Collapsing features in debcargo.toml
------------------------------------------

TL;DR: Set `collapse_features = true` in debcargo.toml, unless something
breaks. This eliminates empty feature packages and speeds up the NEW trip.

Rust and Debian have two different levels of abstraction when handling
dependencies and the relationship between them. In Rust the lowest level is a
feature, while in Debian it's the binary package.

This means that the following dependency chain is not a problem in rust:

- crate A with feature AX depends on crate B with feature BY
- crate B with feature BX depends on crate A with feature AY

This is a perfectly valid situation in the rust+cargo ecosystem. Notice that
there is no dependency cycle on the per-feature level, and this is enforced by
cargo; but if collapse_features is used then package A+AX+AY would cyclicly
depend on package B+BX+BY.

This is reflected in the Debian packages by producing `Provides` lines for all
combinations of features, and this can become a quite large section.

Setting `collapse_features = true` in debcargo.toml removes this behaviour and
is generally recommended, unless when it leads to dependency cycles of Debian
packages. If that happens, those must be broken up by having some or all of the
packages set this feature to false.

Changed orig tarballs
---------------------

Sometimes the orig.tar generated by debcargo might change e.g. if you are using
a newer version of debcargo and one of the dependencies relating to generating
the tarball was updated and its behaviour changed - compression settings,
tarball archive ordering, etc. This will cause your upload to get REJECTED by
the Debian FTP archive for having a different orig.tar. In this case, set
``REUSE_EXISTING_ORIG_TARBALL=1`` when running ``./release.sh``.

ITPs
----

Don't file ITPs for library crates, but do file them for binary crates.

Generally we'll be uploading a dozen crates or so at once. Submitting ITPs for
these is unnecessary since we're the only ones uploading and there is no chance
of conflict. It would only be spam for the bug tracker. Please instead
coordinate uploads on the ``#debian-rust`` IRC channel.

Testing
-------

Debian has two types of tests:

1. pre-install tests run in ``debian/rules``
2. post-install tests defined in ``debian/tests/control``

For Debian rust packages, in (1) we run the crate's test suite with default
features but only if there are no dev-dependencies, and in (2) we run the whole
test suite with each feature enabled separately plus ``--no-default-features``
and ``--all-features``.

Sometimes, tests require extra tweaks and settings to work. In this case, you
can tweak ``debian/rules`` for (1), and for (2) you will simply have to mark
the relevant tests as broken using ``test_is_broken = true``. See the existing
crate configs for examples.

Other times, the tests are simply broken or can't be run in Debian. In this
case you should disable the test in (1) by running ``dh_auto_test -- build``
instead of the default ``dh_auto_test -- test --all``, and for (2) again you
should mark the relevant tests as broken.
These tests are going to be marked as flaky in autopkgtest, still executed but
won't fail the autopkgtest run.

Please note that ``[packages.lib]\ntest_is_broken = true`` will transitively
disable tests for all combinations of features. Sometimes this is correct e.g.
if the test actually breaks for all features. Sometimes this is *not* correct,
e.g. if the test only breaks for ``--no-default-features``. In the latter case
you should instead patch the crate to ignore those tests when the relevant
features are absent - e.g. ``src/regex-automata/debian/patches/ignore-std-tests.patch``.

Binary-crate has "required-features"
------------------------------------

See ``src/dotenv`` for an example on dealing with this.

Binary-crate has conflicting name
---------------------------------

See ``src/fd-find`` for an example on dealing with this.

Updating the dependencies
-------------------------

In some cases, libraries/programs are forcing an old version of a library as
dependencies. In order to limit the number of duplicated libraries in the
archive, please try to evaluate if a newer version of the dependencies could be
used.

To achieve that, after ``./update.sh``, try::

  $ cd build/<package>/
  $ rm -rf .pc # sometimes this is necessary due to minor debcargo bug
  $ quilt push -a
  $ quilt new relax-dep.diff
  $ quilt edit Cargo.toml
  $ quilt header -e --dep3
  $ quilt refresh
  $ cargo build # check that it works. if it does, then
  $ cp -R patches ../../src/<package>/debian

Suppose you want to change the dependency from 0.3 to 0.5. If the crate builds
with no further source changes, then we would change the required version in
``Cargo.toml`` from ``0.3`` to ``>= 0.3, < 0.6`` or something like that. Then
the convention is to put all these changes into a single patch called
``relax-dep-versions.patch``.

OTOH, if the cargo build fails, and you can fix it up by editing the source
code in a minor way to use the new crate API, then: for each crate that needs
to be updated, you should instead name the patch ``update-dep-<crate>.patch``
and add both the ``Cargo.toml`` and the source code changes to it. The change
to ``Cargo.toml`` would then simply say (e.g.) ``0.5`` since the older versions
actually don't work, and not the version range from the previous paragraph.

If you want to make a crate work with an older dependency version than listed
in ``Cargo.toml`` (for example 0.3 instead of 0.5), you cannot use a flexible
version requirement like ``>= 0.3, < 0.6``.  Instead you have to specify only
the older version, in this example ``0.3`` (`explanation`_).

.. _explanation: https://salsa.debian.org/rust-team/debcargo-conf/merge_requests/86#note_135456

Information on patch headers is available in `dep3`_.
Use (some of) the headers to explain **why** the patch exists.

.. _dep3: https://dep-team.pages.debian.net/deps/dep3/

Help, something went wrong!
---------------------------

Sometimes, the error messages are not the most informative. In this case you
can try re-running the command with ``RUST_BACKTRACE=1``. If you are using the
``debcargo`` from Debian's own repositories, you should also install the
``debcargo-dbgsym`` package, otherwise the stack trace will be next to useless.
Make sure you have the `debug repository <https://wiki.debian.org/HowToGetABacktrace#Installing_the_debugging_symbols>`_
enabled in your APT sources.


Some ramblings
--------------

In ``#debian-rust`` came these two blog posts along with the remark of _good read_
 * https://blog.hackeriet.no/packaging-a-rust-project-for-debian/
 * https://blog.hackeriet.no/packaging-rust-part-II/

Now are they, those two blog posts, parked here. Waiting for better integration.

Also, there is a rust_hacks.md alongside this README that summarizes some
useful "hacks" in packaging.


Developing Rust code using Debian-packaged crates
=================================================

While perhaps not the stated intention, the Rust ecosystem in Debian
is actually quite usable for developing Rust code in general. Thanks
to `source replacement
<https://doc.rust-lang.org/cargo/reference/source-replacement.html>`_,
Cargo can be configured to use only local, Debian-provided packages by
placing something like the following in ``~/.cargo/config.toml`` (for
user-wide effect) or in a given project's ``.cargo/config.toml``::

  [net]
  offline = true
  
  [source]
  
  [source.crates-io]
  replace-with = "debian"
  
  [source.debian]
  directory = "/usr/share/cargo/registry"

In this state, Cargo will only look for crates installed as Debian
packages on the local system.
