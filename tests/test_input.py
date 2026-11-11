"""Regression tests for terminal input: every key must do what it says, and no
key may quit the game by accident."""
import curses
import os
import pty
import tty
import unittest

from depths.terminal import normalize_key, read_key


def press(data: bytes) -> int:
    master, slave = pty.openpty()
    tty.setraw(slave)
    os.write(master, data)
    try:
        return read_key(slave)
    finally:
        os.close(master)
        os.close(slave)


class ReadKeyTests(unittest.TestCase):
    def test_arrows(self):
        self.assertEqual(press(b"\x1b[A"), curses.KEY_UP)
        self.assertEqual(press(b"\x1b[B"), curses.KEY_DOWN)
        self.assertEqual(press(b"\x1b[C"), curses.KEY_RIGHT)
        self.assertEqual(press(b"\x1b[D"), curses.KEY_LEFT)

    def test_ss3_arrows_are_not_a_quit(self):
        # kitty, konsole and gnome-terminal all send these in application mode
        self.assertEqual(press(b"\x1bOA"), curses.KEY_UP)
        self.assertEqual(press(b"\x1bOB"), curses.KEY_DOWN)

    def test_modified_arrows_are_not_a_quit(self):
        self.assertEqual(press(b"\x1b[1;2A"), curses.KEY_UP)
        self.assertEqual(press(b"\x1b[1;5C"), curses.KEY_RIGHT)

    def test_unknown_escape_is_swallowed(self):
        self.assertEqual(press(b"\x1b[3~"), 0)  # Delete
        self.assertEqual(press(b"\x1b[H"), 0)  # Home

    def test_lone_escape_still_quits(self):
        self.assertEqual(press(b"\x1b"), 27)

    def test_plain_ascii(self):
        self.assertEqual(press(b"w"), ord("w"))

    def test_cyrillic_layout(self):
        # Russian layout: the same physical key must act the same
        self.assertEqual(press("ц".encode()), ord("w"))
        self.assertEqual(press("ф".encode()), ord("a"))
        self.assertEqual(press("ы".encode()), ord("s"))
        self.assertEqual(press("в".encode()), ord("d"))
        self.assertEqual(press("Д".encode()), ord("L"))


class NormalizeKeyTests(unittest.TestCase):
    def test_passes_curses_keys_through(self):
        self.assertEqual(normalize_key(curses.KEY_UP), curses.KEY_UP)
        self.assertEqual(normalize_key(ord("q")), ord("q"))

    def test_maps_cyrillic(self):
        self.assertEqual(normalize_key(ord("л")), ord("k"))
        self.assertEqual(normalize_key(ord("Ы")), ord("S"))


if __name__ == "__main__":
    unittest.main()
