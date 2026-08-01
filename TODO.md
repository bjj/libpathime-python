# TODO

Upcoming work only; prune as things complete.

## Next session: GitHub, CI, releases

- [ ] Push `libpathime` to `github.com/bjj/libpathime` first — its vendored
      forks (pyzy, anthy-unicode, ibus-table-chinese) are already on GitHub,
      so it is the only missing link in the submodule chain. Then push this
      repo to `github.com/bjj/libpathime-python`. `.gitmodules` uses a
      relative URL (`../libpathime.git`), which resolves against whichever
      remote a clone came from, so orion and GitHub clones both work without
      edits.
- [ ] Turn on CI: `.github/workflows/ci.yml` is drafted but has never run —
      budget a debugging round. Linux builds with Ninja and tests against the
      install tree; Windows uses the `windows-msvc` preset with vcpkg's
      binary-archive cache. The first Windows run builds glib from source
      (slow); later runs restore from the cache. If the serial MSVC build is
      too slow even cached, switch to the `windows-ninja` preset plus a
      dev-prompt action (e.g. `ilammy/msvc-dev-cmd`).
- [ ] Release packages. Proposed shape, keeping the env-var contract: a tag
      builds (a) sdist + pure wheel of the binding and (b) per-OS zips of the
      libpathime `cmake --install` tree — library, `pathime-data/`, and
      THIRD-PARTY.md for the license rollup — attached to a GitHub release.
      Platform wheels that bundle the library stay deferred until someone
      needs `pip install pathime` to work with no separate download.
- [ ] sdist contents: setuptools does not include `tests/` or `demo/` by
      default; decide whether they belong in the sdist when wiring the
      release job.

## Later

- [ ] The demo's table engine is hardcoded to cangjie5; a table picker from
      `option_value_name` would exercise the enumerable-string surface.
