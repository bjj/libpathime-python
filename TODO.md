# TODO

Upcoming work only; prune as things complete.

## Next

- [ ] Release v0.1.2 in lockstep with libpathime (its RELEASING.md has the
      order). Before tagging: bump `pyproject.toml` to 0.1.2 and the
      submodule to libpathime's v0.1.2 tag. One-time setup first, in repo
      settings and on pypi.org: create the `pypi` GitHub Environment with a
      required reviewer, and register this repo's release workflow +
      environment as the project's Trusted Publisher on PyPI (the `pathime`
      name is still unclaimed — sooner is better).

## Later

- [ ] Platform wheels that bundle the library stay deferred until someone
      needs `pip install pathime` to work with no separate download.
- [ ] add a screenshot of the demo
- [ ] The demo's table engine is hardcoded to cangjie5; a table picker from
      `option_value_name` would exercise the enumerable-string surface.
