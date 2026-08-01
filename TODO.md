# TODO

Upcoming work only; prune as things complete.

## Next session: GitHub, CI, releases

- [ ] Give ourselves a version tag (after CI is green). Pushing `v0.1.0`
      triggers `release.yml`, which drafts a GitHub release with the sdist and
      pure wheel; publish by hand after a look at the assets.
- [ ] Turn on CI: `.github/workflows/ci.yml` is drafted but has never run —
      budget a debugging round. Linux builds with Ninja and tests against the
      install tree; Windows uses the `windows-msvc` preset with vcpkg's
      binary-archive cache. The first Windows run builds glib from source
      (slow); later runs restore from the cache. If the serial MSVC build is
      too slow even cached, switch to the `windows-ninja` preset plus a
      dev-prompt action (e.g. `ilammy/msvc-dev-cmd`).
- [ ] Platform wheels that bundle the library stay deferred until someone
      needs `pip install pathime` to work with no separate download.
      (`release.yml` ships sdist + pure wheel only; the per-OS install trees
      proposed earlier already exist as libpathime's own release assets, so
      the notes point there instead of rebuilding them here.)
- [ ] add a screenshot of the demo

## Later

- [ ] The demo's table engine is hardcoded to cangjie5; a table picker from
      `option_value_name` would exercise the enumerable-string surface.
