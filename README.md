# pathime — Python binding for libpathime

A ctypes binding for [libpathime](libpathime/README.md), the CJK input method
engine library: Korean Hangul, Japanese kana–kanji conversion, Chinese Pinyin
and Bopomofo, and table-driven methods (Cangjie, Wubi, …), behind one
synchronous phone-keyboard-shaped API.

Pure Python — nothing here compiles. The same package serves Linux and
Windows; only libpathime itself is built per platform.

## Build libpathime, point the binding at it

```bash
git submodule update --init --recursive
cmake -S libpathime -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
cmake --install build --prefix "$PWD/dist"
export PATHIME_LIBRARY="$PWD/dist/lib/libpathime.so"
```

The install step matters: it lays `pathime-data/` beside the library, which is
where the engines find their dictionaries by default. On Windows, build per
`libpathime/BUILD.md` and point `PATHIME_LIBRARY` at `pathime.dll`; the
binding adds that DLL's directory to the search path so the vendored backend
DLLs beside it resolve.

For detailed building instructions see [`libpathime/BUILD.md`](libpathime/BUILD.md).

## Use

```python
import pathime

pathime.init()  # or init(data_dir=...) to say where engines keep learning

with pathime.Engine(pathime.EngineId.PINYIN) as engine:
    with pathime.Context(engine) as ctx:
        ctx.type("nihao")
        print(ctx.composition.preedit)      # "ni hao"
        print(ctx.composition.candidates[0])  # "你好"
        ctx.select_candidate(0)
        print(ctx.take_committed())         # "你好"

pathime.shutdown()
```

Callbacks, options, requirements and the rest mirror `pathime.h`; start from
the package docstring (`python -c "import pathime; help(pathime)"` with
`PYTHONPATH=src`).

## Tests

```bash
PATHIME_LIBRARY=... python -m pytest
```

The suite drives the real library through every engine. It deliberately does
not repeat libpathime's own coverage: it tests the binding's contract — copied
snapshots, typed options, deferred callback exceptions, scalar-value
positions — plus one end-to-end path per engine.

## Demo

```bash
PATHIME_LIBRARY=... python3 demo/phone_keyboard.py --engine pinyin
```

A phone-like keyboard in the terminal: text field, candidate strip, on-screen
keys. Digits tap the strip, arrows slide and page it, Ctrl+E cycles engines,
Ctrl+T/Ctrl+R commit/discard, Ctrl+C quits.

