# Debian Rust packaging guide by example

This guide helps one to grasp the basics of packaging Rust crates in the Debian
Rust team by going through a concrete example. Feel free to skip parts you are
familiar with, or to update it with better and more accurate information.

What Rust calls a "crate" is a self-contained unit of code. Think of the source
code of a C program or library, but due to Rust defaulting to static
compilation, it sometimes functions like a shared library, in that a dependent
crate "links" to it. It's in many ways synonymous with a "package" in Debian or
other package systems' sense. In this guide, we'll use "crate" when referring
to a Rust crate, and "package" when referring to a Debian package, including
the packaged artifact of the crate.

The crate we'll use as example is [`ouch`](https://crates.io/crates/ouch), an
all-in-one (de)compression program.

## Prepare

First, let's install needed tools, export some env vars, and clone the
`debcargo-conf` repository if you haven't already:

```sh
$ sudo vi /etc/apt/sources.list # and add unstable
$ sudo apt update
$ sudo apt install devscripts quilt git rustc cargo debcargo
$ cargo install cargo-debstatus
$ export DEBNAME="<YOUR NAME>"
$ export DEBEMAIL="<YOUR EMAIL>"
$ export QUILT_PATCHES="debian/patches"
$ cd ~/works
works $ git clone https://salsa.debian.org/rust-team/debcargo-conf.git
works $ cd debcargo-conf
debcargo-conf $ git config user.name "<YOUR NAME>"
debcargo-conf $ git config user.email "<YOUR EMAIL>"
```

First, add the `unstable` release, where most of our packaging happens, which
means the most recent packages Debian has for general use. I haven't tried
using `testing` or even `stable`. I won't recommend that, ask on #debian-rust
if you insist.

`devscripts` has some convenience scripts for every Debian maintainer. See
https://salsa.debian.org/debian/devscripts for a list.

`quilt` is a patch managing tool widely used in Debian. Read
https://wiki.debian.org/UsingQuilt. It uses `less` as the pager by default, so
install it or configure it to use what you prefer.

`DEBNAME` and `DEBEMAIL` are the standard way to tell Debian packaging tools
who you are.

`rustc` and `cargo` are, well, rustc and cargo. But the Debian packaged
version. We haven't yet packaged nightly or even beta Rust, not to mention
`rustup`, so to package Rust for Debian, you gotta stick to what is in Debian.
At least for now.

