# TODO

Upcoming work only; prune as things complete.

## Next

From the 2026-08-02 three-repo review (verified against this tree; the C
library's and C# binding's shares are in their own TODO.md files), in
priority order:

- [ ] Test the wheel users install, not the checkout. `tests/conftest.py`
      pins `src/` onto `sys.path`, so CI never imports the built package, and
      the release workflow builds the sdist and wheel without checking,
      installing, or testing either. Add a packaging job to CI and release:
      `python -m build`, `twine check dist/*`, install the wheel into a clean
      venv, run the tests from there against a built libpathime; build a
      wheel from the sdist too, which is what catches MANIFEST gaps. The
      release checkout needs `submodules: recursive` before it can run any
      of this.
- [ ] Verify the release names a native library that exists. The tag is
      checked against `pyproject.toml`, but nothing checks that the
      libpathime submodule pin matches the libpathime release the notes link
      to (the URL just assumes the same tag name). Fail the release if the
      pin's tag and the linked release disagree.
- [ ] Publish to PyPI via Trusted Publishing (decided 2026-08-02). The wheel
      is pure `py3-none-any` — exactly what PyPI is for — and the `pathime`
      name is currently unclaimed by anyone. OIDC publish job, gated behind
      the same draft-review step as the GitHub release; rides on the
      wheel-testing item above, since PyPI deletions are as restricted as
      NuGet's. While touching `pyproject.toml`: per-version
      `Programming Language :: Python :: 3.x` classifiers and Issues URL.
- [ ] Reject an unsupported native library at load. `load_library()` never
      calls `pathime_version()`; an older library surfaces as a raw
      `AttributeError` from `_declare`, a newer-but-incompatible one loads
      silently. Pre-1.0 the C library's compatibility promise is per-minor
      (its SONAME is moving to track that), so validate major.minor at load
      and raise something that names both versions.

## Later

- [ ] Test the declared floor: CI runs only 3.12 while `pyproject.toml` says
      `>=3.9`. Linux at {3.9, current}, Windows at current, the packaging job
      at 3.9 (metadata failures show up at the floor). Doubles as the signal
      for when dropping 3.9 is safe.
- [ ] Workflow hygiene, to the core repo's standard: SHA-pin `setup-python`
      and the release workflow's `checkout` (currently `@v4`, an older major
      than CI's); `permissions: contents: read` at the top of CI;
      `dependabot.yml` with `github-actions` + `gitsubmodule` (the latter
      turns the submodule bump into an arriving PR); attest release
      artifacts with `actions/attest-build-provenance` like the core repo
      does; `SECURITY.md`.
- [ ] Update the "Install from a release" section of README.md when
      libpathime's binary archives gain their top-level directory (queued in
      the core repo's TODO) — the `mkdir` workaround and the "no top-level
      directory" warning come out then.
- [ ] Platform wheels that bundle the library stay deferred until someone
      needs `pip install pathime` to work with no separate download.
- [ ] add a screenshot of the demo
- [ ] The demo's table engine is hardcoded to cangjie5; a table picker from
      `option_value_name` would exercise the enumerable-string surface.
