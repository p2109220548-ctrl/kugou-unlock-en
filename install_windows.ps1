# ============================================================
#  KuGou Unlocker — Windows one-click installer (launched by install_windows.bat)
#  Author: shushuu (鼠鼠shushuu) — https://github.com/p2109220548-ctrl
#  Personal non-commercial use only · Do not redistribute
# ============================================================
# Double-clicking install_windows.bat runs this script — no commands to type.
# It will: 1) detect / silently install Python  2) install the required
# components  3) create a desktop shortcut.

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Write-Step($msg)  { Write-Host "" ; Write-Host ">>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }

Write-Host "============================================================"
Write-Host "   KuGou Unlocker · One-click Installer (Windows)"
Write-Host "   Author: shushuu  |  Personal use only - no commercial use"
Write-Host "============================================================"

# ------------------------------------------------------------
# Step 1/3: find a usable Python 3.11+
# ------------------------------------------------------------
function Find-Python {
    $candidates = @()
    foreach ($name in @("py", "python3", "python")) {
        try { $src = (Get-Command $name -ErrorAction SilentlyContinue).Source
              if ($src) { $candidates += $src } } catch {}
    }
    foreach ($p in @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "C:\Program Files\Python314\python.exe",
        "C:\Program Files\Python313\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe"
    )) { if (Test-Path $p) { $candidates += $p } }

    foreach ($c in $candidates) {
        try {
            $ver = (& $c -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null | Out-String).Trim()
            if ($ver -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 11) { return $c }
        } catch {}
    }
    return $null
}

# Fully automatic Python install: prefers the official offline installer bundled
# with this package (no internet needed); falls back to official source + mirrors
# if the bundled file is missing. Returns the python path on success.
function Install-PythonAuto {
    $installer = Join-Path $env:TEMP "python-3.14.8-amd64.exe"
    $ok = $false
    # First choice: the offline installer shipped inside this package
    $localInstaller = Join-Path $scriptDir "python-3.14.8-amd64.exe"
    if (Test-Path $localInstaller) {
        Write-Ok "Found the bundled Python offline installer (no internet needed)"
        Copy-Item $localInstaller $installer -Force
        $ok = $true
    } else {
        # Bundled installer missing: official source first, then mirrors
        $urls = @(
            "https://www.python.org/ftp/python/3.14.8/python-3.14.8-amd64.exe",
            "https://registry.npmmirror.com/-/binary/python/3.14.8/python-3.14.8-amd64.exe",
            "https://mirrors.huaweicloud.com/python/3.14.8/python-3.14.8-amd64.exe"
        )
        foreach ($u in $urls) {
            try {
                Write-Host "    Downloading from $u …"
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -Uri $u -OutFile $installer -UseBasicParsing
                if ((Get-Item $installer).Length -gt 10MB) { $ok = $true; break }
            } catch { Write-Warn2 "Download failed from this mirror, trying the next one…" }
        }
    }
    if (-not $ok) {
        Write-Warn2 "Automatic download failed. Opening the official download page instead:"
        Write-Warn2 "  1) Download 'Windows installer (64-bit)' and run it"
        Write-Warn2 "  2) Tick 'Add python.exe to PATH' at the bottom of the installer"
        Write-Warn2 "  3) Then double-click install_windows.bat again"
        Start-Process "https://www.python.org/downloads/latest/"
        exit 1
    }
    Write-Ok "Silently installing Python 3.14.8 (a window may flash briefly — normal, 1-2 minutes)…"
    $proc = Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1" -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Warn2 "Silent install did not finish (exit code $($proc.ExitCode)). Opening the installer for a manual run:"
        Write-Warn2 "  Click through it, tick 'Add python.exe to PATH', then double-click install_windows.bat again."
        Start-Process $installer
        exit 1
    }
    # Refresh PATH for the current session so the fresh Python is visible
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $found = Find-Python
    if (-not $found) { $found = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" }
    if (-not (Test-Path $found)) {
        Write-Warn2 "Python was installed but not found automatically. Please double-click install_windows.bat once more."
        exit 1
    }
    Write-Ok "Python installed: $found"
    return $found
}

