# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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