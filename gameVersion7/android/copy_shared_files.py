# Copy these 5 files UNCHANGED from gameVersion7 into the android folder:
# - utils.py
# - particles.py
# - enemies.py
# - renderer.py
# - level_generator.py
#
# They work identically on Android — no changes needed.
# Run this script once to copy them automatically:

import shutil, os

src = os.path.join(os.path.dirname(__file__), "..")
dst = os.path.dirname(__file__)

for f in ["utils.py", "particles.py", "enemies.py", "renderer.py", "level_generator.py"]:
    shutil.copy(os.path.join(src, f), os.path.join(dst, f))
    print(f"Copied {f}")

print("Done!")
