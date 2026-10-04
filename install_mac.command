#!/bin/bash
# ============================================================
#  KuGou Unlocker — macOS one-click installer (double-click to run)
#  Author: shushuu (鼠鼠shushuu) — https://github.com/p2109220548-ctrl
#  Personal non-commercial use only · Do not redistribute
# ============================================================
# Double-click this file — no commands to type. It will:
#   1) detect Python 3.11+ (opens the official download page if missing)
#   2) install the required components
#   3) generate the double-click launcher start_kugou_unlocker.command
#
# If macOS says the file "cannot be opened because it is from an unidentified
# developer": right-click this file -> Open -> Open.
# If it says you lack permission: open Terminal, drag this file in, press
# Enter after prefixing it with chmod +x.

cd "$(dirname "$0")" || exit 1

echo "============================================================"
echo "   KuGou Unlocker · One-click Installer (macOS)"
echo "   Author: shushuu  |  Personal use only - no commercial use"
echo "============================================================"

# ---------- Step 1/3: check Python 3.11+ ----------
echo ""
echo ">>> Step 1 / 3: checking Python"
PY=""
for c in python3 python3.13 python3.12 python3.11 python; do
    if command -v "$c" >/dev/null 2>&1; then
        v=$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)
        major="${v%%.*}"; minor="${v#*.}"
        if [ "${major:-0}" -ge 3 ] && [ "${minor:-0}" -ge 11 ] 2>/dev/null; then PY="$c"; break; fi
    fi
done

if [ -z "$PY" ]; then
    echo "    [!]  No Python 3.11+ detected — opening the official download page…"
    echo "    Please install the 'macOS 64-bit universal2 installer' (next-next-finish),"
    echo "    then double-click this file again."
    open "https://www.python.org/downloads/latest/"
    exit 1
fi
echo "    [OK] Python found: $PY"

# ---------- Step 2/3: install components ----------
echo ""
echo ">>> Step 2 / 3: installing components (pycryptodome / numpy)"
if "$PY" -m pip install --user --disable-pip-version-check --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple pycryptodome numpy; then
    echo "    [OK] Components installed (Tsinghua mirror)"
elif "$PY" -m pip install --user --disable-pip-version-check --quiet pycryptodome numpy; then
    echo "    [OK] Components installed (official index)"
else
    echo "    [!]  Automatic component install failed (this does NOT affect .kgm/.kgma files)."
    echo "    If converting .kgg fails later, run in Terminal: $PY -m pip install --user pycryptodome numpy"
fi

# ---------- Step 3/3: generate the launcher ----------
echo ""
echo ">>> Step 3 / 3: generating the launcher start_kugou_unlocker.command"
PY_ABS="$($PY -c 'import sys;print(sys.executable)')"
cat > "start_kugou_unlocker.command" <<LAUNCHER
#!/bin/bash
# KuGou Unlocker launcher · by shushuu · personal use only · no commercial use
cd "\$(dirname "\$0")" || exit 1
exec "$PY_ABS" kugou_unlock_gui.py
LAUNCHER
chmod +x "start_kugou_unlocker.command"
echo "    [OK] Launcher created"

echo ""
echo "============================================================"
echo "   Installation complete!"
echo "   Double-click start_kugou_unlocker.command in this folder:"
echo "     1. Click 'Find my KuGou folder' (or pick files/folder manually)"
echo "     2. Choose where to save  3. Click 'Start conversion'"
echo "   Full illustrated guide: 'KuGou Unlocker User Manual.pdf' or README.md"
echo "   -- by shushuu (shushuu) · Personal use only · No commercial use --"
echo "============================================================"
