[app]
title = Pung
package.name = pung
package.domain = org.sidiusktan

source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,ogg,wav,mp3,ico,ttf
source.exclude_dirs = bin,.buildozer,build,.git,.github,__pycache__,assets/system/icon.ico

version = 1.0

# Фиксируем версии, иначе buildozer тянет Python 3.14 и pygame не собирается
requirements = python3==3.11.15,hostpython3==3.11.15,pygame-ce==2.5.5,pillow

orientation = landscape
fullscreen = 1

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

android.api = 34
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

p4a.bootstrap = sdl2
p4a.local_recipes = .

icon.filename = %(source.dir)s/assets/system/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