Unlike most Debian packages, we take a rather novel approach, that is, we only
store an "overlay" `debian/` directory for each packaged crate, all located in
`debcargo-conf/src/{crate}/debian`. For simple crates, only a few files are
needed: `changelog`, `copyright`, and `debcargo.toml`. You should be familiar
with the first two and their containing `debian/` directory, if not, read
[placeholder for a beginner's guide to Debian packaging] first. The latter is
specific to [`debcargo`](https://salsa.debian.org/rust-team/debcargo), the
Automated Rust Packaging Tool for Debian ™️. Alright, it's just a tool that
automates the creation of the usual package necessities like origin source
tarballs, `.dsc` and `.changes` files, written by infinity0 with help from
others. Check out [this
example](https://salsa.debian.org/rust-team/debcargo/-/blob/master/debcargo.toml.example)
for some options it provides.

`cargo-debstatus` is a cargo subcommand written by kpcyrd. It retrieves
dependencies of a crate, finds out which have been packaged and which have not,
then list them in a nice tree format. It's installed using `cargo install`
because it hasn't been uploaded to Debian, but we are working on it.

Then, to set up a build enviroment for `build.sh`, our omni-build script:

```sh
$ sudo apt install reprepro debootstrap sbuild dh-cargo schroot autopkgtest
$ sudo sbuild-createchroot --include=eatmydata,ccache,gnupg,dh-cargo,cargo,lintian,perl-openssl-defaults \
      --chroot-prefix debcargo-unstable unstable \
      /srv/chroot/debcargo-unstable-amd64-sbuild http://deb.debian.org/debian
```

We are using [`sbuild`](https://wiki.debian.org/sbuild) to isolate build
environments. Read the wiki and follow the configuration section to your need.
I recommend adding this to your `~/.sbuildrc` so it opens a shell inside the
environment for inspection:


```perl
$external_commands = {
    # %s means open a shell
    # TERM=xterm-256 enables color output, delete if you'd rather not
    'build-failed-commands' => ['env TERM=xterm-256color %s'],
};
```

`build.sh` hasn't been changed to make use of build environment tools other
than `schroot` (like `unshare` or even Docker), so bear with me for the time
being. If you are smart enough to make it work, don't hesitate to share by
pushing your changes!

## NEW

First, remove the overlay directory of `ouch`:

```
debcargo-conf $ rm -r src/ouch
```

Why? Well, at the time of writing, despite not packaged in Debian, it's already
"packaged" in in this repository, just waiting to be uploaded, which is what
really defines "packaged" for users. That means if you skip, what you get is an
update, not a NEW package this section describes. Skip if you are okay with
that.

Like `build.sh`, we have another script for updating the overlay directory:
`update.sh`. For simple cases, just run `./update.sh {crate}`. So in this
guide, we run `update.sh ouch`:

```
debcargo-conf $ ./update.sh ouch
    Updating crates.io index
Generate binary crate with default name 'ouch', set bin_name to override or bin = false to disable.
Wrote back file to overlay: copyright.debcargo.hint
Wrote back file to overlay: changelog
Package Source: build/ouch
Original Tarball for package: build/rust-ouch_0.4.1.orig.tar.gz

FIXME found in the following files.
         •  build/ouch/debian/changelog
         •  build/ouch/debian/control
         •  build/ouch/debian/copyright
        (•) build/ouch/debian/copyright.debcargo.hint
(skipped for brevity)
```

The script fetched the crate, read some metadata, and generated some files. See
that "binary crate" line? We'll get to it later. For now, press Enter:

```
diff --git a/src/ouch/debian/changelog b/src/ouch/debian/changelog
new file mode 100644
index 000000000..c86b323a1
--- /dev/null
+++ b/src/ouch/debian/changelog
@@ -0,0 +1,5 @@
+rust-ouch (0.4.1-1) UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO; urgency=medium
+
+  * Package ouch 0.4.1 from crates.io using debcargo 2.6.0
+
+ -- Blair Noctis <n@sail.ng>  Wed, 19 Apr 2023 17:59:03 +0000
diff --git a/src/ouch/debian/copyright b/src/ouch/debian/copyright
new file mode 100644
index 000000000..f69bb0263
--- /dev/null
+++ b/src/ouch/debian/copyright
@@ -0,0 +1 @@
+FIXME fill me in using ./copyright.debcargo.hint as a guide
diff --git a/src/ouch/debian/copyright.debcargo.hint b/src/ouch/debian/copyright.debcargo.hint
new file mode 100644
index 000000000..869089126
--- /dev/null
+++ b/src/ouch/debian/copyright.debcargo.hint
@@ -0,0 +1,51 @@
+Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
+Upstream-Name: ouch
+Upstream-Contact:
+ Vinícius Rodrigues Miguel <vrmiguel99@gmail.com>
+ João M. Bezerra <marcospb19@hotmail.com>
+Source: https://github.com/ouch-org/ouch
+
+Files: *
+Copyright:
+ FIXME (overlay) UNKNOWN-YEARS Vinícius Rodrigues Miguel <vrmiguel99@gmail.com>
+ FIXME (overlay) UNKNOWN-YEARS João M. Bezerra <marcospb19@hotmail.com>
+License: MIT
+Comment:
+ FIXME (overlay): Since upstream copyright years are not available in
+ Cargo.toml, they were extracted from the upstream Git repository. This may not
+ be correct information so you should review and fix this before uploading to
+ the archive.
(skipped for brevity)
```

So that's how those generated files look like. There's `d/changelog` (we call
`debian/` paths like that in Debian), there's `d/copyright`, and there's…
`d/copyright.debcargo.hint`. What's that?

Well, as you may have guessed from its name, it's a `hint` for `d/copyright`
used by `debcargo`. Aside from being a template for the real thing, it has few
to do with us now. So leave those "hint" files alone, just `git add` them when
committing.

There are a few FIXMEs, so, fix them! But first, that
`UNRELEASED-FIXME-AUTOGENERATED-DEBCARGO` thing is there to stay. Why? It's a
placeholder that debcargo uses to tell if a crate is waiting to be uploaded.
For a non-DD maintainer, just leave it be, a DD will change it when uploading.
If you _are_ a DD, then `release.sh` is for you.

After the diff there's more. Read that. It also generated a `build/sd`
directory, the usual Debian package directory where a `debian/` resides along
with the actual source, and a `rust-{crate}_{version}.orig.tar.gz` outside it.

By the way, this is a new package by looking at `--- /dev/null`, which means
these files are new (diff'ed to nothing).

## Copyright matters

First, let's "fix" `d/copyright`. Debian is very serious on this. The hint file
has pre-filled some info, so let's make use of it:

```sh
debcargo-conf $ cp src/ouch/debian/copyright.debcargo.hint src/ouch/debian/copyright
debcargo-conf $ vi src/ouch/debian/copyright
```

If you don't know how `d/copyright` works… well, its first line says `Format:`,
the link after it may be of some help.

The second paragraph starts with `Files: *`. It's the only paragraph needed for
most simple crates where the author(s) and maybe a few contributors hold the
full copyright. Replace `FIXME (overlay) UNKNOWN-YEARS` with the copyright
years you found in the crate's LICENSE file, then remove the `Comment:` lines,
which are meant for complicated situations where you need to let ftpmasters
know the details.

After that, there may be some `Files: LICENSE.*` paragraphs. That's usually
redundant where the license file(s) holds the same license as other files. Just
delete those.

Then goes a `Files: debian/*` paragraph. Copyright on `debian/` belongs to the
maintainers, and the defaults usually suffice. We usually keep them licensed
under the same terms as the crate for simplicity.

The last paragraph(s) are the license texts. Debian has some common licenses
under `/usr/share/common-licenses`; if the license is not there, we have to
reproduce it at the end of `d/copyright`. The Rust community prefers MIT and
Apache 2.0, as that's how the Rust project is (dual) licensed. `debcargo` does
this for us if the license is easy to find, which is the most common case.

## `debcargo.toml`

Then we have this [TOML](https://toml.io) file. Open it, there are… only two
lines.

```toml
overlay = "."
uploaders = ["Blair Noctis <n@sail.ng>"]
```

The first line tells `debcargo` this is the overlay directory. There's usually
no reason to change that.

The second line tells Debian and people you are the uploader for this package,
because you are the one who created this packaging effort.

For simple crates, that would suffice. But this time we need more.

Remember the "binary crate" line we saw earlier? So ouch is a binary crate.
That means it builds to a binary that's executable, and we want to install it
for later use. (Some crates have more, but you get the idea.) Sometimes a
library crate has some unwanted binaries like test programs, in which case we
could add a `bin = false` line to make debcargo disable building binaries.

A binary crate needs a few more things to be filled out. First,
`source.section`:

```toml
[source]
section = "utils"
```

`[source]` means it's for source packages, which we often call `src:foo`.

[Sections](https://www.debian.org/doc/debian-policy/ch-archive.html#sections)
is a way to categorize packages. For available sections, see
https://packages.debian.org/unstable/. Note that the link text is a section's
descriptive name, the actual section ID (?) lies in the URL and after
"Subsection" in its own page's heading. `ouch` falls into the Utilities
section, so here it's `utils`. This translates to [the `Section`
line](https://www.debian.org/doc/debian-policy/ch-controlfields.html#section)
in
[`d/control`](https://www.debian.org/doc/debian-policy/ch-controlfields.html#source-package-control-files-debian-control).
It also implies the `Section` line for binary packages if you don't specify
otherwise.

Then we have `packages.bin.summary` and `packages.bin.description`:

```toml
[source]
section = "utils"

[packages.bin]
summary = "Unified compression and decompression CLI"
description = """
ouch is a unified CLI that compresses to and decompresses from various formats,
currently tar, zip, gz, xz/lzma, bz(2), lz4, sz, zst. It's easy to use and quite
fast.
"""
```

 `summary` is an one line description of "what this package is". `description`
 is the longer "what can this package do, and what's the other information I
 need to know about it". Upstream usually has those, but don't just copy-paste,
 there's sometimes bluff. Make sure Debian users know what this **really** is.
 
 They together form [the `Description`
 field](https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-description)
 for a binary package.

 ## Dependencies… there are always dependencies

 Software has become larger and larger. No one can write the whole codebase,
 neither do they have the knowledge to. So we write what we're good at, and use
 what other people wrote that they're goot at.

 Back to packaging. You need to know which crates our crate depends on. You can
 check https://crates.io/crates/{crate}/dependencies, or you can use
 `cargo-debstatus`.

```
debcargo-conf $ cd build/ouch
ouch $ cargo debstatus
 Downloaded (quite some other crates) (and their versions)
ouch v0.4.1 (/home/i/works/debcargo-conf/build/ouch)
├── atty v0.2.14 (in debian)
├── bstr v1.1.0
│   ├── memchr v2.5.0 (in debian)
│   ├── once_cell v1.17.0 (in debian)
│   ├── regex-automata v0.1.10 (in debian)
│   └── serde v1.0.152 (in debian)
├── fs-err v2.9.0
(skipped for brevity)
├── lzzzz v1.0.4
├── ubyte v0.10.3
(skipped for brevity)
[build-dependencies]
(skipped for brevity)
└── clap_mangen v0.2.6
[dev-dependencies]
├── infer v0.12.0
│   └── cfb v0.7.3
(skipped for brevity)
```

See those lines ending with `(in debian)`? They are, well, in Debian. Those
without may also be in Debian, but the versions don't match. It's not a problem
for usual Rust users, because crates.io holds all the versions ever published
and cargo just pulls whatever a crate asks for, but in Debian we (usually) have
only one version for a given package. We do have versioned packages which are
called `foo-1` which means the `foo` package at version `1`, where the mainline
may be at 2. This should be used sparsingly, as unrestricted versioned packages
will bloat the archive. That said, if making things work with a single version
takes too much work, a few versioned packages are totally acceptable. Just be
fair to fellow maintainers.

Other than that, those without are what we're gonna package first.

Notice `[build-dependencies]` and `[dev-dependencies]`? The former, like the
name suggests, is dependencies used when building the crate. They are always
needed. The latter, while indeed used when developing the crate, mostly mean
"test dependencies" for us, which sometimes can be skipped without failing to
produce a `.deb`, but it's better not to.

Looks like we don't have `bstr`, right? Wrong.

```
debcargo-conf $ head src/bstr/debian/changelog
rust-bstr (1.4.0-1) experimental; urgency=medium

  * Package bstr 1.4.0 from crates.io using debcargo 2.6.0
  * Set test_is_broken for the "unicode" feature, the crate
    refuses to build if "unicode" is enabled but "std" is
    not.
```

We have bstr 1.4.0 packaged, but in `experimental`. It's even bumpier than
`unstable`, and we usually don't use it unless the release is in freeze or
uploading to unstable poses too much risk. Here it means someone made it build,
so we only need to rebuild it:

```
debcargo-conf $ ./repackage.sh bstr
debcargo-conf $ cd build && ./build.sh bstr
(countless lines of build log)
build $ ls *.deb
librust-bstr-dev_1.4.0-1_amd64.deb
```

`repackage.sh` is used to generate the build directory without bumping
`d/changelog` entry like `update.sh` would. `build.sh`, like `update.sh`, in
simple cases is just `./build.sh {crate}` despite requiring being run under
`build/`. After quite some log lines, the `.deb` will be under `build`, if the
build was successful.

Next is `fs-err`. It's, at the time of writing, not uploaded. So `rm -r
src/fs-err` (because I pushed it there), and go through the NEW package process
for it, then build:

```
debcargo-conf $ ./update.sh fs-err
debcargo-conf $ cd build && ./build.sh fs-err
(log lines)
+------------------------------------------------------------------------------+
| Summary                                                                      |
+------------------------------------------------------------------------------+

Autopkgtest: fail
(skipped for brevity)
debcargo-conf builder: analyzing autopkgtest log: rust-fs-err_2.9.0-1_amd64.test.log
UNKNOWN
=======

rust-fs-err_2.9.0-1_amd64.test.log
error[E0658]: use of unstable library feature 'ready_macro'
error[E0658]: use of unstable library feature 'ready_macro'
error[E0658]: use of unstable library feature 'ready_macro'
librust-fs-err+tokio-dev:tokio FAIL non-zero exit status 101
rust-fs-err:@        FAIL non-zero exit status 101


You should: Analyze the relevant test log and deal with it. Ask in #debian-rust for help if you get stuck.
Explanation: We weren't able to automatically guess the reason behind the test failure

debcargo-conf builder: build complete: rust-fs-err_2.9.0-1_amd64.changes
```

Oh. It failed. That's normal. Otherwise there's no need for so many maintainers.
Anyway, let's fix it.

The line `error[E0658]: use of unstable library feature 'ready_macro'` exposed
the culprit. As we said earlier, only stable Rust has been packaged, so
unstable features can't be used. And notice the line
`librust-fs-err+tokio-dev:tokio FAIL non-zero exit status 101`, clearly it's
the feature `tokio`. What are we gonna do? Disable it, of course. By patching
its `Cargo.toml`.

One word about the tests: what failed is `autopkgtest`, a testing tool
developed by CI team. We at Rust team split each feature of our crates into
separate tests then run them using `autopkgtest`. Most upstreams don't test to
that level of detail, but it has captured quite a few problems otherwise hidden.
On the other hand, some features in some crates are meant to be enabled in all
circumstances, or only in a few valid combinations. For those we need to mark
some tests "flaky" by writting this in `debcargo.toml`:

```toml
[packages."lib+feature"]
test_is_broken = true

# or, sometimes:
[packages.lib]
test_is_broken = true

[packages."lib+feature"]
test_is_broken = false
```

Read https://salsa.debian.org/rust-team/debcargo/-/blob/master/debcargo.toml.example
for how this works.

But that's not the case here.

## Patching

If you haven't heard of it, a patch matches an old state of a chunk of code
(actually, text) then changes it to a new state. Some argue it's called a diff,
which describes both states, while patching is the action of applying it. These
two word are used interchangeably. In Debian we make a lot of patches. Also, Git
commits can be expressed as patches, try running `git show` in one of your
repositories.

Create the `d/patches` directory and link it to the build directory:

```sh
debcargo-conf $ mkdir src/fs-err/debian/patches
debcargo-conf $ ln -s src/fs-err/debian/patches build/fs-err/debian/
debcargo-conf $ cd build/fs-err
```

This way our patches are "sync"ed to its `src/`.

Then use quilt to create a patch:

```sh
fs-err $ quilt new relax-deps.patch
fs-err $ quilt edit Cargo.toml
```

`relax-deps` is just a convention.

Then find the relevant section:

```toml
[dependencies.tokio]
version = "1.21"
features = ["fs"]
optional = true
default_features = false
```

That's… a dependency. Yeah. In Rust, features can depend on dependencies.
Anyway, let's patch it out.

When it comes to patching something out, some people simply deletes relevant
lines, but some prefer commenting out, so users know what's disabled and have
the option to enable it. There's no conclusion on that and you can go either
way.

After that, refresh the patch:

```
fs-err $ quilt refresh
Refreshed patch relax-deps.patch
```

Then rebuild it:

```
fs-err $ cd ../..
debcargo-conf $ ./update.sh fs-err
debcargo-conf $ cd build && ./build.sh fs-err
(build logs)
+------------------------------------------------------------------------------+
| Summary                                                                      |
+------------------------------------------------------------------------------+

Autopkgtest: pass
(skipped for brevity)
```

It passed. Yay! Let's get to the next, `lzzzz`.

```
debcargo-conf $ ./update.sh lzzzz
    Updating crates.io index
Suspicious file, should probably be excluded: "lzzzz-1.0.4/vendor/liblz4/lz4.c"
Suspicious file, should probably be excluded: "lzzzz-1.0.4/vendor/liblz4/lz4file.c"
Suspicious file, should probably be excluded: "lzzzz-1.0.4/vendor/liblz4/lz4frame.c"
Suspicious file, should probably be excluded: "lzzzz-1.0.4/vendor/liblz4/lz4hc.c"
Suspicious file, should probably be excluded: "lzzzz-1.0.4/vendor/liblz4/xxhash.c"
debcargo failed: Suspicious files detected, aborting. Ask on #debian-rust if you are stuck.
```

Uh-oh. It failed too, but a new kind. It sas "Suspicious file" and looking at
the path, it's some vendored C source.

Because there's no single package system to rule them all, upstream who write
and/or use C code often "vendor" their C dependencies, which is a fancy way of
saying carrying a copy of them along its own code, so what we have here is
`lzzzz` carrying its copy of `liblz4`.

However on Debian, C libraries are more often than not already packaged, and we
usually don't allow vendoring unless it's really needed. So in this case, we'll
use the Debian packaged `liblz4`.

```
$ apt search liblz4
Sorting... Done
Full Text Search... Done
liblz4-1/unstable,now 1.9.4-1 amd64 [installed]
  Fast LZ compression algorithm library - runtime

liblz4-dev/unstable 1.9.4-1 amd64
  Fast LZ compression algorithm library - development files
```

So what we need here is `liblz4-dev`. Let's add it, while also excluding the
"suspicious" vendored source:

```toml
# in debcargo.toml
excludes = ["vendor/*"]

[packages.lib]
depends = ["liblz4-dev"]
```

There's no `lzzzz-1.0.4/` in `excludes`, because `excludes` is based on the
source directory, which, in this case, _is_ `lzzzz-1.0.4/`. Well.

Let's try again:

```
debcargo-conf $ ./update.sh lzzzz
    Updating crates.io index
crate tarball was modified; repacking for debian
(skipped for brevity)
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4.c"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4.h"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4file.c"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4file.h"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4frame.c"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4frame.h"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4frame_static.h"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4hc.c"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/lz4hc.h"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/xxhash.c"
Filtered out files from .orig.tar.gz: "lzzzz-1.0.4/vendor/liblz4/xxhash.h"
Wrote back file to overlay: copyright.debcargo.hint
Wrote back file to overlay: changelog
Package Source: build/lzzzz
Original Tarball for package: build/rust-lzzzz_1.0.4.orig.tar.gz
```

That's better. The line `crate tarball was modified; repacking for debian`
means its origin source tarball is modified (in this case, excluding some
files). This is common on Debian where we hold the
[DFSG](https://www.debian.org/social_contract#guidelines) very seriously, so
even the slightest non-free elements need to be kept out. You may sometimes see
versions like `1.67.1+dfsg1-1`, where `dfsg` is jsut that.

Then build it:

```
debcargo-conf $ cd build && ./build.sh lzzzz
(build log)
running: "cc" "-O0" "-ffunction-sections" "-fdata-sections" "-fPIC" "-g" "-fno-omit-frame-pointer" "-m64" "-g" "-O2" "-ffile-prefix-map=/<<PKGBUILDDIR>>=." "-fstack-protector-strong" "-Wformat" "-Werror=format-security" "-o" "/<<PKGBUILDDIR>>/target/x86_64-unknown-linux-gnu/debug/build/lzzzz-bcbea88d54fff91b/out/vendor/liblz4/lz4hc.o" "-c" "vendor/liblz4/lz4hc.c"
(skipped for brevity)
  cargo:warning=cargo:warning=cc1: fatal error: vendor/liblz4/lz4hc.c: No such file or directorycc1: fatal error: vendor/liblz4/lz4.c: No such file or directory
  cargo:warning=compilation terminated.
(skipped for brevity)
  exit status: 1

  --- stderr
  Error: Error { kind: ToolExecError, message: "Command \"cc\" \"-O0\" \"-ffunction-sections\" \"-fdata-sections\" \"-fPIC\" \"-g\" \"-fno-omit-frame-pointer\" \"-m64\" \"-g\" \"-O2\" \"-ffile-prefix-map=/<<PKGBUILDDIR>>=.\" \"-fstack-protector-strong\" \"-Wformat\" \"-Werror=format-security\" \"-o\" \"/<<PKGBUILDDIR>>/target/x86_64-unknown-linux-gnu/debug/build/lzzzz-bcbea88d54fff91b/out/vendor/liblz4/lz4.o\" \"-c\" \"vendor/liblz4/lz4.c\" with args \"cc\" did not execute successfully (status code exit status: 1)." }
dh_auto_test: error: /usr/share/cargo/bin/cargo build returned exit code 101
make: *** [debian/rules:3: binary] Error 25
dpkg-buildpackage: error: debian/rules binary subprocess returned exit status 2
```

Your shell most likely don't provide enough scrollback buffer to cache the
entire log, so read `build/rust-{crate}_{version}_{arch}.build` for the full
log, or `build/rust-{crate_{version}_{arch}.test.log` for only the tests.

If you used the `build-failed-commands` snippet, now it will open a shell for
inspection. But this time just Ctrl-D to exit.

Vendoring in Rust requires a special `build.rs` to work, which prepares things
before building the crate itself, and for vendoring, builds and/or prepares the
C libraries it uses. `lzzzz` uses `liblz4`, so it most certainly uses a
`build.rs`. Let's have a look:

```rust
lzzzz $ cat build.rs
fn main() -> Result<(), cc::Error> {
    let sources = &["lz4.c", "lz4hc.c", "lz4frame.c", "xxhash.c"][..];
    let dir = std::path::Path::new("vendor/liblz4");
    cc::Build::new()
        .files(sources.iter().map(|file| dir.join(file)))
        .try_compile("lz4")
}
```

This is a rather simple `build.rs` which just lists C source files and call
`cc` to build them. Because Rust has great interoperability with C, it can load
and link shared libraries just like C programs do. Thus all we need to do is
provide `liblz4-dev`. Larger crates may involve `pkg-config` and complex logic.
For now, just `quilt new` a patch and comment out the code inside `fn main()`:

```rust
fn main() {}/*-> Result<(), cc::Error> {
    let sources = &["lz4.c", "lz4hc.c", "lz4frame.c", "xxhash.c"][..];
    let dir = std::path::Path::new("vendor/liblz4");
    cc::Build::new()
        .files(sources.iter().map(|file| dir.join(file)))
        .try_compile("lz4")
}*/
```

Then regenerate and build:

```
debcargo-conf $ ./update.sh lzzzz
debcargo-conf $ cd build && ./build.sh lzzzz
(build log)
autopkgtest: WARNING: package librust-lzzzz-dev is not installed though it should be
autopkgtest: WARNING: Test dependencies are unsatisfiable - calling apt install on test deps directly for further data about failing dependencies in test logs
librust-lzzzz-dev:   SKIP installation fails and skip-not-installable set
autopkgtest [17:00:08]: @@@@@@@@@@@@@@@@@@@@ summary
rust-lzzzz:@         SKIP installation fails and skip-not-installable set
librust-lzzzz-dev:default SKIP installation fails and skip-not-installable set
librust-lzzzz-dev:   SKIP installation fails and skip-not-installable set

(skipped for brevity)
Autopkgtest: no tests
(skipped for brevity)

You should: Package the missing dev-dependencies.
Explanation: autopkgtest cannot install all dependencies.  Check the dev-dependencies section in the Cargo.toml or the Testsuite-Triggers field in the dsc file to see a list of additional autopkgtest dependencies, or inspect the full log to find the missing packages.
```

This time it builds, but `SKIP`ed `autopkgtest` tests. Scroll back, and you'll
find:

```
Correcting dependencies...Starting pkgProblemResolver with broken count: 1
Starting 2 pkgProblemResolver with broken count: 1
Investigating (0) autopkgtest-satdep:amd64 < 0 @iU K Nb Ib >
Broken autopkgtest-satdep:amd64 Depends on librust-assert-fs-1+default-dev:amd64 < none @un H > (>= 1.0.6-~~)
  Removing autopkgtest-satdep:amd64 because I can't find librust-assert-fs-1+default-dev:amd64
Done
 Done
```

`assert-fs` is needed for testing but it's not there. This happens, just keep
calm and package it. Then it comes to…

## Let the dependent depend

So you packaged the dependencies, now it's time to let the dependent use them.
How? It's actually quite simple:

```
build $ ./build.sh ouch *{fs-err,lzzzz,ubyte,OTHER,DEPENDENCIES}*amd64.deb
# or
build $ EXTRA_DEBS=*{fs-err,lzzzz,ubyte,OTHER}*amd64.deb ./build.sh ouch
```

Behind the scene, `build.sh` passes them as `--extra-package` arguments to
`sbuild`, who takes them into the build enviroment and installs them just like
those in the archive.

This forms a nice little dependency tree, just like the crates themselves.
Bottom up, until the final and the one you wanted at first.

## Paperworks for binaries

Most people package a Rust crate because it provides a program they want to
use. That's sometimes called a binary, and for those binaries, there are some
more paperworks to do.

First, traditionally, a program should have a man page, short for manual page,
which describes what it does and how to use it. Debian has a mechanism for
installing one, conveniently called `d/{package}.manpages`, which is really
just a text file that lists paths to man pages in the build directory.

However, time has changed. Many modern programs still provide a `--help`
argument to show help message, but no man pages. We can use `help2man` to
convert that to a more or less readable man page. But luckily, `ouch` builds
that for us. Just not how you think it would…

```rust
debcargo-conf $ cat build/ouch/build.rs
/// This build script checks for env vars to build ouch with shell completions and man pages.
///
/// # How to generate shell completions and man pages:
///
/// Set `OUCH_ARTIFACTS_FOLDER` to the name of the destination folder:
///
/// ```sh
/// OUCH_ARTIFACTS_FOLDER=my-folder cargo build
/// ```
///
/// All completion files will be generated inside of the folder "my-folder".
///
/// If the folder does not exist, it will be created.
///
/// We recommend you naming this folder "artifacts" for the sake of consistency.
///
/// ```sh
/// OUCH_ARTIFACTS_FOLDER=artifacts cargo build
/// ```

/////// (skipped for brevity)
    if let Some(dir) = env::var_os("OUCH_ARTIFACTS_FOLDER") {
        let out = &Path::new(&dir);
        create_dir_all(out).unwrap();
        let cmd = &mut Opts::command();

        Man::new(cmd.clone())
            .render(&mut File::create(out.join("ouch.1")).unwrap())
            .unwrap();

        for subcmd in cmd.get_subcommands() {
            let name = format!("ouch-{}", subcmd.get_name());
            Man::new(subcmd.clone().name(&name))
                .render(&mut File::create(out.join(format!("{name}.1"))).unwrap())
                .unwrap();
        }
```

So we need to provide an `OUCH_ARTIFACTS_FOLDER` env var, preferably
`artifacts`. We could patch it, but we have a better way: `d/rules`. It's
actually a `Makefile`, with some Debian exclusive goodies. Let's write it:

```make
debcargo-conf $ cat src/ouch/debian/rules
#!/usr/bin/make -f
%:
    dh $@ --buildsystem cargo

override_dh_auto_build:
    # see its build.rs
    env OUCH_ARTIFACTS_FOLDER=artifacts dh_auto_build
```

`override_dh_auto_build` means to `override` the `auto_build` stage of `dh`,
which is the executable of
[debhelper](https://packages.debian.org/unstable/debhelper). Then we use `env`
to still run `dh_auto_build` but with the needed env var.

Then write the `d/.manpages`:

```
debcargo-conf $ cat src/ouch/debian/ouch.manpages
artifacts/*.1
```

Simple as that.

The `build.rs` also talked about shell completions, which are nice, so we'll
have them too. But there's no special mechanism for that; instead, we use
`d/{package}.install`, which is a general mechanism to install anything that
should be installed.

```
debcargo-conf $ cat src/ouch/debian/ouch.install
artifacts/ouch.bash /usr/share/bash-completion/completions/
artifacts/ouch.fish /usr/share/fish/completions/
artifacts/_ouch /usr/share/zsh/vendor-completions/
```

One for each of the most popular shells.

## Upload, update, repeat

Now you have the crate packaged in a nice `.deb`, it's time to upload it. If you
are a DD, you are most likely more capable than me, so reading `release.sh` and
using it should be fairly easy. If not:

Write a `RFS` file in `src/{crate}/debian`. It stands for "Request For Sponsor",
which is what a non-DD maintainer does when looking for a sponsor to upload
their package. This is only how Rust team does it; other teams have their own
ways. If there's no particular team for a package, https://mentors.debian.net is
worth a try.

`git add src/{crate}` and `git commit`. There's no policy on commit messages,
but being descriptive and concise is always a good thing.

`git push` if you are a member of `rust-team` on salsa.d.o, or create a merge
request if not. Ask in #debian-rust for sponsor.

Check your package regularly for new versions, and update them when there are. 
You took the responsibility of packaging it, so keep carrying it. No one will
blame you for giving up one package due to work or other factors, but if you do
that too much, some people will start to dislike you. Just don't do it if you
don't have the time.

To update a crate, run `./update.sh {crate}` then `cd build && ./build.sh
{crate}`. In simple cases that's enough. In not so simple cases, you may need to
relax dependencies, fix bugs, or change things to fit them in Debian.

When there are dependencies, there are reverse dependencies. Run
`list/list-rdeps.sh {crate}` for a list of (packages of) crates that depend on
`{crate}`. Sometimes updating a crate means updating their rdeps. Coordinate
with others. Take it slow and steady.

## ITP, RFS, RFP, and other TLAs

In Debian, when you are not a DD (Debian Developer) but want to upload a
package, you need to RFS (Request For Sponsor). And when you want to package a
new program or library (DD or not), you file an ITP (Intent To Package).

I don't know why people love those TLAs (Three Letter Acronyms) so much, but it
is what it is. You can check other TLAs and TwoLAs (Two Letter Acronyms) used
across Debian at https://wiki.debian.org/Glossary.

### WNPP

First, let's get to know WNPP, or "Work-Needed and Prospective Packages", a kind
of info board to let people know which packages need work, help, or one intends
to package. It's implemented as a pseudo package on bugs.debian.org (or, as we
often call it, bugs.d.o), Debian's bug tracking system. There are quite a few
other pseudo packages for the same or similar purpose.

People have developed various tools for that:

- bugs.d.o itself is an email interface for submitting and replying to bugs, so
  one can file an ITP by submitting to it just like filing a bug. Use
  `reportbug` to generate a template, it knows WNPP.
- https://wnpp.debian.net is a web interface to view and search WNPP entries.
- `wnpp-check` in `devscripts` package is a CLI to search for WNPP entries.

### ITP

Now, ITP. Usually there's one ITP for each package, but due to the sheer number
of library crates, we at Rust team don't file ITPs for them, only binary crates.
In this guide, we are only filing for `ouch`.

First, check if others have filed. Here I'm using `wnpp-check` because it's
easier to demonstrate:

```
$ wnpp-check ouch
(RFP - #1001167) https://bugs.debian.org/1001167 couchdb
(RFP - #691903) https://bugs.debian.org/691903 libcouchbase
(ITP - #968662) https://bugs.debian.org/968662 libinput-touch-translator
(ITP - #1032176) https://bugs.debian.org/1032176 ouch
(RFP - #831635) https://bugs.debian.org/831635 touchandgo
```

Ouch, it's already filed (pun intended). By me. Sorry. That means I'm somewhat
the "owner" of this packaging effort, and most people don't like someone else
"stealing" it. But you likely have something different in mind. Assume it's
`bottom` (which, by the way, does have no ITP at the time of writing). Check
again:

```
$ wnpp-check bottom
$
```

No one has filed. Let's file for it:

```
$ reportbug -p
Please enter the name of the package in which you have found a problem, or type 'other' to report a more general problem. If
you don't know what package the bug is in, please contact debian-user@lists.debian.org for assistance.
> wnpp
Are you sure you want to file a WNPP report [y|N|q|?]? y
(skipped)
What sort of request is this? (If none of these things mean anything to you, or you are trying to report a bug in an existing
package, please press Enter to exit reportbug.)

1 ITP  This is an `Intent To Package'. Please submit a package description along with copyright and URL in such a report.
(skipped)
Choose the request type: 1
Please enter the proposed package name: bottom
Checking package information...
Please briefly describe this package; this should be an appropriate short description for the eventual package:
> A TUI to monitor processes and system resources
Your report will be carbon-copied to debian-devel, per Debian policy.
Querying Debian BTS for reports on wnpp...
6978 bug reports found:
(skipped)
(1-64/6978) Is the bug you found listed above [y|N|b|m|r|q|s|f|e|?]? s (for skip)

Enter any additional addresses this report should be sent to; press ENTER after each address. Press ENTER on a blank line to
continue.
>

Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
From: Blair Noctis <n@sail.ng>
To: Debian Bug Tracking System <submit@bugs.debian.org>
Subject: ITP: bottom -- A TUI to monitor processes and system resources

Package: wnpp
Severity: wishlist
Owner: Blair Noctis <n@sail.ng>
X-Debbugs-Cc: debian-devel@lists.debian.org, n@sail.ng

* Package name    : bottom
  Version         : x.y.z
  Upstream Contact: Name <somebody@example.org>
* URL             : https://www.example.org/
* License         : (GPL, LGPL, BSD, MIT/X, etc.)
  Programming Lang: (C, C++, C#, Perl, Python, etc.)
  Description     : A TUI to monitor processes and system resources

(Include the long description here.)

Please also include as much relevant information as possible.
For example, consider answering the following questions:
 - why is this package useful/relevant? is it a dependency for
   another package? do you use it? if there are other packages
   providing similar functionality, how does it compare?
 - how do you plan to maintain it? inside a packaging team
   (check list at https://wiki.debian.org/Teams)? are you
   looking for co-maintainers? do you need a sponsor?
Thank you for using reportbug
```

That's a bit long, but rather clear. `-p` means to print the email, not send
it, because I prefer writing, signing and sending it in an email client. Copy
the email starting with `Package: wnpp` into the body, put the `Subject` in the
subject line and `submit@bugs.debian.org` in `To`, fill out the placeholders,
then send it. A few minutes later a confirmation email will come from bugs.d.o.

Start packaging. Add `Closes: #{bug number}` to its `d/changelog`, so when the
package is uploaded, the ITP bug is marked as done by an automated email from
FTP masters.

But it may be too difficult, and you want to hand it off. Then you can change
it to a RFP (Request For Packaging) by sending bugs.d.o
[commands](https://www.debian.org/Bugs/server-control) to
`{number}@bugs.debian.org`:

```
retitle -1 RFP - {summary}
thanks
```

This will `retitle` it to be a RFP. `-1` means the bug this email is
addressing.

If you later have the time again, just `retitle` it to be an ITP and continue
the work.
