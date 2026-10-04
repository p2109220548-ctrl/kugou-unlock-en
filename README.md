<div align="center">

<img src="docs/logo.png" width="130" alt="shushuu"/>

# KuGou Unlocker

**Turn encrypted KuGou downloads into normal music files that play anywhere**

Three clicks · No command line · Beginner-friendly · Fully lossless · Fully offline

📄 **Full illustrated guide**: [`docs/KuGou Unlocker User Manual.pdf`](docs/KuGou%20Unlocker%20User%20Manual.pdf)

</div>

---

## What is this?

Songs you download from the KuGou desktop client are encrypted (file extensions `.kgm`, `.kgma`, `.vpr`, `.kgg`). They only play inside KuGoo — copy them to a car stereo, phone, USB stick, or lossless player and you get "format not supported".

This tool restores those encrypted songs into **normal FLAC / MP3 files** that play anywhere.

> **Never coded? Never touched a command line? That's completely fine — this tool was built for you.**
> Double-click the installer, wait for it to finish, then click three buttons. That's all.

- ✅ **Fully lossless**: the output is byte-for-byte the file you downloaded — zero quality loss
- ✅ **Three clicks**: open the app → pick files → hit start. That's all
- ✅ **No internet**: everything happens on your own computer; your music is never uploaded

---

## Beginner tutorial (no code involved)

### Step 0: check two things

- You're on Windows (Win10 / Win11) or macOS (🍎 marks the mac differences)
- The **KuGou desktop client is installed** (the "keys" for `.kgg` songs live inside it; not needed if you only process `.kgm` / `.kgma` / `.vpr` files)

### Step 1: download this tool

