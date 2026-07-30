# TODO

Upcoming work only; prune as things complete.

## Binding

- [ ] `src/pathime/_ffi.py` — ctypes structs, prototypes, library loading
- [ ] `src/pathime/__init__.py` — public API: init/shutdown, Engine, Context,
      enums, exceptions, option access with introspection
- [ ] Callback trampoline: copy composition eagerly, defer Python exceptions
      until the triggering call returns
- [ ] Windows loading path (`pathime.dll` name, `os.add_dll_directory`) —
      untestable here; keep it simple and documented
- [ ] `pyproject.toml`

## Tests (pytest, against the real library)

- [ ] Lifecycle: version, init/shutdown, has_engine, error mapping
- [ ] Pinyin end-to-end: nihao → candidates → select → commit
- [ ] Hangul: syllable composition, backspace, commit
- [ ] Anthy: kana preedit, space conversion
- [ ] Table: cangjie5 via PATHIME_OPT_TABLE_FILE
- [ ] Options: get/set/reset, info, inventory walk, unsupported → error
- [ ] Binding-specific: snapshot independence, callback exception deferral,
      non-BMP text in surrounding text (scalar-value positions)

## Demo

- [ ] `demo/phone_keyboard.py` — terminal phone-keyboard simulation:
      text area, candidate strip, on-screen key layout, engine switching

## Documentation

- [ ] `BINDING-NOTES.md` — grow as pain points appear; final pass at the end
- [ ] `README.md` — how to build libpathime, point the binding at it, run
      tests and demo
