#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KuGou Unlocker — graphical interface
====================================

A point-and-click interface for everyone: choose files -> choose where to
save -> hit "Start conversion". No command line, no code.

Just run this file (`python kugou_unlock_gui.py`). The decryption core lives
in kugou_unlock.py; this file only handles the interface.

IMPORTANT — personal use only: only process files you legitimately own.
Keep decrypted copies private; do not redistribute them.
"""

# Project signature (must be kept per the LICENSE terms):
# Author: shushuu (鼠鼠shushuu) — https://github.com/p2109220548-ctrl
# Personal non-commercial use only
__author__ = "shushuu (https://github.com/p2109220548-ctrl)"
__license__ = "Personal-NonCommercial-Use-Only (see LICENSE file)"

import ctypes
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import kugou_unlock as core
import kugou_integrity as integrity

# UI fonts: Segoe UI on Windows, Helvetica Neue on macOS (same look everywhere)
if sys.platform == 'darwin':
    UI_FONT, LOG_FONT = "Helvetica Neue", "Menlo"
elif os.name == 'nt':
    UI_FONT, LOG_FONT = "Segoe UI", "Consolas"
else:
    UI_FONT, LOG_FONT = "Helvetica", "DejaVu Sans Mono"


class App:
    """Main window: a three-step wizard plus a background conversion thread."""

    def __init__(self, root):
        self.root = root
        self.src = None          # selected source (list of files, or a folder)
        self.src_kind = None     # 'files' / 'folder'
        self.out_dir = tk.StringVar()
        self.fmt = tk.StringVar(value="auto")
        self.db_override = None  # manually chosen key database
        self.events = queue.Queue()
        self.running = False
        self._build()
        self._check_env_async()
        self._log("— " + integrity.AUTHOR_LINE)
        self._log("— " + integrity.DISCLAIMER)

    # ---------------- UI construction ----------------
    def _build(self):
        # Attribution stays in the window title (must be kept per the LICENSE)
        self.root.title("KuGou Unlocker · shushuu (鼠鼠shushuu)")
        # Window size adapts to the system DPI scale (no longer tiny at 125%/150% scaling)
        try:
            scale = self.root.winfo_fpixels("1i") / 96.0
        except Exception:
            scale = 1.0
        scale = max(1.0, min(scale, 3.0))
        self.root.geometry("%dx%d" % (int(680 * scale), int(700 * scale)))
        self.root.minsize(int(620 * scale), int(620 * scale))

        style = ttk.Style(self.root)
        for theme in (("aqua", "vista", "clam") if sys.platform == "darwin" else ("vista", "clam")):
            if theme in style.theme_names():
                style.theme_use(theme)
                break

        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        # ---- Title + About ----
        top = ttk.Frame(outer)
        top.pack(fill="x")
        ttk.Label(top, text="KuGou Unlocker",
                  font=(UI_FONT, 16, "bold")).pack(side="left")
        ttk.Button(top, text="About", command=self._show_about,
                   width=8).pack(side="right")

        # ---- Step 1: choose input ----
        box1 = ttk.LabelFrame(outer, text="① Choose files to convert", padding=10)
        box1.pack(fill="x", pady=(12, 6))
        row1 = ttk.Frame(box1)
        row1.pack(fill="x", pady=4)
        ttk.Button(row1, text="Find my KuGou folder", command=self._pick_auto).pack(side="left", padx=(0, 8))
        ttk.Button(row1, text="Choose files…", command=self._pick_files).pack(side="left", padx=(0, 8))
        ttk.Button(row1, text="Choose a folder…", command=self._pick_folder).pack(side="left")
        self.w_src_info = ttk.Label(box1, text="No files selected yet", foreground="#555555")
        self.w_src_info.pack(anchor="w")

        # ---- Step 2: output location ----
        box2 = ttk.LabelFrame(outer, text="② Choose where to save", padding=10)
        box2.pack(fill="x", pady=6)
        row2 = ttk.Frame(box2)
        row2.pack(fill="x", pady=4)
        ttk.Button(row2, text="Choose output folder…", command=self._pick_out).pack(side="left", padx=(0, 8))
        self.w_out_info = ttk.Label(row2, text="", foreground="#555555")
        self.w_out_info.pack(side="left", fill="x", expand=True)

        # ---- Step 3: output format ----
        box3 = ttk.LabelFrame(outer, text="③ Choose output format", padding=10)
        box3.pack(fill="x", pady=6)
        ttk.Radiobutton(box3, text="Keep original format (recommended · lossless)",
                        variable=self.fmt, value="auto").pack(anchor="w", pady=2)
        self.w_fmt_flac = ttk.Radiobutton(box3, text="FLAC (lossless)",
                                          variable=self.fmt, value="flac")
        self.w_fmt_flac.pack(anchor="w", pady=2)
        self.w_fmt_mp3 = ttk.Radiobutton(box3, text="MP3 (320k, lossy)",
                                         variable=self.fmt, value="mp3")
        self.w_fmt_mp3.pack(anchor="w", pady=2)
        self.w_fmt_wav = ttk.Radiobutton(box3, text="WAV (lossless)",
                                         variable=self.fmt, value="wav")
        self.w_fmt_wav.pack(anchor="w", pady=2)
        self.w_fmt_note = ttk.Label(box3, foreground="#777777", wraplength=int(600 * scale), justify="left",
                                    text="Tip: decryption is a lossless unwrap — quality is never "
                                         "reduced. Transcoding to another format needs FFmpeg installed.")
        self.w_fmt_note.pack(anchor="w", pady=(4, 0))

        # ---- Start button + progress ----
        self.w_start = ttk.Button(outer, text="Start conversion", command=self._start)
        self.w_start.pack(fill="x", pady=12, ipady=6)
        self.w_progress = ttk.Progressbar(outer, maximum=100)
        self.w_progress.pack(fill="x")
        self.w_status = ttk.Label(outer, text="")
        self.w_status.pack(anchor="w", pady=(4, 8))

        # ---- Log ----
        boxlog = ttk.LabelFrame(outer, text="Log", padding=8)
        boxlog.pack(fill="both", expand=True)
        logwrap = ttk.Frame(boxlog)
        logwrap.pack(fill="both", expand=True)
        self.w_log = tk.Text(logwrap, height=8, state="disabled", wrap="none",
                             font=(LOG_FONT, 9), background="#fafafa")
        scrollbar = ttk.Scrollbar(logwrap, command=self.w_log.yview)
        self.w_log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.w_log.pack(side="left", fill="both", expand=True)

        # ---- Footer: open output folder + key database status + legal note ----
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(8, 0))
        self.w_key_status = ttk.Label(bottom, text="Checking for the KuGou key database…",
                                      foreground="#555555")
        self.w_key_status.pack(side="left")
        ttk.Button(bottom, text="Locate key database…", command=self._pick_keydb,
                   width=22).pack(side="right")
        self.w_open_out = ttk.Button(bottom, text="Open output folder", command=self._open_out,
                                     width=22, state="disabled")
        self.w_open_out.pack(side="right", padx=(0, 8))
        ttk.Label(outer, text="Developed by shushuu (鼠鼠shushuu) · Personal use only · No commercial use · Do not redistribute",
                  foreground="#999999").pack(anchor="e", pady=(6, 0))

        self.root.after(100, self._poll_events)

    # ---------------- environment check (background thread) ----------------
    def _check_env_async(self):
        def work():
            has_ffmpeg = core.check_ffmpeg() is not None
            db = core.discover_kgg_db()
            key_count = 0
            if db:
                try:
                    key_count = len(core.decrypt_kgg_db(db))
                except Exception:
                    db = None
            self.events.put(("env", has_ffmpeg, db, key_count))
        threading.Thread(target=work, daemon=True).start()

    def _apply_env(self, has_ffmpeg, db, key_count):
        self.has_ffmpeg = has_ffmpeg
        self.key_db = db
        state = "normal" if has_ffmpeg else "disabled"
        for w in (self.w_fmt_flac, self.w_fmt_mp3, self.w_fmt_wav):
            w.config(state=state)
        if not has_ffmpeg:
            self.w_fmt_note.config(text="FFmpeg not found — transcoding disabled "
                                        "(\"keep original format\" still works)")
        if db:
            self.w_key_status.config(text="✓ KuGou key database found (%d) — .kgg ready to convert"
                                     % key_count, foreground="#1a7f37")
        else:
            self.w_key_status.config(text="⚠ KuGou key database not found: converting .kgg "
                                          "needs the KuGou client installed", foreground="#b35900")

    # ---------------- pickers ----------------
    def _refresh_src_info(self):
        if self.src is None:
            self.w_src_info.config(text="No files selected yet")
        elif self.src_kind == "folder":
            self.w_src_info.config(text="Folder selected: %s" % self.src)
        else:
            self.w_src_info.config(text="%d encrypted audio file(s) selected" % len(self.src))

    def _pick_auto(self):
        """One-click auto-discovery of the KuGou download folder
        (reads the KuGou config, then scans default locations on every drive)."""
        self.w_src_info.config(text="…")
        self.root.update()
        found = core.discover_kugou_music_dir()
        if found:
            # Folder found — open the picker (all files pre-selected by default)
            self._show_file_picker(found)
        else:
            self.w_src_info.config(text="Not found automatically — please pick the KuGou "
                                        "download folder manually (e.g. C:\\KuGou\\KugouMusic)",
                                   foreground="#b35900")

    def _open_out(self):
        """Open the output folder (enabled once a conversion finished)."""
        out = self.out_dir.get()
        if out and os.path.isdir(out):
            try:
                if os.name == 'nt':
                    os.startfile(out)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', out])
                else:
                    subprocess.Popen(['xdg-open', out])
            except Exception:
                pass

    def _pick_files(self):
        types = [("KuGou encrypted audio", "*.kgm *.kgma *.vpr *.kgg"), ("All files", "*.*")]
        paths = filedialog.askopenfilenames(filetypes=types)
        if paths:
            self.src = list(paths)
            self.src_kind = "files"
            self._refresh_src_info()

    def _pick_folder(self):
        path = filedialog.askdirectory()
        if path:
            # After picking a folder, open the picker so the user can select
            # which files inside it should be converted (Select all available).
            self._show_file_picker(os.path.normpath(path))

    def _pick_out(self):
        path = filedialog.askdirectory()
        if path:
            self.out_dir.set(os.path.normpath(path))
            self.w_out_info.config(text=self.out_dir.get())

    def _pick_keydb(self):
        path = filedialog.askopenfilename(filetypes=[("KGMusicV3.db", "*.db"), ("All files", "*.*")])
        if path:
            self.db_override = path
            try:
                n = len(core.decrypt_kgg_db(path))
                self.key_db = path
                self.w_key_status.config(text="✓ KuGou key database found (%d) — .kgg ready" % n,
                                         foreground="#1a7f37")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ---------------- in-folder file picker ----------------
    def _show_file_picker(self, folder):
        """After a folder is chosen, list every encrypted audio file inside it
        for selection (all pre-selected by default; Select all available)."""
        files = []
        try:
            for name in sorted(os.listdir(folder)):
                if os.path.splitext(name)[1].lower().lstrip('.') in core.AUDIO_EXTS:
                    full = os.path.join(folder, name)
                    if os.path.isfile(full):
                        try:
                            size_mb = os.path.getsize(full) / 1048576.0
                            label = "%s   (%.1f MB)" % (name, size_mb)
                        except OSError:
                            label = name
                        files.append((full, label))
        except OSError:
            pass
        if not files:
            messagebox.showinfo("KuGou Unlocker",
                                "No encrypted audio files in this folder "
                                "(.kgm / .kgma / .vpr / .kgg)")
            return

        try:
            scale = self.root.winfo_fpixels("1i") / 96.0
        except Exception:
            scale = 1.0
        scale = max(1.0, min(scale, 3.0))

        dlg = tk.Toplevel(self.root)
        dlg.title("Choose files to convert")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(True, True)
        dlg.geometry("%dx%d+%d+%d" % (
            int(620 * scale), int(460 * scale),
            self.root.winfo_x() + 30, self.root.winfo_y() + 40))

        frame = ttk.Frame(dlg, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Found %d encrypted audio file(s) in the selected folder. "
                              "Pick the ones to convert (Ctrl / Shift for multi-select):"
                  % len(files),
                  wraplength=int(580 * scale), justify="left").pack(anchor="w", pady=(0, 6))

        listwrap = ttk.Frame(frame)
        listwrap.pack(fill="both", expand=True)
        lb = tk.Listbox(listwrap, selectmode="extended", font=(UI_FONT, 10),
                        activestyle="dotnone", exportselection=False)
        sb = ttk.Scrollbar(listwrap, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)
        for _full, label in files:
            lb.insert("end", label)
        lb.selection_set(0, "end")  # everything pre-selected

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(8, 0))

        def select_all(_evt=None):
            lb.selection_set(0, "end")
            lb.see(0)

        def clear_sel():
            lb.selection_clear(0, "end")

        def confirm(_evt=None):
            sel = lb.curselection()
            if not sel:
                return
            self.src = [files[i][0] for i in sel]
            self.src_kind = "files"
            self.w_src_info.config(
                text="%d / %d file(s) selected (from: %s)" % (len(sel), len(files), folder),
                foreground="#1a7f37")
            dlg.destroy()

        ttk.Button(btns, text="Select all", command=select_all).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=clear_sel).pack(side="left")
        ttk.Button(btns, text="OK", command=confirm, style="Accent.TButton").pack(side="right")
        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="right", padx=(0, 8))

        lb.bind("<Double-Button-1>", confirm)
        dlg.bind("<Return>", confirm)
        dlg.bind("<Escape>", lambda _e: dlg.destroy())
        lb.focus_set()

    # ---------------- about ----------------
    def _show_about(self):
        """About dialog: official logo, version, attribution, license & disclaimer."""
        top = tk.Toplevel(self.root)
        top.title("About KuGou Unlocker")
        top.transient(self.root)
        top.resizable(False, False)
        top.grab_set()
        pad = ttk.Frame(top, padding=16)
        pad.pack(fill="both", expand=True)
        # Official logo photo (docs/logo.png — protected by the integrity check)
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(core.__file__)),
                                     "docs", "logo.png")
            photo = tk.PhotoImage(file=logo_path)
            factor = max(1, photo.width() // 150)
            photo = photo.subsample(factor, factor)
            tk.Label(pad, image=photo, background="#ffffff").pack()
            top._logo_ref = photo  # prevent garbage collection
        except Exception:
            pass
        ttk.Label(pad, text=integrity.banner(core.__version__),
                  justify="center", font=(UI_FONT, 9)).pack(pady=(8, 4))
        ttk.Button(pad, text="OK", command=top.destroy).pack(pady=(4, 0))
        top.update_idletasks()
        top.geometry("+%d+%d" % (self.root.winfo_x() + 60, self.root.winfo_y() + 60))

    # ---------------- conversion ----------------
    def _log(self, line):
        self.w_log.config(state="normal")
        self.w_log.insert("end", line + "\n")
        self.w_log.see("end")
        self.w_log.config(state="disabled")

    def _start(self):
        if self.running:
            return
        if not self.src:
            messagebox.showwarning("KuGou Unlocker", "Please choose files or a folder first")
            return
        if not self.out_dir.get():
            messagebox.showwarning("KuGou Unlocker", "Please choose an output folder first")
            return
        self.running = True
        self.w_start.config(state="disabled")
        self.w_progress.config(value=0)
        src, out, fmt = self.src, self.out_dir.get(), self.fmt.get()
        db = self.db_override or self.key_db
        self._log("— Starting conversion…")

        def work():
            try:
                def progress(done, total, path, status, info):
                    self.events.put(("progress", done, total, path, status, info))
                ok, fail = core.batch_convert(src, out, target_fmt=fmt, db_path=db,
                                              progress_cb=progress)
                self.events.put(("done", ok, fail, out))
            except Exception as e:
                self.events.put(("error", str(e)))

        threading.Thread(target=work, daemon=True).start()

    # ---------------- event polling (UI thread) ----------------
    def _poll_events(self):
        try:
            while True:
                evt = self.events.get_nowait()
                kind = evt[0]
                if kind == "env":
                    self._apply_env(evt[1], evt[2], evt[3])
                elif kind == "progress":
                    _, done, total, path, status, info = evt
                    if total:
                        self.w_progress.config(value=100.0 * done / total)
                        self.w_status.config(text="Converting… %d/%d" % (done, total))
                    name = os.path.basename(path)
                    mark = "✓" if status == "ok" else "✗"
                    self._log("%s %s → %s" % (mark, name, info))
                elif kind == "done":
                    _, ok, fail, out = evt
                    if fail == 0:
                        self.w_progress.config(value=100)
                    self.w_status.config(text="Finished: %d succeeded, %d failed" % (ok, fail))
                    self._log("— Finished: %d succeeded, %d failed" % (ok, fail))
                    self.running = False
                    self.w_start.config(state="normal")
                    # Enable "Open output folder" after a conversion — no yes/no
                    # dialogs that are easy to misclick.
                    self.w_open_out.config(state="normal")
                    if fail == 0:
                        messagebox.showinfo("Finished", "Conversion finished!\n"
                                             "%d succeeded, %d failed.\nClick \"Open output folder\" "
                                             "below to see your songs.\nFiles saved to:\n%s"
                                             % (ok, fail, out))
                    else:
                        messagebox.showwarning("Finished", "Conversion failed: %d file(s) could "
                                               "not be converted.\nSee the log below for details."
                                               % fail)
                elif kind == "error":
                    self.running = False
                    self.w_start.config(state="normal")
                    messagebox.showerror("Error", evt[1])
        except queue.Empty:
            pass
        self.root.after(120, self._poll_events)


def _enable_windows_high_dpi():
    """Declare DPI awareness (Windows): keeps the UI crisp and correctly laid
    out under high-DPI scaling. Must be called before creating tk.Tk().

    Without this, Windows bitmap-stretches the whole window on scaled displays,
    which makes the interface blurry and offsets the layout.
    """
    if os.name != "nt":
        return
    try:  # Win10 1703+: Per-Monitor V2, correct even with mixed-DPI monitors
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:  # Win 8.1+ fallback
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:  # older systems fallback
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _show_integrity_error(problems):
    """Integrity verification failed: show a dialog and exit, never the main UI."""
    text = integrity.fail_text(problems)
    try:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("KuGou Unlocker · Integrity check failed", text)
        r.destroy()
    except Exception:
        pass
    sys.exit(2)


def main():
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # Tamper protection: refuse to start when program/docs/license were modified
    ok, problems = integrity.verify()
    if not ok:
        _show_integrity_error(problems)
        return
    _enable_windows_high_dpi()
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
