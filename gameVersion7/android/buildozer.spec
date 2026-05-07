[app]
title = Chaos Ball
package.name = chaosball
package.domain = com.yourname

source.dir = .
source.include_exts = py,png,jpg,wav,mp3,ogg,atlas,json

version = 1.0

# Entry point
entrypoint = main

requirements = python3,pygame

orientation = landscape

fullscreen = 1

android.permissions = VIBRATE

[buildozer]
log_level = 2
warn_on_root = 1
