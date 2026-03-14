<div align="center">
  <img src="AudioShelf.png" alt="AudioShelf Logo" width="120">
  <h1>🎧 AudioShelf</h1>

  <p>
    <img src="https://img.shields.io/badge/Accessibility-NVDA%20%26%20JAWS-green.svg" alt="Accessibility">
    <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform">
    <img src="https://img.shields.io/github/downloads/M-Rajabi-dev/AudioShelf/total?label=Downloads&color=success" alt="Downloads">
    <img src="https://img.shields.io/github/license/M-Rajabi-dev/AudioShelf?color=blue" alt="License">
  </p>

  <p>

  <b>The ultimate audiobook player that treats your books like books, not just files.</b>
  </p>
</div>

---

AudioShelf is a specialized desktop application designed for audiobook enthusiasts who need precision, organization, and accessibility. Unlike generic media players, AudioShelf understands that every book is a unique journey with its own progress, history, and settings.

---

## 🌟 Why AudioShelf?

Most players treat audio files equally. AudioShelf treats every book as a distinct entity.

### 📚 Book-Centric Management
*   **Independent Progress:** Remembers exactly where you left off in *every single book*, down to the second.
*   **Smart Metadata:** Automatically imports and manages book details, chapters, and file structures.
*   **Metadata Persistence:** Saves your progress, bookmarks, and playback state directly alongside the book files (`.json`). Move your library to another PC, and your listening history moves with it.
*   **Dedicated History:** Keep track of your recently played books in a dedicated history tab.

### 🎛️ Professional Playback Control
*   **Smart Resume:** Intelligently rewinds a few seconds after long pauses so you never lose the context of the story.
*   **A-B Loop:** Repeat specific sections of audio effortlessly—perfect for language learners.
*   **Variable Speed:** Adjust playback speed without distorting the narrator's voice (Pitch-corrected).
*   **10-Band Equalizer:** Custom audio presets (e.g., Vocal Clarity) to enhance different narrators' voices.

### 🗣️ Accessibility First
* **Screen Reader Optimized:** Built from the ground up with native support for screen readers (including **NVDA** and **JAWS**) for precise semantic announcements.
*   **Keyboard-Driven:** Every single feature is accessible via customizable hotkeys for a mouse-free experience.

### 🛠️ Powerful Tools
*   **Auto-Updater:** Automatically checks for and installs the latest updates at startup.
*   **Sleep Timer:** Configurable timer with system actions (Shutdown/Sleep/Hibernate).
*   **Portable Mode:** Run AudioShelf directly from a USB drive without installation.
*   **Audiobookshelf Import:** Connect to your self-hosted Audiobookshelf server with an API key and stream books directly, with optional per-book local download from the context menu.
*   **Audiobookshelf Progress Sync:** AudioShelf can pull your latest position from Audiobookshelf when opening a streamed book and push listening progress back while you play.

---

## ⌨️ Essential Hotkeys

AudioShelf is designed to be keyboard-centric. Press `F1` in the app for the full list.

| Action | Shortcut |
| :--- | :--- |
| **Play / Pause** | `Space` |
| **Stop (Reset)** | `Shift + Space` |
| **Rewind / Forward** | `Left` / `Right` Arrow |
| **Chapter Navigation** | `Alt + PageUp` / `Alt + PageDown` |
| **Chapter List** | `Alt + C` |
| **Volume Control** | `Up` / `Down` Arrow |
| **Speed Control** | `J` (Faster) / `H` (Slower) / `K` (Reset) |
| **Quick Bookmark** | `B` |
| **Sleep Timer** | `T` |
| **Play Last Book** | `Ctrl + L` |
| **Search Library** | `Ctrl + F` |

---

## 📥 Download & Installation

Get the latest version directly using the links below:

### 💿 Option 1: Installer (Recommended)
**[Click here to Download Setup (.exe)](https://AudioShelf.github.io/setup)**
* Run the installer to set up AudioShelf on your PC.

### 🎒 Option 2: Portable (No Install)
**[Click here to Download Portable (.zip)](https://AudioShelf.github.io/portable)**
* Extract the zip file anywhere (e.g., on a USB stick) and run `AudioShelf.exe`.



### 📦 Option 3: Winget (Best for Updates)
Install securely via Windows Package Manager. Just open Terminal (CMD or PowerShell) and type:

```powershell
winget install AudioShelf
```
> *Benefit: You can easily update later by typing `winget upgrade AudioShelf`.*

> *View full version history on the [Releases Page](https://github.com/M-Rajabi-dev/AudioShelf/releases).*

---

## 🛠️ For Developers (Running from Source)

AudioShelf is built using **Python 3.14**, but supports Python 3.10+.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/M-Rajabi-dev/AudioShelf.git
   cd AudioShelf
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python AudioShelf.py
   ```

4. **Run the test suite:**
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```

---

## ❤️ Support & Contributing

AudioShelf is a free and open-source project developed with passion.

*   **Star** this repository on GitHub ⭐
*   **Donate** via the in-app support menu.
*   **Contribute:** Pull Requests are welcome!

---

## 🌍 Translation & Localization

AudioShelf aims to be accessible to everyone. We are currently looking for contributors to help translate the app into more languages!

If you would like to help:
1. Download the template: [`locale/AudioShelf.pot`](./locale/AudioShelf.pot).
2. Translate it using [Poedit](https://poedit.net/).
3. Submit a Pull Request or contact the maintainer.

---

## 📜 License

Copyright (c) 2025-2026 Mehdi Rajabi.
AudioShelf is Free Software: You can use, study, share and improve it at your will.
Specifically you can redistribute and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

---

## Code Signing Policy

This project uses free code signing provided by [SignPath.io](https://signpath.io) and a certificate issued by [SignPath Foundation](https://signpath.org).

### Team Roles and Responsibilities
* **Maintainer & Reviewer:** [Mehdi Rajabi](https://github.com/M-Rajabi-dev) (Owner)
* **Approver:** [Mehdi Rajabi](https://github.com/M-Rajabi-dev) (Owner)

### Privacy Policy
This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.
