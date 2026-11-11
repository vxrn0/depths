"""Terminal I/O: curses colors, pixel-size queries, raw key reads, sixel detect."""
import curses, os, re, select, sys, time, tty, termios

from .constants import COLORS


def init_colors():
    curses.start_color()
    try:
        curses.use_default_colors()
    except Exception:
        pass
    BG_FLOOR = 236
    BG_WALL = 234
    tile_colors = {"wall","floor","door","stairs","secret","player","goblin","orc","troll","dragon",
        "skeleton","bat","wraith","archer","necromancer","mimic","rat","vampire","golem",
        "potion","weapon","armor","gold","scroll","food","ring","wand","key","trap","dim"}
    if curses.COLORS < 256:
        # limited color terminal: no backgrounds
        for name, code in COLORS.items():
            c8 = code % 8
            try:
                curses.init_pair(hash(name) % 200 + 1, c8, -1)
            except Exception:
                pass
    else:
        for name, code in COLORS.items():
            bg = BG_WALL if name in ("wall","secret") else (BG_FLOOR if name in tile_colors else -1)
            curses.init_pair(hash(name) % 200 + 1, code, bg)
    for name in COLORS:
        setattr(Color, name, hash(name) % 200 + 1)

class Color: pass

def cp(name): return curses.color_pair(getattr(Color, name))


_cell_size_cache = None
_terminal_pixels_cache = None


def get_cell_size():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write("\x1b[16t")
        sys.stdout.flush()
        buf = ""
        deadline = time.time() + 0.5
        while time.time() < deadline:
            r,_,_ = select.select([fd], [], [], 0.1)
            if not r: 
                if buf: break
                continue
            c = os.read(fd, 1).decode('latin1', 'replace')
            buf += c
            if c == 't':
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    m = re.search(r'\x1b\[6;(\d+);(\d+)t', buf)
    if m:
        return int(m.group(2)), int(m.group(1))
    return 8, 16


def get_terminal_pixels():
    """Query terminal text area size in pixels (CSI 14 t). Cached."""
    global _terminal_pixels_cache
    if _terminal_pixels_cache is not None:
        return _terminal_pixels_cache
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write("\x1b[14t")
        sys.stdout.flush()
        buf = ""
        deadline = time.time() + 0.5
        while time.time() < deadline:
            r,_,_ = select.select([fd], [], [], 0.1)
            if not r:
                if buf: break
                continue
            c = os.read(fd, 1).decode('latin1', 'replace')
            buf += c
            if c == 't':
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    m = re.search(r'\x1b\[4;(\d+);(\d+)t', buf)
    if m:
        _terminal_pixels_cache = (int(m.group(2)), int(m.group(1)))
        return _terminal_pixels_cache
    cell_w, cell_h = get_cell_size()
    import shutil
    ts = shutil.get_terminal_size((80, 24))
    _terminal_pixels_cache = (ts.columns * cell_w, ts.lines * cell_h)
    return _terminal_pixels_cache


def get_cell_size_cached():
    global _cell_size_cache
    if _cell_size_cache is None:
        _cell_size_cache = get_cell_size()
    return _cell_size_cache


# Cyrillic letters on a Russian layout, mapped to the Latin key on the same cap.
_CYRILLIC = {
    "ц": "w", "ф": "a", "ы": "s", "в": "d",
    "р": "h", "о": "j", "л": "k", "д": "l",
    "н": "y", "г": "u", "и": "b", "т": "n",
    "й": "q", "з": "p", "к": "r", "ш": "i",
    "м": "v", "с": "c", "ч": "x",
}
_CYRILLIC.update({k.upper(): v.upper() for k, v in _CYRILLIC.items()})

_ARROWS = {"A": curses.KEY_UP, "B": curses.KEY_DOWN,
           "C": curses.KEY_RIGHT, "D": curses.KEY_LEFT}


def normalize_key(key):
    """A Russian-layout letter acts as the Latin key on the same cap."""
    if 0 < key < 0x10000:
        latin = _CYRILLIC.get(chr(key))
        if latin:
            return ord(latin)
    return key


def _read_char(fd, first):
    """Finish a UTF-8 sequence: os.read(fd, 1) hands back bare bytes."""
    n = 4 if first[0] >= 0xF0 else 3 if first[0] >= 0xE0 else 2 if first[0] >= 0xC0 else 1
    while len(first) < n:
        more = os.read(fd, n - len(first))
        if not more:
            break
        first += more
    return first.decode("utf-8", "replace")


def read_key(fd):
    first = os.read(fd, 1)
    if not first:
        return 0
    if first == b"\x1b":
        buf = b""
        while len(buf) < 16:
            r, _, _ = select.select([fd], [], [], 0.05)
            if not r:
                break
            buf += os.read(fd, 1)
        if not buf:
            return 27  # a lone Esc
        if buf[:1] in (b"[", b"O"):
            # CSI (`ESC [ 1;2A`) and SS3 (`ESC O A`) both end in the arrow letter
            return _ARROWS.get(chr(buf[-1]), 0)
        return 0  # unknown escape: ignored, never mistaken for a quit
    ch = _read_char(fd, first)
    return normalize_key(ord(ch)) if len(ch) == 1 else 0


def _safe_detect_sixel():
    try:
        return detect_sixel()
    except Exception:
        return False


def detect_sixel():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write("\x1b[c")
        sys.stdout.flush()
        buf = ""
        deadline = time.time() + 0.5
        while time.time() < deadline:
            r,_,_ = select.select([fd], [], [], 0.1)
            if not r:
                if buf: break
                continue
            c = os.read(fd, 1).decode('latin1', 'replace')
            buf += c
            if c == 'c':
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ";4;" in buf or ";4c" in buf or "4;" in buf
