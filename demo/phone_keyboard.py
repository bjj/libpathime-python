#!/usr/bin/env python3
"""A phone-like keyboard in a terminal, driven by the pathime binding.

The screen is what a phone shows: a text field, a candidate strip, and an
on-screen keyboard. Your physical keys stand in for taps:

- letters, space, enter, backspace — taps on the keyboard, offered to the
  engine first; whatever it declines falls through to the document
- 1-9        — tap a candidate on the visible strip
- left/right — slide the highlight along the strip
- up/down    — page the strip (down raises max-candidates past the end,
               which is how a phone keyboard's expanding panel works)
- Ctrl+E     — next engine   Ctrl+T — commit   Ctrl+R — discard   Ctrl+C — quit

Run it pointing at a built libpathime:

    PATHIME_LIBRARY=/tmp/pathime-install/lib/libpathime.so \
        python3 demo/phone_keyboard.py [--engine pinyin] [--data-dir DIR]

The model below (PhoneKeyboard) is UI-free — the curses part only draws it —
so the test suite can type into it headlessly.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pathime
from pathime import EngineId, Key, Mod, Option

STRIP_SIZE = 9  # candidates visible at once: what digits 1-9 can tap

ENGINE_LABELS = {
    EngineId.HANGUL: "한국어",
    EngineId.ANTHY: "日本語",
    EngineId.PINYIN: "拼音",
    EngineId.BOPOMOFO: "注音",
    EngineId.TABLE: "倉頡",
}


class PhoneKeyboard:
    """The phone: a document, an input context, and a candidate strip.

    One instance owns one context per engine (a phone keeps every language's
    keyboard warm); ``switch_engine`` moves between them without disturbing
    the composition each one holds.
    """

    def __init__(self, engine_ids: list[EngineId]):
        self.document: list[str] = []  # one scalar value per entry
        self.cursor = 0
        self.page = 0
        self.engines: dict[EngineId, pathime.Engine] = {}
        self.contexts: dict[EngineId, pathime.Context] = {}
        for engine_id in engine_ids:
            engine = pathime.Engine(engine_id)
            if engine_id == EngineId.TABLE:
                engine.set_option(Option.TABLE_FILE, "cangjie5")
            self.engines[engine_id] = engine
            self.contexts[engine_id] = pathime.Context(
                engine,
                on_commit=self._insert,
                on_delete_surrounding=self._delete,
                on_composition_changed=lambda comp: self._follow_cursor(),
            )
        self.active = engine_ids[0]
        self._refresh_surrounding()

    # ---- the client side of the pathime contract ----

    def _insert(self, text: str) -> None:
        for ch in text:
            self.document.insert(self.cursor, ch)
            self.cursor += 1

    def _delete(self, offset: int, count: int) -> None:
        start = self.cursor + offset
        del self.document[start:start + count]
        self.cursor = start

    def _refresh_surrounding(self) -> None:
        self.context.set_surrounding_text("".join(self.document), self.cursor)

    def _follow_cursor(self) -> None:
        comp = self.context.composition
        if comp.candidate_cursor < self.page * STRIP_SIZE or \
                comp.candidate_cursor >= (self.page + 1) * STRIP_SIZE:
            self.page = comp.candidate_cursor // STRIP_SIZE

    # ---- what the UI reads ----

    @property
    def context(self) -> pathime.Context:
        return self.contexts[self.active]

    @property
    def composition(self) -> pathime.Composition:
        return self.context.composition

    @property
    def text(self) -> str:
        return "".join(self.document)

    def strip(self) -> tuple[list[str], int]:
        """The visible candidate page and the highlight's position in it
        (-1 when the highlight is on another page)."""
        comp = self.composition
        start = self.page * STRIP_SIZE
        visible = list(comp.candidates[start:start + STRIP_SIZE])
        highlight = comp.candidate_cursor - start
        return visible, (highlight if 0 <= highlight < len(visible) else -1)

    # ---- what the UI calls ----

    def key(self, key: str | int, modifiers: Mod = Mod.NONE) -> None:
        """A tap on the on-screen keyboard: engine first, document second."""
        handled = self.context.process_key(key, modifiers)
        if not handled:
            self._fallthrough(key)
        self._refresh_surrounding()

    def _fallthrough(self, key: str | int) -> None:
        if isinstance(key, str):
            self._insert(key)
        elif key == Key.SPACE:
            self._insert(" ")
        elif key == Key.RETURN:
            self._insert("\n")
        elif key == Key.BACKSPACE and self.cursor > 0:
            del self.document[self.cursor - 1]
            self.cursor -= 1
        elif key == Key.LEFT and self.cursor > 0:
            self.cursor -= 1
        elif key == Key.RIGHT and self.cursor < len(self.document):
            self.cursor += 1

    def tap_candidate(self, digit: int) -> None:
        """Digit 1-9: tap that candidate on the visible strip."""
        index = self.page * STRIP_SIZE + digit - 1
        if index < self.composition.candidate_count:
            self.context.select_candidate(index)
            self.page = 0
            self._refresh_surrounding()

    def slide(self, direction: int) -> None:
        """Left/right along the strip; the preedit may preview the hover."""
        comp = self.composition
        if not comp.candidates:
            return
        index = comp.candidate_cursor + direction
        if 0 <= index < comp.candidate_count:
            try:
                self.context.set_candidate_cursor(index)
            except pathime.UnsupportedError:
                pass

    def page_strip(self, direction: int) -> None:
        """Up/down: page the strip, growing the list past its cap on the way
        down — the cap is composition-safe and only ever appends."""
        comp = self.composition
        if direction > 0:
            wanted = (self.page + 1) * STRIP_SIZE
            if wanted >= comp.candidate_count:
                cap = self.context.get_option(Option.MAX_CANDIDATES)
                if comp.candidate_count == cap:  # maybe truncated; ask for more
                    self.context.set_option(Option.MAX_CANDIDATES,
                                            cap + STRIP_SIZE)
            if wanted < self.composition.candidate_count:
                self.page += 1
        elif self.page > 0:
            self.page -= 1

    def switch_engine(self) -> None:
        ids = list(self.contexts)
        self.active = ids[(ids.index(self.active) + 1) % len(ids)]
        self.page = 0
        self._refresh_surrounding()

    def commit(self) -> None:
        self.context.commit()
        self._refresh_surrounding()

    def reset(self) -> None:
        self.context.reset()
        self._refresh_surrounding()

    def close(self) -> None:
        for ctx in self.contexts.values():
            ctx.close()
        for engine in self.engines.values():
            engine.close()


# =========================================================================
# The curses front end
# =========================================================================

KEY_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]


def _draw(stdscr, phone: PhoneKeyboard, last_key: str) -> None:
    import curses

    stdscr.erase()
    height, width = stdscr.getmaxyx()
    comp = phone.composition

    def put(y, x, text, attr=0):
        if not (0 <= y < height and 0 <= x < width - 1):
            return
        try:
            stdscr.addnstr(y, x, text, width - x - 1, attr)
        except curses.error:
            pass  # a wide character clipped at the right edge

    label = ENGINE_LABELS.get(phone.active, phone.active.name)
    put(0, 1, f"[{label} {phone.active.name.lower()}]  Ctrl+E engine  "
              f"Ctrl+T commit  Ctrl+R discard  Ctrl+C quit", curses.A_DIM)

    # The text field: document with the preedit drawn in at the cursor,
    # settled green, still-changing tail underlined.
    put(2, 1, "┌" + "─" * (width - 4) + "┐", curses.A_DIM)
    doc = phone.text
    before, after = doc[:phone.cursor], doc[phone.cursor:]
    x = 3
    put(3, x, before)
    x += sum(2 if ord(c) > 0xFF else 1 for c in before)
    settled = comp.preedit[:comp.preedit_settled]
    tail = comp.preedit[comp.preedit_settled:]
    put(3, x, settled, curses.color_pair(2) | curses.A_UNDERLINE)
    x += sum(2 if ord(c) > 0xFF else 1 for c in settled)
    put(3, x, tail, curses.color_pair(3) | curses.A_UNDERLINE)
    x += sum(2 if ord(c) > 0xFF else 1 for c in tail)
    put(3, x, "▏", curses.A_BLINK)
    put(3, x + 1, after)
    put(4, 1, "└" + "─" * (width - 4) + "┘", curses.A_DIM)

    # The candidate strip.
    visible, highlight = phone.strip()
    x = 1
    for i, cand in enumerate(visible):
        attr = curses.A_REVERSE if i == highlight else 0
        text = f" {i + 1} {cand} "
        put(6, x, text, attr)
        x += sum(2 if ord(c) > 0xFF else 1 for c in text) + 1
    if comp.candidate_count > (phone.page + 1) * STRIP_SIZE:
        put(6, x, "▸", curses.A_DIM)
    total = comp.candidate_count
    if total:
        put(7, 1, f"page {phone.page + 1} · {total} candidates"
                  + ("+" if total >= phone.context.get_option(Option.MAX_CANDIDATES)
                     else ""),
            curses.A_DIM)

    # The on-screen keyboard, last tap highlighted.
    y = 9
    for row_index, row in enumerate(KEY_ROWS):
        x = 2 + row_index * 2
        for ch in row:
            attr = curses.A_REVERSE if ch == last_key else curses.A_DIM
            put(y, x, f" {ch} ", attr)
            x += 4
        y += 1
    put(y, 10, "  ␣ space  ", curses.A_REVERSE if last_key == " " else curses.A_DIM)

    stdscr.refresh()


def _run(stdscr, phone: PhoneKeyboard) -> None:
    import curses

    curses.raw()  # Ctrl+C is a key here, not a signal
    curses.curs_set(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

    last_key = ""
    while True:
        _draw(stdscr, phone, last_key)
        wch = stdscr.get_wch()
        last_key = wch if isinstance(wch, str) else ""

        if wch == "\x03":  # Ctrl+C
            return
        if wch == "\x05":  # Ctrl+E
            phone.switch_engine()
        elif wch == "\x14":  # Ctrl+T
            phone.commit()
        elif wch == "\x12":  # Ctrl+R
            phone.reset()
        elif wch == curses.KEY_LEFT:
            phone.slide(-1)
        elif wch == curses.KEY_RIGHT:
            phone.slide(+1)
        elif wch == curses.KEY_UP:
            phone.page_strip(-1)
        elif wch == curses.KEY_DOWN:
            phone.page_strip(+1)
        elif wch in ("\x7f", "\x08", curses.KEY_BACKSPACE):
            phone.key(Key.BACKSPACE)
        elif wch in ("\n", "\r", curses.KEY_ENTER):
            phone.key(Key.RETURN)
        elif wch == "\x1b":
            phone.key(Key.ESCAPE)
        elif isinstance(wch, str) and wch.isdigit() and wch != "0" \
                and phone.composition.candidates:
            phone.tap_candidate(int(wch))
        elif isinstance(wch, str) and wch.isprintable():
            phone.key(wch)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="phone-like keyboard demo for the pathime binding")
    parser.add_argument("--engine", default="pinyin",
                        choices=[e.name.lower() for e in EngineId],
                        help="engine to start on (Ctrl+E cycles the rest)")
    parser.add_argument("--data-dir", default=None,
                        help="where engines keep what they learn")
    parser.add_argument("--library", default=None,
                        help="path to libpathime (else PATHIME_LIBRARY)")
    args = parser.parse_args()

    if args.library:
        pathime.load(args.library)
    pathime.init(data_dir=args.data_dir)

    available = [e for e in EngineId if pathime.has_engine(e)]
    if not available:
        print("no engines available — is pathime-data/ beside the library?",
              file=sys.stderr)
        return 1
    start = EngineId[args.engine.upper()]
    if start in available:
        available.remove(start)
        available.insert(0, start)

    phone = PhoneKeyboard(available)
    try:
        import curses
        curses.wrapper(_run, phone)
    except KeyboardInterrupt:
        pass
    finally:
        phone.close()
        pathime.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
