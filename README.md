<div align="center">
  <img src="AudioShelf.png" alt="AudioShelf Logo" width="120">
  <h1>🎧 AudioShelf</h1>
</div>

> **The ultimate audiobook player that treats your books like books, not just files.**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Accessibility](https://img.shields.io/badge/Accessibility-Native%20NVDA-green.svg)
![Python](https://img.shields.io/badge/Python-3.14-yellow.svg)

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

### ♿ Accessibility First
*   **Screen Reader Optimized:** Built from the ground up with native `nvdaControllerClient.dll` integration for precise semantic announcements.
*   **Keyboard-Driven:** Every single feature is accessible via customizable hotkeys for a mouse-free experience.

### 🛠️ Powerful Tools
*   **Auto-Updater:** Automatically checks for and installs the latest updates at startup.
*   **Sleep Timer:** Configurable timer with system actions (Shutdown/Sleep/Hibernate).
*   **Portable Mode:** Run AudioShelf directly from a USB drive without installation.

---

## ⌨️ Essential Hotkeys

AudioShelf is designed to be keyboard-centric. Press `F1` in the app for the full list.

| Action | Shortcut |
| :--- | :--- |
| **Play / Pause** | `Space` |
| **Stop (Reset)** | `Shift + Space` |
| **Rewind / Forward** | `Left` / `Right` Arrow |
| **Volume Control** | `Up` / `Down` Arrow |
| **Speed Control** | `J` (Faster) / `H` (Slower) / `K` (Reset) |
| **Quick Bookmark** | `B` |
| **Sleep Timer** | `T` |
| **Play Last Book** | `Ctrl + L` |
| **Search Library** | `Ctrl + F` |

---

## 📥 Download & Installation

Get the latest version from the [Releases Page](https://github.com/M-Rajabi-Dev/AudioShelf/releases).
### Option 1: Installer (Recommended)
*   Download the file ending in **`-Setup.exe`** (e.g., `AudioShelf-1.0.0-Win64-Setup.exe`).
*   Run the installer. It will create a shortcut on your desktop and Start Menu.

### Option 2: Portable
*   Download the file ending in **`-Portable.zip`** (e.g., `AudioShelf-1.0.0-Win64-Portable.zip`).
*   Extract the zip file anywhere (e.g., on a USB stick).
*   Run `AudioShelf.exe` inside the folder. No installation required.

---

## 🛠️ For Developers (Running from Source)

AudioShelf is built using **Python 3.14**, but supports Python 3.10+.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/M-Rajabi-Dev/AudioShelf.git
   cd AudioShelf
   ```

2. **Install dependencies:**
   ```bash
   pip install wxpython python-mpv tinytag
   ```

3. **External Dependencies:**
   * Ensure `libmpv-2.dll` is placed in the root directory.
   * Ensure `nvdaControllerClient.dll` is available for screen reader support.

4. **Run the application:**
   ```bash
   python AudioShelf.py
   ```

---

## 🤖 Development Philosophy

AudioShelf is an example of **AI-Assisted Development**. 
The project was conceptualized to solve specific accessibility gaps in existing players. Modern AI tools were utilized to accelerate the coding process, allowing the focus to remain on user experience and solving edge cases for the visually impaired community. We believe in transparency and leveraging technology to bridge accessibility gaps.

---

## ❤️ Support & Contributing

AudioShelf is a free and open-source project developed with passion.

*   **Star** this repository on GitHub ⭐
*   **Donate** via the in-app support menu.
*   **Contribute:** Pull Requests are welcome!

---

## 📜 License

Copyright (c) 2025 Mehdi Rajabi.
Distributed under the MIT License. See `LICENSE` for more information.
