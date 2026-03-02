import pytest
import win32con
from unittest.mock import patch
from tray.clipboard import Clipboard

def test_process_message_calls_on_clipboard_change():
    cb = Clipboard()
    with patch.object(cb, '_on_clipboard_change') as mock_change:
        with patch('tray.clipboard.win32gui.DefWindowProc', return_value=0):
            cb._process_message(0, Clipboard._WM_CLIPBOARDUPDATE, 0, 0)
            mock_change.assert_called_once()

def test_process_message_ignores_other_messages():
    cb = Clipboard()
    with patch.object(cb, '_on_clipboard_change') as mock_change:
        with patch('tray.clipboard.win32gui.DefWindowProc', return_value=0):
            cb._process_message(0, 0, 0, 0)
            mock_change.assert_not_called()

def test_read_clipboard_returns_text():
    def format_available(fmt):
        return fmt == win32con.CF_UNICODETEXT

    with (
        patch('tray.clipboard.win32clipboard.OpenClipboard'),
        patch('tray.clipboard.win32clipboard.CloseClipboard'),
        patch('tray.clipboard.win32clipboard.IsClipboardFormatAvailable', side_effect=format_available),
        patch('tray.clipboard.win32clipboard.GetClipboardData', return_value="Sample text")
    ):

        clip = Clipboard.read_clipboard()
        assert clip is not None
        assert clip.clip_type == 'text'
        assert clip.value == 'Sample text'

def test_read_clipboard_returns_none_when_empty():
    with (patch('tray.clipboard.win32clipboard.OpenClipboard'),
        patch('tray.clipboard.win32clipboard.CloseClipboard'),
        patch('tray.clipboard.win32clipboard.IsClipboardFormatAvailable', return_value=False)
    ):
    
        clip = Clipboard.read_clipboard()
        assert clip is None

def test_read_clipboard_returns_none_on_open_failure():
    with (
        patch('tray.clipboard.win32clipboard.OpenClipboard', side_effect=Exception("locked")),
        patch('tray.clipboard.win32clipboard.CloseClipboard'),
        patch('tray.clipboard.time.sleep')
    ):

        clip = Clipboard.read_clipboard()
        assert clip is None

def test_on_text_callback_fires():
    result = []
    cb = Clipboard(on_text=lambda t: result.append(t))

    mock_clip = Clipboard.Clip('text', 'hello')
    with patch.object(Clipboard, 'read_clipboard', return_value=mock_clip):
        cb._on_clipboard_change()
    
    assert result == ['hello']

def test_on_update_callback_fires():
    result = []
    cb = Clipboard(on_update=lambda c: result.append(c))

    mock_clip = Clipboard.Clip('text', 'asdf')
    with patch.object(Clipboard, 'read_clipboard', return_value=mock_clip):
        cb._on_clipboard_change()

    assert result == [mock_clip]