[app]
title = دفتر خیاطی
package.name = daftarkhayati
package.domain = org.mohamadtalkinsta
source.dir = .
source.include_exts = py,kv,ttf,png,jpg,json
source.exclude_dirs = tests,.github,bin,.buildozer
version = 1.0.0
requirements = python3,kivy==2.3.1,arabic-reshaper,python-bidi
p4a.branch = develop
orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
