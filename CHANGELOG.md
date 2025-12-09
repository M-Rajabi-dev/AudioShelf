# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-10

### Added
- **Shift+Delete Support:** Use `Shift + Delete` to permanently delete files from your computer (with confirmation).
- **Copy Time:** Added `Ctrl+I` shortcut to copy the current playback time to the system clipboard.
- **Safety Improvements:** Added warning sounds to critical confirmation dialogs (Delete, Clear Library, etc.).

### Changed
- **Dialog Behavior:** Confirmation dialogs now default to "Yes" for faster workflow (standard Windows behavior).
- **Shortcuts List:** Updated the help dialog with missing shortcuts (Paste, Properties, etc.) and clearer descriptions.
- **Time Announcements:** Time is now announced in natural language (e.g., "5 minutes remaining") instead of raw numbers.

### Fixed
- Fixed an issue where tracks might be announced twice or not at all depending on window focus.
- **Background File Announcement:** Filenames are now announced when changing tracks even if the player is minimized (respects verbosity settings).
- Improved stability of global media keys (Play/Pause/Next) to prevent crashes.

### Removed
- Removed the behavior where holding `Shift` bypassed delete confirmations (replaced with standard `Shift+Delete`).

## [1.0.0] - 2025-12-06

### Added
- **Initial Release:** First public release of AudioShelf, a precision-focused audiobook player designed for accessibility.
- **Smart Library:**
  - Automatic scanning of folders and single files.
  - Support for custom shelves (categories).
  - "Virtual Shelves" for Pinned, All Books, and Finished books.
- **Advanced Playback:**
  - Per-Book Memory: Remembers position, volume, and speed for every single book independently.
  - Smart Resume: Automatically rewinds a few seconds after long pauses.
  - A-B Loop: Ability to repeat specific sections of audio.
  - Variable Speed: Pitch-corrected speed control (0.5x to 3.0x).
  - 10-Band Equalizer: Built-in presets (Vocal Clarity, etc.).
- **Accessibility:**
  - Native integration with `nvdaControllerClient.dll` for high-performance speech feedback.
  - Full keyboard navigation support.
  - Global hotkeys for background control.
- **Tools:**
  - Portable Mode support for running from USB drives.
  - Sleep Timer with system shutdown/sleep options.
  - Metadata Export to `.json` files.
- **Technical:**
  - Built with Python 3.14 and wxPython.
  - Core playback engine based on `MPV`.
  - Installer (NSIS) and Portable Zip packages.