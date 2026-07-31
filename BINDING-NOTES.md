# Binding notes

Pain points and observations from writing the Python (ctypes) binding, to take
back to libpathime. The audience is the libpathime project deciding what, if
anything, to change; each item ends with a suggestion, which may be "nothing".
Items marked **(C# too)** are expected to apply to a future C# (P/Invoke)
binding, which shares the ctypes shape: declare the ABI by hand, marshal at
the boundary, keep callback delegates alive.

For calibration: the whole binding is ~600 lines of Python plus ~250 of ffi
declarations, written and tested against all five engines in a day, with no
change needed to libpathime. The list below is the friction that remains, not
a complaint; the last section is what made it easy and should be preserved.

## Documentation gaps

- **The header never says what `data_dir = NULL` selects.** It carefully
  rules out the empty string "so that a caller who built the path and got
  nothing is told, instead of silently writing to the default" — so a default
  exists — but the default itself is stated nowhere in `pathime.h`.
  `init.cc:94` says *"The header commits to 'a platform-appropriate default
  beneath the user's configuration directory'"* and no such sentence exists in
  the header: it looks like the commitment was edited out of the header while
  the implementation comment still cites it. The binding's `init()` docstring
  had to say "the library default" without being able to say what that is.
  **Suggestion:** restore the sentence to `pathime_init_params_t::data_dir`
  (APPDATA on Windows, XDG config dir elsewhere, per-user, survives cache
  cleaning), and fix the dangling citation in `init.cc`. **(C# too)**

- **Consuming a bare build tree from another language finds no data.** The
  build stages `pathime-data/` beside the library only under
  `LIBPATHIME_BUILD_TESTS` or `LIBPATHIME_BUILD_DEMO`; a binding pointed at a
  plain build gets a library where every engine reports unavailable and
  nothing says why. `cmake --install` is the answer and works. **Suggestion:**
  one line in BUILD.md's "What gets produced": consuming from outside the
  tree means installing first (or enabling the demo to get the staged copy).

- **And an installed tree on Windows does not load.** The install stages the
  vendored backend DLLs beside `pathime.dll` but not pyzy's vcpkg runtime
  (`glib-2.0-0.dll`, `sqlite3.dll`, `iconv-2.dll`, `intl-8.dll`,
  `pcre2-8.dll`) — vcpkg's applocal step populates only the *build* tree's
  `bin/`. `docs/windows-port.md` says so and says to copy them alongside, but
  the symptom lands far from the sentence: `LoadLibrary` reports "Could not
  find module 'pathime.dll' (or one of its dependencies)", naming a file that
  exists and nothing about pyzy, and diagnosing means loading each DLL in the
  tree by hand until one fails. Together with the item above this makes both
  obvious ways of pointing a binding at the library — the build tree and the
  installed tree — incomplete on Windows in a different way each.
  **Suggestion:** make the install complete (vcpkg's
  `X_VCPKG_APPLOCAL_DEPS_INSTALL=ON` exists for exactly this), or failing
  that, put the copy step in BUILD.md's "What gets produced", where a
  deployer actually reads — today it lives only in the port notes.

## Transcription — what a binding must copy by hand, and what checks it

A ctypes/P/Invoke binding re-declares every enum, constant, and struct layout
by hand. Transcription errors are silent — a transposed enum value produces a
working call that does the wrong thing — so what matters is what the library
lets a binding *verify at runtime*. Today that coverage is uneven:

- **Options: excellent.** `pathime_option_count` / `pathime_option_name` /
  `pathime_option_value_name` / `pathime_engine_option_info` let the test
  suite assert `option_name(CHINESE_VARIANT) == "chinese-variant"` — this
  caught real mistakes while writing the binding, and the inventory walk
  means a binding keeps working against a newer library's options it has
  never heard of.

- **Engines: nothing.** There is no `pathime_engine_name()`. A binding that
  transposed `PATHIME_ENGINE_PINYIN` and `PATHIME_ENGINE_BOPOMOFO` would pass
  every structural check and create the wrong engine. The demo also wanted
  the name for its `--engine` flag and its status line, and had to carry its
  own table — exactly the thing `pathime_option_name` exists to avoid.
  **Suggestion:** `pathime_engine_name(pathime_engine_id_t)` returning a
  stable machine-readable key ("hangul", "pinyin", …), "" for a value that is
  not an engine id, static and callable before init, mirroring
  `pathime_option_name`. Cheap, and it completes the pattern. **(C# too)**

- **Status codes, requirement bits, modifier bits, keysyms, fuzzy/correction
  bits: nothing checks them.** `pathime_status_string` exists but its text is
  prose, not a stable key, so a test can only assert it is non-empty. These
  enums are small and ABI-frozen, so the risk is bounded; listing them here
  mainly so the cost is a known one. **Suggestion:** nothing — a
  machine-readable name per status code would be ceremony. The one that
  might earn it is the requirements bits, where a wrong transcription
  silently drops a MISSING_CALLBACK safety net.

- **`pathime_option_t` → value-enum association is manual.** The descriptor
  gives an option's *type* and its legal values, but "ENUM of
  pathime_hangul_layout_t" exists only in prose, so the binding hardcodes a
  {option → Python enum class} map. Unavoidable without codegen; the
  value-name surface at least verifies each entry. **Suggestion:** nothing
  for C. If a generated-bindings future ever arrives, this map is the part
  worth generating.

- **`pathime_option_type()` needs an engine.** An option's type is
  option-static — every engine reports the same type — but the only way to
  read it is `pathime_engine_option_info`, which needs an engine handle. The
  binding's generic typed `get_option()` therefore does an info call per get,
  and could not offer typed access before init. Trivial cost, slight smell.
  **Suggestion:** consider `pathime_option_type(pathime_option_t)` as a
  static pre-init lookup beside `pathime_option_name`; or nothing, since
  info-per-get works.

## Callbacks

- **Exceptions cannot cross the C frame, and the engine-level setters make
  that non-local.** A Python exception in a callback must be caught at the
  trampoline, remembered, and re-raised after the triggering call returns —
  standard binding fare for `process_key`. What is not standard:
  `pathime_engine_set_option_*` dispatches `composition_changed` to every
  inheriting context, so the *engine* wrapper must be able to surface errors
  stashed on contexts it was never passed. The binding ended up with a
  weak-set of contexts per engine purely for this. The header does warn that
  engine setters invoke other contexts' callbacks (it is why they are not
  callback-safe). **Suggestion:** nothing to change — but this is worth a
  sentence in whatever "writing a binding" doc ever exists, because the
  obvious per-call error slot is wrong. **(C# too — same trampoline, same
  non-local dispatch.)**

- **`user_data` is dead weight for closure languages, and that is fine.** The
  header says `pathime_context_engine`/`_user_data` exist for language
  bindings handed a bare handle by their own callback plumbing. Python
  closures and C# delegates capture their wrapper object, so neither needs
  it; both cost nothing. A plain-C-function-pointer binding (or one avoiding
  per-context closure allocation) still wants it. **Suggestion:** nothing.

- **`commit_text` being required forced a design decision the other two
  callbacks did not.** Optional callbacks map naturally to optional handlers
  — the binding installs the `delete_surrounding_text` trampoline only when
  the user supplies one, so `PATHIME_ERROR_MISSING_CALLBACK` still fires and
  still means what it means. `commit_text` may not be NULL, so a binding
  must install *something* even when the user gave nothing; this binding
  buffers committed text on the context (`take_committed()`), which then
  turned out to be the nicest interface for tests anyway. **Suggestion:**
  nothing — but keep "required" rare, because every required callback is a
  binding-side policy decision about what to do on the user's behalf.

## Units and text

- **Scalar-value positions are a perfect fit for Python and a real cost for
  C#.** Python `str` indexes scalar values, so every position in the API is
  directly a string index — `preedit_settled`, surrounding-text cursors, and
  `delete_surrounding_text` offsets all worked with zero conversion, and the
  non-BMP test passed first try. C# strings are UTF-16 code units: every one
  of those positions must be converted in both directions, with surrogate
  pairs the failure case that tests always miss. The choice of scalar values
  is still right — it is the only unit that is *some* language's native one
  and unambiguous in all of them. **Suggestion (C#):** the C# binding should
  convert at the boundary and expose UTF-16 indices, the way this one
  exposes str indices; budget tests with astral-plane text from day one.
  Nothing to change in C.

- **`pathime_str_t` binds cleanly.** By-value two-word struct, explicit
  length, "never required to be NUL-terminated" but always terminated when
  produced by the library — `ctypes.string_at(ptr, len)` and P/Invoke's
  equivalent both consume it without ceremony, and the no-embedded-NUL rule
  means no scanning. **Suggestion:** nothing; keep it.

## Lifetime and misc

- **Borrowed-until-next-mutation is easy to make safe by copying, and the
  header's own guarantees make the copy cheap and complete.** Candidates are
  fully materialized before `composition_changed` dispatches and
  `pathime_context_candidate` is callback-safe, so the binding snapshots the
  entire composition — candidates included — inside the callback, and no
  borrowed pointer ever reaches Python. The "callback-safe" list at the top
  of the header is exactly the contract that makes this legal, and it is the
  single most binding-friendly design decision in the API. **Suggestion:**
  nothing; preserve that list's precision.

- **Destruction ordering is the caller's problem and a GC language feels
  it.** Contexts before engine, engines before shutdown — with Python
  finalizers running in arbitrary order, the binding cannot safely destroy
  from `__del__` and instead offers `close()`/context managers and documents
  the order. A leaked context whose engine died first is a use-after-free
  waiting in `pathime_context_destroy`. **Suggestion:** nothing for C — this
  is what handles cost — but a C# binding should consider SafeHandle with
  the engine handle keeping a reference to prevent premature release.
  **(C# too)**

- **`out_handled` always written, rejections vs failures, statuses as dense
  small ints:** all three made the error path mechanical — one `_check()`
  raising a mapped exception class, with the header's rejection/failure
  split telling the docstrings which errors leave state indeterminate.
  **Suggestion:** nothing; keep appending, never renumbering.

## What worked (keep these)

Recording these so a future API change knows what it would be breaking:

- `struct_size` versioning meant the binding compiled-in nothing about
  library version; the in/out form on `pathime_option_info_t` is subtle but
  the header explains it at the exact point of use.
- The option inventory walk (`option_count` → `option_name` →
  `engine_option_info` → `option_value_name`) meant the binding, its tests,
  and the demo's table picker carry almost no hardcoded knowledge — the
  `cangjie5` list in the demo came from the library at runtime.
- Synchronous, callback-before-return dispatch with documented ordering
  (deletes before commits, `composition_changed` last) meant the binding
  needed no queue, no re-entrancy guard beyond the documented one, and no
  threads. The GIL and "calls never overlap" compose trivially.
- Documented behaviour was *observed* behaviour, every time: hangul word
  mode's `preedit_settled`, the trailing-`n` commit normalization, table key
  legends committing as letters, the digit look-behind, the caps-and-appends
  candidate rule — each became a passing test on the first run. Zero
  divergence between `pathime.h` and the library it describes.
