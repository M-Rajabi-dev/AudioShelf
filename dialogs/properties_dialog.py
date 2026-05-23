# dialogs/properties_dialog.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import threading
import wx.lib.newevent
from typing import Optional, Dict, Any

from database import db_manager
from db_layer.helpers import get_book_size_on_disk
from i18n import _
from utils import format_time_spoken

SizeResultEvent, EVT_SIZE_RESULT = wx.lib.newevent.NewEvent()


def format_size(size_bytes: Optional[int]) -> str:
    if size_bytes is None:
        return _("Calculating...")
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


class PropertiesDialog(wx.Dialog):
    def __init__(self, parent, book_id: int):
        super(PropertiesDialog, self).__init__(parent, title=_("Book Properties"), size=(500, 450))

        self.book_id = book_id
        self.book_path: Optional[str] = None
        self.book_size: Optional[int] = None
        self.book_data: Dict[str, Any] = {}

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.text_ctrl = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP | wx.BORDER_SUNKEN
        )
        self.main_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        self.close_btn = wx.Button(self.panel, wx.ID_CANCEL, _("&Close"))
        btn_sizer.AddButton(self.close_btn)
        btn_sizer.Realize()

        self.main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 10)

        self.panel.SetSizer(self.main_sizer)
        self.CentreOnParent()

        self.Bind(EVT_SIZE_RESULT, self.on_size_result)

        self._load_data()
        self._update_text_content()
        self.start_size_calculation_thread()

        self.text_ctrl.SetFocus()

    def _load_data(self):
        details = db_manager.get_book_details(self.book_id)
        if not details:
            self.book_data = {"title": _("Error Loading Book")}
            return

        self.book_path = details.get('root_path')

        shelf_id = details.get('shelf_id')
        shelf_name = _("Unknown")
        if shelf_id == 1:
            shelf_name = _("Default Shelf")
        else:
            s_info = db_manager.get_shelf_details(shelf_id)
            if s_info:
                shelf_name = s_info['name']

        files = db_manager.get_book_files(self.book_id)
        file_count = len(files)
        total_duration_ms = sum(f[3] for f in files if f[3])

        if file_count == 1:
            file_count_str = _("1 file")
        else:
            file_count_str = _("{0} files").format(file_count)


        playback = db_manager.get_playback_state(self.book_id)
        progress_str = _("Not started")
        
        if playback and file_count > 0:
            idx = playback.get('last_file_index', 0)
            pct = int(((idx + 1) / file_count) * 100)
            progress_str = f"{pct}% ({_('File')} {idx + 1} {_('of')} {file_count})"

        elapsed_ms = 0
        if playback and file_count > 0:
            idx = playback.get('last_file_index', 0)
            pos = playback.get('last_position_ms', 0)
            for i in range(idx):
                if i < len(files):
                    elapsed_ms += (files[i][3] or 0)
            elapsed_ms += pos

        if details.get('is_finished'):
            progress_str = _("Finished")
            elapsed_ms = total_duration_ms

        remaining_ms = max(0, total_duration_ms - elapsed_ms)

        last_played = details.get('last_played_timestamp')
        last_played_str = str(last_played) if last_played else _("Never")

        self.book_data = {
            "title": details.get('title', _("Unknown Title")),
            "path": self.book_path,
            "shelf": shelf_name,
            "files": file_count_str,
            "duration": format_time_spoken(total_duration_ms),
            "elapsed": format_time_spoken(elapsed_ms),
            "remaining": format_time_spoken(remaining_ms),
            "progress": progress_str,
            "last_played": last_played_str,
            "status": _("Pinned") if details.get('is_pinned') else _("Normal")
        }

    def _update_text_content(self):
        size_str = format_size(self.book_size)
        d = self.book_data

        lines = [
            f"{_('Title')}: {d.get('title')}",
            "-" * 30,
            f"{_('Status')}: {d.get('status')}",
            f"{_('Progress')}: {d.get('progress')}",
            f"{_('Total Duration')}: {d.get('duration')}",
            f"{_('Time Elapsed')}: {d.get('elapsed')}",
            f"{_('Time Remaining')}: {d.get('remaining')}",
            "",
            f"[{_('File Info')}]",
            f"{_('Location')}: {d.get('path')}",
            f"{_('File Count')}: {d.get('files')}",
            f"{_('Total Size')}: {size_str}",
            f"{_('Shelf')}: {d.get('shelf')}",
            "",
            f"[{_('History')}]",
            f"{_('Last Played')}: {d.get('last_played')}"
        ]

        full_text = "\n".join(lines)
        
        self.text_ctrl.ChangeValue(full_text)
        self.text_ctrl.SetInsertionPoint(0)

    def start_size_calculation_thread(self):
        thread = threading.Thread(target=self._calculate_size_worker)
        thread.daemon = True
        thread.start()

    def _calculate_size_worker(self):
        try:
            size_bytes = get_book_size_on_disk(self.book_path)
            wx.PostEvent(self, SizeResultEvent(size=size_bytes))
        except Exception:
            wx.PostEvent(self, SizeResultEvent(size=None))

    def on_size_result(self, event: SizeResultEvent):
        self.book_size = event.size
        self._update_text_content()