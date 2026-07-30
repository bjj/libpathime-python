# Binding notes

Pain points and observations from writing the Python (ctypes) binding, to take
back to libpathime. Written as discovered; the audience is the libpathime
project deciding what, if anything, to change. Items marked **(C# too)** are
expected to apply to a future C# (P/Invoke) binding, which shares the ctypes
shape: declare the ABI by hand, marshal at the boundary, keep callback
delegates alive.

## Build and layout

- The build tree stages `pathime-data/` beside the library only when
  `LIBPATHIME_BUILD_TESTS` or `LIBPATHIME_BUILD_DEMO` is on. An out-of-tree
  binding pointed at a bare build tree gets a library with every engine
  unavailable and no hint why. `cmake --install` is the documented answer and
  works; a one-line mention in BUILD.md ("consuming the build tree from
  another language: install first, or enable the demo") would have saved a
  detour into LibpathimeRuntimeData.cmake.
