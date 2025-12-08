# frames/player/hotkey_manager.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from typing import Dict, Callable

if wx.Platform == '__WXMSW__':
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        MOD_NONE = 0x0000
        
        VK_MEDIA_PLAY_PAUSE = 0xB3
        VK_MEDIA_NEXT_TRACK = 0xB0
        VK_MEDIA_PREV_TRACK = 0xB1
        VK_VOLUME_UP = 0xAF
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_MUTE = 0xAD
        VK_BROWSER_BACK = 0xA6
        VK_BROWSER_FORWARD = 0xA7
    except (ImportError, AttributeError):
        logging.error("Failed to import ctypes or load user32.dll. Global hotkeys disabled.")
        user32 = None
        VK_MEDIA_PLAY_PAUSE = VK_MEDIA_NEXT_TRACK = VK_MEDIA_PREV_TRACK = 0
        VK_VOLUME_UP = VK_VOLUME_DOWN = VK_VOLUME_MUTE = 0
        VK_BROWSER_BACK = VK_BROWSER_FORWARD = 0
else:
    logging.info("Native global hotkeys are only implemented for Windows.")
    user32 = None
    VK_MEDIA_PLAY_PAUSE = VK_MEDIA_NEXT_TRACK = VK_MEDIA_PREV_TRACK = 0
    VK_VOLUME_UP = VK_VOLUME_DOWN = VK_VOLUME_MUTE = 0
    VK_BROWSER_BACK = VK_BROWSER_FORWARD = 0


class HotkeyManager:
    """
    Manages the registration and handling of system-wide global hotkeys using
    native Windows API calls (user32.dll).
    """

    def __init__(self, frame: wx.Frame):
        self.frame = frame
        self.hwnd = self.frame.GetHandle()
        self.hotkey_map: Dict[int, Callable] = {}
        self.next_hotkey_id: int = 1

        if not self.hwnd:
            logging.error("HotkeyManager: Cannot register hotkeys, window handle (HWND) is None.")

    def _register(self, vk_code: int, callback: Callable):
        """Registers a single global hotkey with the OS."""
        if not user32 or not self.hwnd:
            return

        hk_id = self.next_hotkey_id
        self.next_hotkey_id += 1

        if not user32.RegisterHotKey(self.hwnd, hk_id, MOD_NONE, vk_code):
            error_code = ctypes.GetLastError()
            logging.error(f"Failed to register hotkey ID {hk_id} (VK: {vk_code}). Error: {error_code}")
        else:
            logging.info(f"Registered hotkey ID {hk_id} (VK: {vk_code})")
            self.hotkey_map[hk_id] = callback

    def setup_hotkeys(self, key_function_map: Dict[int, Callable]):
        """
        Registers multiple hotkeys based on a mapping of VK codes to callback functions.
        """
        if not user32:
            return

        logging.info("Registering native Windows global hotkeys...")
        for vk_code, callback in key_function_map.items():
            if vk_code != 0:
                self._register(vk_code, callback)

    def on_hotkey_pressed(self, event: wx.KeyEvent):
        """
        Event handler for wx.EVT_HOTKEY.
        """
        if self.frame.is_exiting:
            return

        hk_id = event.GetId()
        callback = self.hotkey_map.get(hk_id)
        
        if callback:
            logging.debug(f"Global hotkey pressed, ID: {hk_id}")
            try:
                callback()
            except Exception as e:
                logging.error(f"Error executing hotkey callback: {e}")
        else:
            logging.warning(f"Unknown hotkey ID received: {hk_id}")
        
        event.Skip()

    def unregister_hotkeys(self):
        """Unregisters all currently active global hotkeys."""
        if not user32 or not self.hwnd:
            return

        logging.info("Unregistering global hotkeys...")
        for hk_id in list(self.hotkey_map.keys()):
            if not user32.UnregisterHotKey(self.hwnd, hk_id):
                logging.debug(f"Failed to unregister hotkey ID {hk_id}")
            else:
                logging.debug(f"Unregistered hotkey ID {hk_id}")
        
        self.hotkey_map.clear()
