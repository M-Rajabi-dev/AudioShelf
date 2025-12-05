# main.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import sys
import os
import logging
import socket
import threading
import wx
from logging.handlers import RotatingFileHandler

APP_NAME = "AudioShelf"
PORTABLE_MARKER_FILE = ".portable"
LOCAL_DATA_DIR_NAME = "user_data"
IPC_PORT = 48921

def _get_log_path_for_os() -> str:
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
        internal_path = os.path.join(app_path, '_libs')
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))
        internal_path = app_path

    is_portable = (
        os.path.exists(os.path.join(app_path, PORTABLE_MARKER_FILE)) or
        os.path.exists(os.path.join(internal_path, PORTABLE_MARKER_FILE))
    )
    
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        if os.path.exists(os.path.join(sys._MEIPASS, PORTABLE_MARKER_FILE)):
            is_portable = True

    if is_portable:
        data_dir = os.path.join(app_path, LOCAL_DATA_DIR_NAME)
    else:
        if sys.platform == "win32":
            local_app_data_path = os.getenv('LOCALAPPDATA')
            if local_app_data_path:
                data_dir = os.path.join(local_app_data_path, APP_NAME)
            else:
                data_dir = os.path.join(os.path.expanduser("~"), f".{APP_NAME}_local")
        elif sys.platform == "darwin":
            data_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Logs', APP_NAME)
        else:
            xdg_state_home = os.getenv('XDG_STATE_HOME')
            if xdg_state_home:
                data_dir = os.path.join(xdg_state_home, APP_NAME)
            else:
                data_base_dir = os.getenv('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
                data_dir = os.path.join(os.path.dirname(data_base_dir), 'state', APP_NAME)

    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "AudioShelf.log")

LOG_FILE = _get_log_path_for_os()
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"
LOG_MAX_SIZE_MB = 5
LOG_BACKUP_COUNT = 3

try:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    logging.info("--- Logging started for AudioShelf ---")
    logging.info(f"Log file location: {LOG_FILE}")

except Exception as e:
    print(f"FATAL: Could not initialize logger. Error: {e}", file=sys.stderr)


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical("Unhandled exception caught:", exc_info=(exc_type, exc_value, exc_traceback))

    try:
        app = wx.GetApp()
        if app and hasattr(app, 'player_frame_instance') and app.player_frame_instance:
            if hasattr(app.player_frame_instance, 'hotkey_manager') and app.player_frame_instance.hotkey_manager:
                app.player_frame_instance.hotkey_manager.unregister_hotkeys()
    except Exception as e:
        logging.error(f"Failed to cleanup during crash: {e}")

    wx.MessageBox(
        "A critical error occurred. AudioShelf must close.\n"
        f"Please check the log file for details:\n{LOG_FILE}",
        "Unhandled Error",
        wx.OK | wx.ICON_ERROR
    )

sys.excepthook = handle_uncaught_exception

try:
    from database import db_manager
    from i18n import _
    from frames.library_frame import LibraryFrame
    from frames.library import task_handlers
except ImportError as e:
    logging.critical(f"Failed to import core modules: {e}", exc_info=True)
    sys.exit(1)


class IPCServer(threading.Thread):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.running = True
        self.server_socket = None

    def run(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('127.0.0.1', IPC_PORT))
            self.server_socket.listen(1)
            logging.info(f"IPC Server listening on port {IPC_PORT}")
            
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    data = conn.recv(4096).decode('utf-8')
                    if data:
                        logging.info(f"IPC received: {data}")
                        wx.CallAfter(self.app.on_ipc_message, data)
                    conn.close()
                except socket.error:
                    if self.running:
                        logging.debug("IPC socket accept error (normal during shutdown).")
        except Exception as e:
            logging.error(f"IPC Server failed: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


class AudioShelfApp(wx.App):
    def __init__(self, *args, **kwargs):
        self.player_frame_instance = None
        self.ipc_server = None
        self.frame = None
        self.instance_checker = None
        super().__init__(*args, **kwargs)

    def OnInit(self):
        logging.info("wx.App.OnInit started.")
        self.SetAppName("AudioShelf")

        self.instance_checker = wx.SingleInstanceChecker(f"AudioShelf_Mutex_{wx.GetUserId()}")
        
        if self.instance_checker.IsAnotherRunning():
            logging.info("Another instance detected via Mutex. Attempting IPC handover...")
            if self._send_to_existing_instance():
                return False
            else:
                logging.warning("Could not connect to existing instance IPC. Exiting.")
                return False

        try:
            self.frame = LibraryFrame(None, title=_("AudioShelf - My Library"))
            
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                icon_path = os.path.join(exe_dir, '_libs', "AudioShelf.ico")
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(base_path, "AudioShelf.ico")
            
            if os.path.exists(icon_path):
                try:
                    icon_bundle = wx.IconBundle()
                    icon_bundle.AddIcon(icon_path, wx.BITMAP_TYPE_ICO)
                    self.frame.SetIcons(icon_bundle)
                except Exception as e:
                    logging.warning(f"Failed to set app icon: {e}")

            self.frame.Show(True)
            self.SetTopWindow(self.frame)

            self.ipc_server = IPCServer(self)
            self.ipc_server.daemon = True
            self.ipc_server.start()

            if len(sys.argv) > 1:
                self._process_cli_arg(sys.argv[1])

            logging.info("LibraryFrame shown. Entering MainLoop.")
            return True

        except Exception as e:
            logging.critical("Failed to create LibraryFrame in OnInit.", exc_info=True)
            return False

    def _send_to_existing_instance(self) -> bool:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(0.1) 
            client_socket.connect(('127.0.0.1', IPC_PORT))
            
            message = sys.argv[1] if len(sys.argv) > 1 else "FOCUS"
            client_socket.sendall(message.encode('utf-8'))
            client_socket.close()
            return True
        except Exception as e:
            logging.error(f"Error sending to existing instance: {e}")
            return False

    def on_ipc_message(self, message):
        target_window = self.frame
        
        if self.player_frame_instance:
            try:
                if self.player_frame_instance.IsShown():
                    target_window = self.player_frame_instance
            except Exception:
                pass

        if target_window:
            if target_window.IsIconized():
                target_window.Iconize(False)
            if not target_window.IsShown():
                target_window.Show()
            
            target_window.Raise()
            target_window.SetFocus()
            target_window.RequestUserAttention()
            
            if hasattr(target_window, 'library_list') and target_window.library_list:
                target_window.library_list.SetFocus()
            elif hasattr(target_window, 'nvda_focus_label'):
                target_window.nvda_focus_label.SetFocus()
            
            if message != "FOCUS":
                self._process_cli_arg(message)

    def _process_cli_arg(self, input_path):
        if os.path.exists(input_path):
            logging.info(f"Processing file/folder argument: {input_path}")
            wx.CallAfter(task_handlers.trigger_book_scan, self.frame, input_path, 1)

    def OnExit(self):
        logging.info("--- Application closing. ---")
        if self.ipc_server:
            self.ipc_server.stop()
        
        try:
            db_manager.close()
        except Exception as e:
            logging.error("Error closing database connection.", exc_info=True)
        
        self.instance_checker = None
        return 0

if __name__ == "__main__":
    logging.info("Starting AudioShelfApp...")
    app = AudioShelfApp(redirect=False)
    app.MainLoop()