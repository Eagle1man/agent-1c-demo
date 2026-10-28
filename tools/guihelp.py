# -*- coding: utf-8 -*-
"""Общие GUI-примитивы для автоматизации 1С: раскладка, ожидание, вставка."""
import ctypes
import time

user32 = ctypes.windll.user32


def ensure_ru(hwnd):
    """Переключить раскладку окна на русскую."""
    try:
        user32.LoadKeyboardLayoutW("00000419", 1)
        user32.PostMessageW(hwnd, 0x50, 0, 0x4190419)
        time.sleep(1)
        return True
    except Exception:
        return False


def wait_for(fn, desc, lines, timeout=25):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = fn()
            if r is not None:
                return r
        except Exception:
            pass
        time.sleep(2)
    lines.append("!! timeout: " + desc)
    return None


def set_clipboard_text(text):
    """Буфер обмена напрямую через Win32 (без powershell)."""
    import ctypes.wintypes as wt
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard(None)
    try:
        user32.EmptyClipboard()
        data = (text + "\x00").encode("utf-16-le")
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
    finally:
        user32.CloseClipboard()
