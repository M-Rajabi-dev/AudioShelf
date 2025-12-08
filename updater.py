# updater.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import wx.lib.newevent
import urllib.request
import json
import threading
import logging
import sys
import os
import subprocess
import tempfile
import re
import zipfile
import time
import shutil

# Configuration
REPO_OWNER = "M-Rajabi-Dev"
REPO_NAME = "AudioShelf"
def get_app_version():
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        version_path = os.path.join(base_path, 'VERSION')
        with open(version_path, 'r') as f:
            return f.read().strip()
    except Exception:
        return "1.0.0"

CURRENT_VERSION = get_app_version()
PORTABLE_MARKER_FILE = ".portable"

UpdateResultEvent, EVT_UPDATE_RESULT = wx.lib.newevent.NewEvent()
DownloadResultEvent, EVT_DOWNLOAD_RESULT = wx.lib.newevent.NewEvent()


class UpdateManager:
    """
    Manages checking for updates, downloading assets, and applying updates.
    """

    def __init__(self, frame: wx.Frame):
        self.frame = frame
        self.api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        self.is_checking = False
        self.is_frozen = getattr(sys, 'frozen', False)
        self.is_portable = self._check_is_portable()

    def _check_is_portable(self) -> bool:
        """
        Robust check for portable mode.
        Checks next to the executable AND inside the _internal folder.
        """
        if self.is_frozen:
            app_path = os.path.dirname(sys.executable)
            internal_path = os.path.join(app_path, '_libs')
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
            internal_path = app_path

        paths_to_check = [
            os.path.join(app_path, PORTABLE_MARKER_FILE),
            os.path.join(internal_path, PORTABLE_MARKER_FILE)
        ]
        
        for p in paths_to_check:
            if os.path.exists(p):
                return True
        return False

    def check_for_updates(self, silent_if_up_to_date: bool = False):
        """Starts the update check."""
        # Only check in frozen mode to avoid updating dev environment
        if not self.is_frozen:
            return

        if self.is_checking:
            return

        self.is_checking = True
        thread = threading.Thread(
            target=self._check_worker,
            args=(silent_if_up_to_date,),
            daemon=True
        )
        thread.start()

    def _check_worker(self, silent_if_up_to_date: bool):
        """Background worker to fetch release info."""
        try:
            logging.info(f"Checking for updates from {self.api_url}...")
            with urllib.request.urlopen(self.api_url, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"API returned status: {response.status}")
                data = json.loads(response.read().decode('utf-8'))

            latest_tag = data.get("tag_name", "0.0.0")
            latest_version = latest_tag.lstrip('v')
            is_newer = self._compare_versions(latest_version, CURRENT_VERSION)
            
            download_url = None
            
            if is_newer:
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    
                    if self.is_portable:
                        # For portable, look for .zip AND 'portable' keyword
                        if name.endswith(".zip") and "portable" in name:
                            download_url = asset.get("browser_download_url")
                            break
                    else:
                        # For installer, look for .exe
                        if name.endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break

            wx.PostEvent(self.frame, UpdateResultEvent(
                success=True,
                has_update=is_newer and (download_url is not None),
                latest_version=latest_version,
                download_url=download_url,
                error_msg=None if download_url else "No matching update file found.",
                silent=silent_if_up_to_date,
                is_portable=self.is_portable
            ))

        except Exception as e:
            logging.error(f"Update check failed: {e}", exc_info=True)
            wx.PostEvent(self.frame, UpdateResultEvent(
                success=False,
                has_update=False,
                latest_version=None,
                download_url=None,
                error_msg=str(e),
                silent=silent_if_up_to_date,
                is_portable=self.is_portable
            ))
        finally:
            self.is_checking = False

    def _compare_versions(self, ver_a: str, ver_b: str) -> bool:
        """Compares two version strings."""
        def parse(v):
            parts = []
            for x in v.split('.'):
                if x.isdigit():
                    parts.append(int(x))
            return parts
        return parse(ver_a) > parse(ver_b)

    def download_and_install(self, url: str):
        """Starts downloading the update asset."""
        if not url:
            return
        logging.info(f"Starting download from: {url}")
        thread = threading.Thread(
            target=self._download_worker,
            args=(url,),
            daemon=True
        )
        thread.start()

    def _download_worker(self, url: str):
        """Downloads the file to a temp location."""
        try:
            temp_dir = tempfile.gettempdir()
            filename = url.split('/')[-1] or ("update.zip" if self.is_portable else "setup.exe")
            save_path = os.path.join(temp_dir, filename)

            logging.info(f"Downloading update to: {save_path}")
            with urllib.request.urlopen(url) as response, open(save_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            logging.info("Download complete.")
            wx.PostEvent(self.frame, DownloadResultEvent(
                success=True, 
                path=save_path, 
                error_msg=None, 
                is_portable=self.is_portable
            ))

        except Exception as e:
            logging.error(f"Download failed: {e}", exc_info=True)
            wx.PostEvent(self.frame, DownloadResultEvent(
                success=False, 
                path=None, 
                error_msg=str(e), 
                is_portable=self.is_portable
            ))

    def apply_update(self, path: str):
        """Dispatches to the correct installation method."""
        if self.is_portable:
            self._perform_portable_update(path)
        else:
            self._launch_installer(path)

    def _launch_installer(self, path: str):
        """Launches the downloaded installer (Standard Mode)."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen([path])
            logging.info("Installer launched. Exiting application.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Failed to launch installer: {e}", exc_info=True)
            wx.MessageBox(f"Failed to launch installer:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    def _perform_portable_update(self, zip_path: str):
        """
        Extracts the update and creates a script to swap files after exit.
        """
        try:
            temp_extract_dir = os.path.join(tempfile.gettempdir(), f"audioshelf_update_{int(time.time())}")
            os.makedirs(temp_extract_dir, exist_ok=True)
            
            logging.info(f"Extracting portable update to {temp_extract_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            current_app_dir = os.path.dirname(sys.executable)
            
            # Handle single root folder in zip
            extracted_items = os.listdir(temp_extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted_items[0])):
                source_dir = os.path.join(temp_extract_dir, extracted_items[0])
            else:
                source_dir = temp_extract_dir

            updater_script_path = os.path.join(tempfile.gettempdir(), "audioshelf_updater.bat")
            executable_name = os.path.basename(sys.executable)
            
            batch_content = f"""
@echo off
title AudioShelf Updater
echo Waiting for AudioShelf to close...
timeout /t 3 /nobreak >nul

echo Updating files...
xcopy "{source_dir}\\*" "{current_app_dir}\\" /E /H /Y /Q

echo Cleaning up...
rmdir /s /q "{temp_extract_dir}"
del "{zip_path}"

echo Restarting AudioShelf...
start "" "{os.path.join(current_app_dir, executable_name)}"

echo Done.
del "%~f0"
exit
"""
            with open(updater_script_path, "w") as bat_file:
                bat_file.write(batch_content)

            logging.info(f"Updater script created at {updater_script_path}. Launching...")
            subprocess.Popen([updater_script_path], shell=True)
            sys.exit(0)

        except Exception as e:
            logging.error(f"Portable update failed: {e}", exc_info=True)
            wx.MessageBox(f"Portable update failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