Write-Step "Step 1 / 3: checking Python"
$py = Find-Python
if ($py) {
    Write-Ok "Python found: $py"
} else {
    Write-Warn2 "No Python 3.11+ detected."
    Write-Host ""
    Write-Host "    Already have Python? You don't need another copy. Choose:" -ForegroundColor Yellow
    Write-Host "      Enter / 1 = install the official Python bundled with this package (recommended · offline · hands-off)"
    Write-Host "      2 = I already have Python — point me to its python.exe"
    Write-Host "      3 = Skip installing Python (stop here; re-run this installer later)"
    Write-Host ""
    $choice = (Read-Host "    Type a number and press Enter").Trim()
    if ($choice -eq "3") {
        Write-Warn2 "Skipped the Python install; components and shortcut were not set up this time."
        Write-Warn2 "Whenever Python 3.11+ is available, just double-click install_windows.bat again."
        exit 0
    }
    if ($choice -eq "2") {
        $py = $null
        foreach ($attempt in 1..3) {
            $in = (Read-Host "    Enter the full path to python.exe (dragging the file into this window works too)").Trim()
            $in = $in.Trim('"').Trim("'")
            if (-not $in) {
                Write-Warn2 "Empty path, try again (attempt $attempt / 3)"
                continue
            }
            if (-not (Test-Path $in)) {
                Write-Warn2 "Path does not exist: $in (attempt $attempt / 3)"
                continue
            }
            $ver = ""
            try { $ver = (& $in -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null | Out-String).Trim() } catch {}
            if ($ver -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 11) {
                $py = $in
                Write-Ok "Using your Python ($ver): $in"
                break
            }
            $yes = Read-Host "    Detected version '$ver' (this tool recommends 3.11+; older may not run). Use it anyway? [y/N]"
            if ($yes -match '^[Yy]') {
                $py = $in
                Write-Ok "Using it as you chose: $in"
                break
            }
            Write-Warn2 "Try another path (attempt $attempt / 3)"
        }
        if (-not $py) {
            Write-Warn2 "No usable Python was provided. Double-click install_windows.bat to try again."
            exit 1
        }
    } else {
        $py = Install-PythonAuto
        if (-not $py) { exit 1 }
    }
}

# ------------------------------------------------------------
# Step 2/3: install the two required components
# ------------------------------------------------------------
Write-Step "Step 2 / 3: installing components (pycryptodome / numpy)"
Write-Host "    (pycryptodome is needed for .kgg files; numpy makes conversions much faster.)"
& $py -m pip install --disable-pip-version-check --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple pycryptodome numpy | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "Components installed (Tsinghua mirror)"
} else {
    Write-Warn2 "Mirror unavailable, retrying with the official index…"
    & $py -m pip install --disable-pip-version-check --quiet pycryptodome numpy | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Components installed (official index)"
    } else {
        Write-Warn2 "Automatic component install failed (this does NOT affect .kgm/.kgma files)."
        Write-Warn2 "If converting .kgg fails later, run manually: $py -m pip install pycryptodome numpy"
    }
}

# ------------------------------------------------------------
# Step 3/3: create the desktop shortcut
# ------------------------------------------------------------
Write-Step "Step 3 / 3: creating the desktop shortcut"
try {
    $pythonw = Join-Path (Split-Path -Parent $py) "pythonw.exe"
    if (-not (Test-Path $pythonw)) { $pythonw = $py }
    $ws = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnkPath = Join-Path $desktop "KuGou Unlocker.lnk"
    $lnk = $ws.CreateShortcut($lnkPath)
    $lnk.TargetPath = $pythonw
    $lnk.Arguments  = '"' + (Join-Path $scriptDir "kugou_unlock_gui.py") + '"'
    $lnk.WorkingDirectory = $scriptDir
    $lnk.Description = "KuGou Unlocker v2.4 · by shushuu · personal use only"
    $lnk.Save()
    Write-Ok "Desktop shortcut created: KuGou Unlocker"
} catch {
    Write-Warn2 "Could not create the shortcut (no problem — just double-click start_kugou_unlocker.bat)."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Installation complete!" -ForegroundColor Green
Write-Host "   Double-click 'KuGou Unlocker' on your desktop:" -ForegroundColor Green
Write-Host "     1. Click 'Find my KuGou folder' (or pick files/folder manually)" -ForegroundColor Green
Write-Host "     2. Choose where to save  3. Click 'Start conversion'" -ForegroundColor Green
Write-Host "   Full illustrated guide: 'KuGou Unlocker User Manual.pdf' or README.md" -ForegroundColor Green
Write-Host "   -- by shushuu (shushuu) · Personal use only · No commercial use --" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
