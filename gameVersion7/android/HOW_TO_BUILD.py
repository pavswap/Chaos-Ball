# HOW TO BUILD THE ANDROID APK
# ================================
# You CANNOT build on Windows directly.
# Use WSL (Windows Subsystem for Linux) OR Google Colab (easiest, free).

# ── OPTION 1: Google Colab (NO INSTALLS NEEDED) ────────────────────────────
# 1. Go to https://colab.research.google.com
# 2. Create a new notebook
# 3. Run these cells:

"""
# Cell 1 – Install buildozer
!pip install buildozer cython

# Cell 2 – Install Android dependencies
!sudo apt-get install -y \
    python3-pip build-essential git python3 python3-dev \
    ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev \
    libsdl2-ttf-dev libportmidi-dev libswscale-dev \
    libavformat-dev libavcodec-dev zlib1g-dev

!sudo apt-get install -y \
    libgstreamer1.0 gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

# Cell 3 – Upload your android folder as a zip, then unzip:
from google.colab import files
uploaded = files.upload()   # upload android.zip

import zipfile
with zipfile.ZipFile('android.zip', 'r') as z:
    z.extractall('android')

# Cell 4 – Build APK
import os
os.chdir('android')
!buildozer android debug

# Cell 5 – Download APK
files.download('bin/chaosball-1.0-debug.apk')
"""

# ── OPTION 2: WSL on Windows ────────────────────────────────────────────────
# 1. Install WSL: open PowerShell as admin → wsl --install
# 2. Open Ubuntu from Start menu
# 3. Run:
#    sudo apt update && sudo apt install -y python3-pip
#    pip3 install buildozer cython
#    cd /mnt/c/Users/Kushal/Desktop/pythonnnn/vibeAhhhGame-main/gameVersion7/android
#    python3 copy_shared_files.py
#    buildozer android debug
# 4. APK will appear in:  android/bin/chaosball-1.0-debug.apk
# 5. Transfer to phone via USB or upload to Google Drive

# ── INSTALLING ON ANDROID ───────────────────────────────────────────────────
# 1. Enable "Unknown Sources" / "Install unknown apps" in Android settings
# 2. Copy APK to phone
# 3. Tap to install → Play!
