# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-04

### 🎉 Initial Release
First public release of AudioShelf! A precision-focused audiobook player designed for accessibility and power users.

### ✨ Key Features
- **Smart Library:** 
  - Automatic scanning of folders and single files.
  - Support for custom shelves (categories).
  - "Virtual Shelves" for Pinned, All Books, and Finished books.
- **Advanced Playback:**
  - **Per-Book Memory:** Remembers position, volume, and speed for every single book independently.
  - **Smart Resume:** Automatically rewinds a few seconds after long pauses.
  - **A-B Loop:** Ability to repeat specific sections of audio.
  - **Variable Speed:** Pitch-corrected speed control (0.5x to 3.0x).
  - **10-Band Equalizer:** With built-in presets (Vocal Clarity, etc.).
- **Accessibility:**
  - Native integration with `nvdaControllerClient.dll` for high-performance speech feedback.
  - Full keyboard navigation support.
  - Global hotkeys for background control.
- **Tools:**
  - **Portable Mode:** Full support for running from USB drives (data saved locally).
  - **Sleep Timer:** Configurable timer with system shutdown/sleep options.
  - **Metadata Export:** Save progress and bookmarks to `.json` files alongside media.
### 🛠 Technical
- Built with Python 3.14 and wxPython.
- Uses `MPV` as the core playback engine for broad format support.
- Includes both Setup Installer (NSIS) and Portable Zip packages.