Click this direct link — [Download kugou-unlock-en.zip](https://github.com/p2109220548-ctrl/kugou-unlock-en/archive/refs/heads/main.zip)
(or on this page, click the green **`< > Code`** button → **Download ZIP**).

Then: right-click the ZIP → **Extract all** to somewhere easy to find (e.g. Desktop).

---

## Option 1: one-click script install (recommended · double-click only)

1. Open the extracted folder
2. **Windows**: double-click **`install_windows.bat`** and follow the 🪟 detailed steps below; **macOS**: double-click **`install_mac.command`** and follow the 🍎 detailed steps below
3. When it's done: **Windows** — double-click "KuGou Unlocker" on the desktop; **macOS** — double-click `start_kugou_unlocker.command` in the folder. The app opens!

> 🪟 **Windows detailed install steps**:
>
> 1. Double-click **`install_windows.bat`** — an installer window opens; you only ever press Enter and number keys, no commands to type
> 2. **Checking Python** (wizard step 1 of 3): the wizard looks for an existing Python automatically —
>    - It prints `[OK] Python found: …` — do nothing, it moves on by itself
>    - It prints "No Python 3.11+ detected" with a three-way menu: **just press Enter (or type 1)** = download the official Python and install it silently (about 1-2 minutes; small windows flashing briefly are normal); type **2** = "I already have Python", press Enter, then **drag your python.exe straight into the wizard window** and press Enter (the path fills itself in; below 3.11 it asks for confirmation); type **3** = skip installing Python for now, and re-run this installer whenever you're ready
> 3. **Installing components** (step 2 of 3): the two small packages needed for `.kgg` (pycryptodome / numpy) are installed automatically, once only
> 4. **Creating the shortcut** (step 3 of 3): a **"KuGou Unlocker"** icon appears on your desktop
> 5. When you see the green "**Installation complete!**", everything is installed
>
> 💡 If downloading Python automatically fails, the wizard opens the official download page; install from there (remember to tick `Add python.exe to PATH`) and double-click `install_windows.bat` once more.
> 💡 To launch later, you can also double-click **`start_kugou_unlocker.bat`** in the folder.

> 💡 **Did the one-click install fail?** No problem — install Python manually with the method below (just follow along, no command line needed), then double-click `install_windows.bat` once more.

<details>
<summary><font size="4"><b>Manual Python install reference</b></font></summary>

1. Open the download page: **https://www.python.org/downloads/** — it looks like this:

   ![Python download page](docs/python-download-page.png)

2. Click the **Python 3.x.x** text link (right after "Or get the standalone installer for" in the picture) — it always points to the **latest stable release**
   - ⚠️ **Do NOT** click the big yellow "Download Python install manager" button at the top — that's the new install manager, whose screens don't match this tutorial
   - Can't find the link? Open **https://www.python.org/downloads/latest/** — this official address always redirects to the latest stable release page; click "Windows installer (64-bit)" there
   - 🍎 **macOS**: on the same page pick the "**macOS 64-bit universal2 installer**" instead; mac installers have no "Add python.exe to PATH" option — nothing to tick, it just works
     - Requires **macOS 10.13 (High Sierra) or newer** — basically any Mac from 2017 onward; one installer covers both Intel and Apple Silicon (M1/M2/M3/M4…) chips, no need to pick a build
3. Run the installer and — **most important step** — tick **`Add python.exe to PATH`** at the bottom (🍎 macOS has no such step, just install)
4. Click **Install Now** and wait for it to finish

> To verify: press `Win + R`, type `cmd`, press Enter, then type `python --version` in the black window. Seeing a version number (e.g. `Python 3.12.5`) means success.
> 🍎 macOS: open Terminal (search in Launchpad) and run `python3 --version`.

</details>

> 🍎 **macOS detailed install steps**:
>
> 1. Double-click **`install_mac.command`** — a Terminal window opens and the install starts automatically. Type nothing, nothing to understand; just wait until the text stops scrolling (a minute or two) and it's done
> 2. If the first double-click says "**cannot verify the developer**" / "cannot be opened" (macOS blocks every unsigned file once — the file itself is fine), pick either fix:
>    - **Right-click** (or Control-click) the file → **Open** → click **Open** again in the dialog — allow it once and normal double-clicks work from then on
>    - Newer macOS (version 15 and up — check via  → About This Mac) may have no "Open" option, or still refuse after it: open **System Settings → Privacy & Security**, scroll down to the "install_mac.command was blocked" notice, click **Open Anyway** → enter your login password
> 3. If it says you **don't have permission to run it** (Permission denied), lift it like this:
>    - Open the **Terminal** app (search "Terminal" in Launchpad)
>    - Type `chmod +x` — note the **space after +x**
>    - **Drag `install_mac.command` straight into the Terminal window** (the full path fills itself in) and press Enter — no error message means success
>    - Go back and double-click again
> 4. When it's done, double-click **`start_kugou_unlocker.command`** in the folder to launch (the first launch may hit the same "unidentified developer" block — allow it once with the method in step 2)
>
> 💡 If the one-click install fails on macOS, use the "Manual Python install reference" above (🍎 marks apply), then double-click `install_mac.command` once more.

## Option 2: command-line install (advanced users)

Already comfortable with a terminal? Do it manually (same result as Option 1):

1. Install Python 3.11+ (see "Manual Python install reference" above)
2. Open a terminal inside the extracted folder (Windows: Shift + right-click on empty space → "Open PowerShell window here" / "Open in Terminal")
3. Run this and wait for "Successfully installed":

```
pip install -r requirements.txt
```

4. Launch the graphical interface (double-click `kugou_unlock_gui.py`, or run):

```
python kugou_unlock_gui.py
```

> 🍎 macOS: use `python3` instead of `python` in Terminal.
> 💡 Converting only `.kgm` / `.kgma` / `.vpr` files? You can skip `requirements.txt` entirely; it's needed for `.kgg`.
> 💡 Want to convert the unlocked FLAC / WAV songs into MP3? That's when you need [FFmpeg](https://ffmpeg.org/download.html); keeping the original format works without it.

---

### Step 2: three clicks and you're done

The window shows three steps — just follow the numbers:

1. **Choose files to convert** — first try "**Find my KuGou folder**": the tool locates your KuGou download directory automatically (it reads KuGou's own settings and scans the common locations on every drive, C:, D:, …). When found, a **file picker window** opens listing every encrypted song in that folder, **all pre-selected by default** — use "**Select all**" for everything, or hold `Ctrl` / `Shift` to pick just a few, then click OK. You can also use "Choose files…" for direct multi-select, or "Choose a folder…" which opens the same picker
   - 🍎 **macOS**: the KuGou mac client saves downloads into the **KuGou** subfolder of your Music folder. If it warns about a missing key database, use "Locate key database…", press `Cmd + Shift + G`, type `~/Library/Application Support`, and pick KGMusicV3.db from the KuGou folder there (no db? play each song once in the KuGou mac client first, then retry)
2. **Choose where to save** — "Choose output folder…" and point it where the converted songs should go (e.g. a new "My Music" folder on the desktop)
3. **Pick a format and hit "Start conversion"** — keep the default "Keep original format" (fully lossless) and watch the progress bar

When it finishes you'll get a summary — click "**Open output folder**" at the bottom to see your songs. Copy them to your car, phone, or player and enjoy.

---

## FAQ

**Q: Does conversion lose quality?**
A: No. "Conversion" here just removes the encryption wrapper — the music inside is untouched. Only choosing "MP3" output turns it into a lossy format.

**Q: Will I get MP3 or FLAC?**
A: It depends on the quality tier you picked in KuGou. "Lossless" downloads give FLAC; standard tier gives MP3. This tool cannot magically add quality.

**Q: Which encrypted formats are supported?**
A: `.kgm`, `.kgma`, `.vpr` and `.kgg` — all KuGou encryption formats. Normal music files (MP3/FLAC) don't need this tool and won't work with it.

**Q: Can I convert a whole folder at once?**
A: Yes — click "Choose a folder…", pick your KuGou download directory, and the picker window lists every song with all pre-selected by default. Click OK and go.

**Q: It says "ekey not found for this file"?**
A: Open KuGou and **play or re-download that song once**, then retry. The keys for `.kgg` are stored locally by KuGou while you listen.

**Q: It warns "KuGou key database not found"?**
A: The KuGou client isn't installed on this computer. It's required for `.kgg` files; `.kgm` / `.kgma` / `.vpr` work without it.

**Q: One particular file always fails to convert?**
A: The song is most likely an incomplete download, or was never played in KuGou (missing key). Play it once or re-download it in KuGou, then retry just that file; other songs are unaffected.

**Q: Conversion is slow / lots of files — how long will it take?**
A: A single song takes seconds; hundreds may take several minutes to a quarter of an hour, depending on your machine. The components installed by the one-click script speed it up, and you should keep the window open while converting.

**Q: I want MP3 output?**
A: Choose "MP3" in the interface — but install [FFmpeg](https://ffmpeg.org/download.html) first (restart the app afterwards). Most of the time "keep original format" is the best choice anyway.

**Q: The converted songs show no cover art or title on my phone / car stereo?**
A: Cover art and titles come from the tags inside the music file itself — some old songs simply don't have them. Use a mainstream player that reads tags; the file itself is fine.

**Q: Double-clicking `install_windows.bat` flashes and disappears / does nothing?**
A: Try **right-click → Run as administrator** first; if your antivirus pops a warning, see the next item.

**Q: Antivirus / Windows Defender flags or deletes the file?**
A: That's a false positive. This is an open-source script without a purchased code signature, and some antivirus products are sensitive to "auto-installer" scripts. Choose "trust / restore" for this tool in your antivirus, and make sure you downloaded it from the official page — never trust versions from other sources.

**Q: Double-clicking the `.py` file does nothing?**
A: Run `install_windows.bat` once first, then use the "KuGou Unlocker" desktop shortcut, or double-click `start_kugou_unlocker.bat`.

**Q: I installed Python but the installer says it can't find it?**
A: The script only checks PATH and common install locations (portable or Conda installs are not found). Type **2** at the three-way menu and drag your `python.exe` into the window to point at it.

**Q: The desktop shortcut wasn't created?**
A: No problem — double-click `start_kugou_unlocker.bat` in the folder to open the app, or run the one-click installer once more to create it.

**Q: Does converting need internet? Administrator rights?**
A: Conversion is **fully offline** — your music is never uploaded; only installing Python and the components needs internet. Administrator rights are normally **not** required (Python installs into your own user folder).

**Q: How do I uninstall this tool?**
A: It's portable — deleting the extracted folder and the desktop shortcut is the whole uninstall; nothing is written to the registry. The Python and components installed earlier stay where they are and don't affect anything else.

**Q: Can I use it on another computer?**
A: Yes — download, extract and run the one-click installer there. Note that `.kgg` keys follow KuGou: the new computer needs KuGou installed and those songs played once, or there is no key in the database.

**Q: Someone is selling this tool, or offering a "paid unlocked version"?**
A: This tool is **fully open-source and free — there is nothing to pay for**; any sale is an impersonation. Refuse it and report it on the official page, and never pay for unofficial "fixed" versions.

**Q: It says "Integrity check failed" at startup?**
A: Some program or document file has been modified or damaged (or the download was incomplete). Please download a fresh ZIP from the official page and extract it again — never trust unofficial "fixed" versions.

## Integrity protection (anti-tampering)

This software ships with built-in **integrity verification**: every program and document file carries a developer-issued checksum manifest (SHA-256 checksums + Ed25519 asymmetric signature — the signing private key is held by the developer only and never ships with the software), verified on every launch. **If any file was modified, replaced or deleted, the software refuses to run** and asks you to re-download from the official page.

**Why this layer of encryption?** For software safety — to prevent tampering and misuse:

- **Anti-tampering**: stops anyone from modifying the program, slipping anything else inside, and passing it off as this tool
- **Anti-misuse**: stops anyone from repackaging or renaming this tool, or even charging you money for it — a modified file fails verification and is refused on the spot

The bundled PDF manual likewise carries multiple layers of **watermarks** (attribution and source marks) for the same purpose — **anti-misuse and traceability**: if someone ever lifts the manual and passes it off as their own tutorial, the watermark proves where it came from. Watermarks do not affect reading.

**Important: this tool is fully open-source and free — there is nothing to pay for.**

- Downloading, installing, using and updating from the official page (this repository) costs **nothing** — no payment, no unlock codes, no membership
- The program contains **no** "paid edition", "unlock code" or "VIP group" of any kind
- **Anyone selling this tool or offering a "paid unlocked version" is an impersonator** — refuse it, and feel free to report it on the official page
- If you ever see the integrity-failure message, do not trust unofficial "fixed" versions

## Legal

- This tool is developed by [shushuu (鼠鼠shushuu)](https://github.com/p2109220548-ctrl): **no commercial use, personal use only**; keep the attribution and the LICENSE file when sharing.
- This tool is intended **only for local files you legitimately own** (downloaded with your own account), for personal playback and other fair uses.
- Decrypted output is **for private use only** — do not redistribute, share, or use commercially.
- The project contains no payment-bypass logic: `.kgg` keys come entirely from the key database already generated by your local KuGou client.
- This tool is **open-source and completely free — there is nothing to pay for**: anyone selling it, bundling it with charges, or offering "paid unlocks" is an impersonator, not the developer — refuse and report on the official page.
- By using this project you agree to comply with the laws of your jurisdiction and the platform's terms of service.

🔗 **Project home**: https://github.com/p2109220548-ctrl/kugou-unlock-en — if you find it useful, a Star ⭐ is appreciated; updates land here first.

## Advanced: command line (optional)

If you prefer the terminal, the core script works standalone:

```bash
python kugou_unlock.py "C:\KuGou\KugouMusic" decrypted/          # whole folder
python kugou_unlock.py src/ out/ --fmt mp3                        # transcode to MP3
python kugou_unlock.py src/ out/ --only kgm,kgg --procs 8         # filter formats
```

## Acknowledgements

Algorithms and constants come from these open-source projects — thanks to the community:
[unlock-music (um/cli)](https://git.unlock-music.dev/um/cli) · [Kugo-Music-Converter](https://github.com/skxxxkx666/Kugo-Music-Converter) · [libtakiyasha](https://github.com/nukemiko/libtakiyasha) · [kugou-audio-unlock](https://github.com/onavcn/kugou-audio-unlock)

## License

Developed by [shushuu (鼠鼠shushuu)](https://github.com/p2109220548-ctrl) under the [Personal-Use License](LICENSE):
**no commercial use — personal use only**. Non-profit sharing and classroom use are welcome; every copy must keep the "Developed by shushuu" attribution.
