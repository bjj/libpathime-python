# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project Overview

`libpathime-python` is a Python binding for `libpathime/` (a git submodule —
**read-only in this repository**; anything it needs changed is taken back to
that project). libpathime is a CJK input
method engine as a plain C library: five engines (Hangul, Anthy, Pinyin,
Bopomofo, Table), a synchronous callback-based client interface, and a
phone-keyboard composition model. Its public surface is one header,
`libpathime/include/pathime/pathime.h`, documented in full; concepts are in
`libpathime/docs/CONCEPTS.md`.

## The shape of the problem

The binding is **ctypes**, not an extension module, so one pure-Python package
serves Linux and Windows alike; nothing is compiled here except libpathime
itself. The package is `src/pathime/`:

- `_ffi.py` — the ctypes layer: struct layouts, function prototypes, library
  loading. A transcription of `pathime.h`, kept in its order.
- `__init__.py` — the public API: `init()`/`shutdown()`, `Engine`, `Context`,
  enums mirroring the C ones, exceptions mirroring `pathime_status_t`.

What the C API's shape means for a binding, in brief:

- **Callbacks, synchronously.** Everything the engine produces arrives through
  a `pathime_client_t` callback table before the triggering call returns. The
  binding keeps the ctypes callback wrappers alive for the context's lifetime
  (they are referenced from C) and turns them into overridable methods /
  constructor arguments on `Context`.
- **Borrowed memory everywhere.** Strings and structs the library returns are
  valid only until the next mutating call. The binding copies eagerly into
  Python `str` at the boundary, so no Python object ever holds a borrowed
  pointer.
- **Two units.** Positions and counts are in Unicode scalar values; only
  `pathime_str_t.len` is bytes. Python `str` indices are scalar values, so the
  binding converts at the boundary and the Python API speaks `str` indices
  only.
- **No overlapping calls.** The library is synchronous and unlocked; the
  binding documents this and does not add locking (the GIL makes accidental
  overlap unlikely but a client using threads must serialize itself).
- **Struct versioning by `struct_size`**, error returns by `pathime_status_t`:
  handled once in `_ffi.py` (`_check()` raises the mapped exception).

## Layout

```
CLAUDE.md            # This file
TODO.md              # Upcoming work only — start here for "what's next"
libpathime/          # Submodule — the C library. DO NOT MODIFY here.
src/pathime/         # The binding package
tests/               # pytest suite driving the real library
demo/                # Phone-keyboard demo (terminal)
```

## Building and testing

Build libpathime as a shared library first (out of tree — this sandbox sits on
a Windows filesystem, so build in `/tmp`):

```bash
cmake -S libpathime -B /tmp/pathime-build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/pathime-build
```

The binding finds the library via `PATHIME_LIBRARY` (path to the `.so`/`.dll`)
or the system loader. The staged build layout keeps `pathime-data/` beside the
library, which is where `pathime_init()` looks by default.

```bash
PATHIME_LIBRARY=/tmp/pathime-build/lib/libpathime.so python -m pytest tests/
```

## Conventions

- Follow libpathime's documentation habits: present tense, state what is true
  and why, keep commit messages short (subject line and a few sentences).
- `TODO.md` holds upcoming work only; prune as things complete.
- Pain points with the C API from a binding author's perspective are taken
  upstream as they are discovered, not reconstructed later. The first round
  (BINDING-NOTES.md, now deleted) landed there; its rulings are in
  libpathime's `docs/design-history.md` §12.
