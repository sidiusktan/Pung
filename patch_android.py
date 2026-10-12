# patch_android.py — запусти ОДИН раз: python patch_android.py
# Он аккуратно правит main.py под Android. Повторный запуск ничего не ломает.
import os

PATH = 'main.py'
if not os.path.isfile(PATH):
    print('main.py не найден рядом с patch_android.py!')
    raise SystemExit(1)

with open(PATH, 'r', encoding='utf-8') as f:
    src = f.read()

# 1) Android-детект + переход в writable-папку для сохранений
if 'IS_ANDROID' not in src:
    old = 'import time as _time\n'
    new = (
        'import time as _time\n'
        '\n'
        "IS_ANDROID = ('ANDROID_ARGUMENT' in os.environ) or ('ANDROID_PRIVATE' in os.environ)\n"
        'if IS_ANDROID:\n'
        "    _priv = os.environ.get('ANDROID_PRIVATE', '')\n"
        '    if _priv and os.path.isdir(_priv):\n'
        '        try:\n'
        '            os.chdir(_priv)\n'
        '        except Exception:\n'
        '            pass\n'
    )
    if old in src:
        src = src.replace(old, new, 1)
        print('+ Android-детект добавлен')
    else:
        print('!! Не нашёл строку "import time as _time" — пропущено')

# 2) Полноэкранный режим на Android
old_mode = 'screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)'
new_mode = (
    'if IS_ANDROID:\n'
    '    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)\n'
    'else:\n'
    '    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)'
)
if old_mode in src:
    src = src.replace(old_mode, new_mode, 1)
    print('+ Полноэкранный режим включён')

# 3) Перевод для надписи "Скоро"
if '"soon":' not in src:
    src = src.replace(
        '"freeze_msg": "ЗАМОРОЗКА 6с",',
        '"freeze_msg": "ЗАМОРОЗКА 6с",\n        "soon": "Скоро",',
        1
    )
    src = src.replace(
        '"freeze_msg": "FROZEN 6s",',
        '"freeze_msg": "FROZEN 6s",\n        "soon": "Soon",',
        1
    )
    print('+ Перевод "Скоро" добавлен')

# 4) Кнопка "Сетевая игра" серая на Android
old_menu = (
    '    for rect, label, color in [\n'
    '        (play_r, t("play"),        (80, 200, 100)),\n'
    '        (mp_r,   t("mp_menu_btn"), (120, 100, 220)),\n'
    '        (lang_r, t("language"),    (60, 140, 220)),\n'
    '        (exit_r, t("exit"),        (200, 80, 80))]:'
)
new_menu = (
    '    _mp_label = t("soon") if IS_ANDROID else t("mp_menu_btn")\n'
    '    _mp_color = (140, 140, 140) if IS_ANDROID else (120, 100, 220)\n'
    '    for rect, label, color in [\n'
    '        (play_r, t("play"),        (80, 200, 100)),\n'
    '        (mp_r,   _mp_label,        _mp_color),\n'
    '        (lang_r, t("language"),    (60, 140, 220)),\n'
    '        (exit_r, t("exit"),        (200, 80, 80))]:'
)
if old_menu in src:
    src = src.replace(old_menu, new_menu, 1)
    print('+ Кнопка MP перекрашена для Android')

# 5) Клик по сетевой кнопке — no-op на Android
old_click = 'elif mp_r.collidepoint(mx, my): net_close(); app_state = "mp_menu"'
new_click = 'elif mp_r.collidepoint(mx, my) and not IS_ANDROID: net_close(); app_state = "mp_menu"'
if old_click in src:
    src = src.replace(old_click, new_click, 1)
    print('+ Клик по MP отключён для Android')

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(src)

print('Готово. main.py обновлён. На ПК игра работает как раньше.')