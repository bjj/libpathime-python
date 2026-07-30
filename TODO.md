# TODO

Upcoming work only; prune as things complete.

- [ ] Verify the Windows path: build libpathime with MSVC, check
      `pathime.dll` loads through `PATHIME_LIBRARY` + `add_dll_directory`,
      run the test suite. Written to work, never executed.
- [ ] Bopomofo has no test of its own beyond the shared option coverage; add
      a keystroke-to-candidate test (needs a bopomofo keystroke table to
      assert against).
- [ ] Packaging is source-only. If this ever ships, decide how the wheel
      finds libpathime (bundle the library and pathime-data, or keep the
      env-var contract).
- [ ] The demo's table engine is hardcoded to cangjie5; a table picker from
      `option_value_name` would exercise the enumerable-string surface.
