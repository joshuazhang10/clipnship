import ctypes
import win32con, win32gui, win32api, win32clipboard
import threading
import time
from dataclasses import dataclass
from typing import Callable

# Adapted from https://abdus.dev/posts/monitor-clipboard/
class Clipboard:
    '''Clipboard class for reading and monitoring win32 clipboard
    '''
    @dataclass
    class Clip:
        '''Holds data type and content of the clipboard.
        '''
        clip_type: str # Type of content
        value: str # Actual content

    _WM_CLIPBOARDUPDATE = 0x031D

    def __init__(
            self,
            on_text: Callable[[str], None] | None = None,
            on_update: Callable[[Clip], None] | None = None,
            on_error: Callable[[str], None] | None = None
        ):
        '''Creates a Clipboard. Clipboard needs a window to monitor messages.
        '''
        self._last_sync_time = 0
        self._rate_limit = 1.0 # Seconds

        self._on_text = on_text
        self._on_update = on_update
        self._on_error = on_error

        self._hwnd: int | None = None

    def _create_window(self) -> int:
        '''Creates a hidden window for listening to messages

        Returns:
            int: hwnd aka window handle
        '''
        window_title = "clipnship"
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._process_message # type: ignore
        wc.lpszClassName = window_title # type: ignore
        wc.hInstance = win32api.GetModuleHandle(None) # type: ignore
        class_atom = win32gui.RegisterClass(wc)
        parent = win32con.HWND_MESSAGE
        return win32gui.CreateWindowEx(0, class_atom, window_title, 0, 0, 0, # type: ignore
            0, 0, parent, 0, 0, None
        )
    
    def _process_message(self, hwnd: int, message: int, wparam: int, lparam: int):
        try:
            if message == self._WM_CLIPBOARDUPDATE:
                self._on_clipboard_change()
        except Exception as e:
            print(f"Error processing message: {e}")
        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)
    
    def _on_clipboard_change(self):
        now = time.perf_counter()
        if now - self._last_sync_time >= self._rate_limit:
            self._last_sync_time = now

            clip = self.read_clipboard()
            if not clip: 
                if self._on_error:
                    self._on_error("Failed to read clipboard")
                return None
            
            if self._on_update:
                # Likely that user doesn't want to get a notification every time they copy on PC
                self._on_update(clip)
            
            if clip.clip_type == 'text' and self._on_text:
                self._on_text(clip.value)

    @staticmethod
    def read_clipboard() -> Clip | None:
        # Window we are copying from needs to release its clipboard before we copy it,
        # so give the window up to 2 seconds to release
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline:
            try:
                win32clipboard.OpenClipboard()
                break
            except Exception:
                time.sleep(0.01)
        else:
            return None

        try:
            def get_formatted(fmt):
                if win32clipboard.IsClipboardFormatAvailable(fmt):
                    return win32clipboard.GetClipboardData(fmt)
                return None

            if text := get_formatted(win32con.CF_UNICODETEXT):
                return Clipboard.Clip('text', text)
            elif text_bytes := get_formatted(win32con.CF_TEXT):
                # ANSI text
                return Clipboard.Clip('text', text_bytes.decode())
            elif bitmap_handle := get_formatted(win32con.CF_BITMAP):
                # TODO: Handle images/screenshots
                # Will need Pillow at some point
                # Windows/iPhone also have different img formats
                pass

            return None
        finally:
            win32clipboard.CloseClipboard()
    
    def listen(self):
        def runner():
            self._hwnd = self._create_window()
            ctypes.windll.user32.AddClipboardFormatListener(self._hwnd)
            win32gui.PumpMessages()
            
        th = threading.Thread(target=runner, daemon=True)
        th.start()
        try:
            while th.is_alive():
                th.join(0.25)
        except KeyboardInterrupt:
            ctypes.windll.user32.RemoveClipboardFormatListener(self._hwnd)
            print("Shutting down...")

if __name__ == '__main__':
    clipboard = Clipboard(on_update=print)
    clipboard.listen()