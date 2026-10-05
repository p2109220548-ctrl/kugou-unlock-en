<div align="center">

<img src="docs/logo.png" width="130" alt="shushuu"/>

# KuGou Unlocker · shushuu

**Turn encrypted KuGou downloads into normal music files that play anywhere**

Three clicks · No command line · Fully lossless · Fully offline · Windows / macOS

*Developed by shushuu (鼠鼠shushuu) · Personal use only · No commercial use*

</div>

---

## What is this?

Songs you download from the KuGou desktop client are encrypted (file extensions `.kgm` / `.kgma` / `.vpr` / `.kgg`) and only play inside KuGoo — copy them to a car stereo, phone, USB stick or lossless player and you get "format not supported".

This tool restores those encrypted songs into **normal FLAC / MP3 files** that play anywhere.

| Feature | What it does |
|---|---|
| Decrypt & restore | `.kgm` / `.kgma` / `.vpr` / `.kgg` → FLAC / MP3 / WAV / OGG / M4A |
| Fully lossless | Byte-for-byte restore of the original audio stream — zero quality loss |
| One-click auto-locate | Finds KuGou's download folder and key database automatically |
| Graphical interface | Double-click to open, three clicks to convert; **select all or pick files** in a folder |
| Batch + parallel | Convert a whole folder at once, automatically multi-threaded |
| Optional transcoding (needs FFmpeg) | Also convert to MP3 320k and other formats |
| Privacy first | Runs fully locally — **nothing is ever uploaded** |

> 📄 A complete illustrated guide ships with the app: **`KuGou Unlocker User Manual.pdf`**.

---

## Installation

### Option 1: one-click script install (recommended · no command line)

1. Download the project ZIP: project page → green **`< > Code`** button → **Download ZIP**,
   or use this [direct download link](https://github.com/p2109220548-ctrl/kugou-unlock-en/archive/refs/heads/main.zip).
2. Right-click the ZIP → **Extract all** to somewhere easy to find (e.g. Desktop).
3. **Windows**: double-click **`install_windows.bat`** and wait — it automatically
   installs Python (using the official offline installer bundled with the package, no internet needed),
   installs two small components, and creates a **"KuGou Unlocker"** desktop shortcut.
   **macOS**: double-click **`install_mac.command`** (if macOS blocks it: right-click → Open → Open).
4. Then double-click **"KuGou Unlocker"** on the desktop (mac: `start_kugou_unlocker.command`
   in the folder) and the app opens.

> Double-clicking `install_windows.bat` requires no command-line knowledge:
> after double-clicking, type nothing and fill in nothing — the wizard runs every
> step itself. If the bundled installer is missing and the download fails, it opens the official
> download page; install from there and double-click `install_windows.bat` once more.

### Option 2: command-line install (advanced users)

Already comfortable with a terminal? Do it manually:

```bash
# 1. Install Python 3.11+ (python.org or your system package manager)
# 2. Clone or download this project, then inside the project folder:
pip install -r requirements.txt      # pycryptodome (needed for .kgg) + numpy (speed)
python kugou_unlock_gui.py           # open the graphical interface
```

> Converting only `.kgm` / `.kgma` / `.vpr` files? You can skip `requirements.txt` entirely;
> MP3 output additionally needs [FFmpeg](https://ffmpeg.org/download.html).

---

## Using the app (graphical interface)

Open the app and follow ①②③:

1. **Choose files to convert**
   - Click "**Find my KuGou folder**" — the tool locates your KuGou download directory automatically;
   - When found, a **file picker window** opens listing every encrypted song in that folder,
     **all pre-selected by default** — use "**Select all**" for everything, or hold
     `Ctrl` / `Shift` to pick just a few, then click OK;
   - You can also click "Choose files…" for direct multi-select, or "Choose a folder…"
     which opens the same picker.
2. **Choose where to save** — click "Choose output folder…" and point it where the
   converted songs should go.
3. **Pick a format and hit "Start conversion"** — keep "Keep original format" (fully lossless),
   watch the progress bar, then click "**Open output folder**" to see your songs.

> 🍎 macOS notes: the KuGou mac client saves downloads into the **KuGou** subfolder of your
> Music folder. If it warns about a missing key database, click "Locate key database…" and
> pick KGMusicV3.db (no db? play each song once in the KuGou mac client first, then retry).

**Command line (optional)**: a full CLI is also available:

```bash
python kugou_unlock.py "C:\KuGou\KugouMusic" decrypted/          # whole folder
python kugou_unlock.py src/ out/ --fmt mp3                        # transcode to MP3
python kugou_unlock.py src/ out/ --only kgm,kgg --procs 8         # filter formats
```

---

## FAQ

- **"ekey not found for this file"**: open KuGou and **play or re-download that song once** — the key is written to the local database — then retry.
- **"KuGou key database not found"**: the KuGou client is not installed on this computer. Required for `.kgg`; `.kgm` / `.kgma` / `.vpr` work without it.
- **Double-clicking `.py` / `.bat` does nothing**: run `install_windows.bat` once first; then use the desktop shortcut or `start_kugou_unlocker.bat`.
- **Want MP3**: choose MP3 output in the app (needs FFmpeg). Most of the time "keep original format" is the best choice.

More answers in `README.md` and `KuGou Unlocker User Manual.pdf`.

---

## Integrity protection (anti-tampering)

This software ships with built-in **integrity verification**: every program and document
file carries a developer-issued checksum manifest (SHA-256 checksums + Ed25519 asymmetric
signature; the signing private key is held by the developer only), verified on
every launch. **If any file was modified, replaced or deleted, the software refuses to
run** and asks you to re-download from the official page:

> https://github.com/p2109220548-ctrl/kugou-unlock-en

This prevents tampered copies from impersonating the original tool. If you ever see the
integrity-failure message, do not trust unofficial "fixed" versions.

---

## Legal

- **This tool is developed by [shushuu (鼠鼠shushuu)](https://github.com/p2109220548-ctrl)**: no commercial use, personal use only; keep the attribution and LICENSE when sharing.
- Only for **local files you legitimately own** (downloaded with your own account); decrypted output is for private playback — **do not redistribute, share, or use commercially**.
- The project contains no payment-bypass logic: `.kgg` keys come entirely from the key database already generated by your local KuGou client.
- By using this project you agree to comply with the laws of your jurisdiction and the platform's terms of service.
