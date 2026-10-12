import pygame
import sys
import os
import io
import random
import math
import array
import socket
import threading
import time as _time

IS_ANDROID = ('ANDROID_ARGUMENT' in os.environ) or ('ANDROID_PRIVATE' in os.environ)
if IS_ANDROID:
    _priv = os.environ.get('ANDROID_PRIVATE', '')
    if _priv and os.path.isdir(_priv):
        try:
            os.chdir(_priv)
        except Exception:
            pass

try:
    pygame.mixer.pre_init(44100, -16, 1, 512)
except Exception:
    pass
pygame.init()

WIDTH, HEIGHT = 1000, 700
if IS_ANDROID:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Pung")

BG_COLOR = (30, 60, 90)
TILE_BG = (245, 240, 230)

def base_path():
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(base_path(), "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")

def _set_window_icon():
    for ext in (".png", ".ico", ".bmp"):
        p = os.path.join(ASSETS_DIR, "system", f"icon{ext}")
        if os.path.isfile(p):
            try:
                pygame.display.set_icon(pygame.image.load(p))
                return
            except Exception:
                pass
_set_window_icon()

LEVEL_SETS = {
    "kids": [
        {"cols": 6,  "rows": 4, "time": 78,  "rocks": 0},
        {"cols": 8,  "rows": 6, "time": 110, "rocks": 0},
        {"cols": 10, "rows": 6, "time": 143, "rocks": 0},
        {"cols": 12, "rows": 8, "time": 182, "rocks": 2},
        {"cols": 14, "rows": 8, "time": 208, "rocks": 2},
        {"cols": 12, "rows": 7, "time": 200, "rocks": 4, "boss": True, "hp": 60},
    ],
    "mid": [
        {"cols": 8,  "rows": 5, "time": 58,  "rocks": 2},
        {"cols": 10, "rows": 6, "time": 85,  "rocks": 4},
        {"cols": 12, "rows": 7, "time": 110, "rocks": 6},
        {"cols": 14, "rows": 8, "time": 143, "rocks": 8},
        {"cols": 16, "rows": 8, "time": 182, "rocks": 10},
        {"cols": 14, "rows": 8, "time": 250, "rocks": 6, "boss": True, "hp": 100},
    ],
    "adult": [
        {"cols": 10, "rows": 6,  "time": 72,  "rocks": 6},
        {"cols": 12, "rows": 7,  "time": 91,  "rocks": 8},
        {"cols": 14, "rows": 8,  "time": 110, "rocks": 10},
        {"cols": 16, "rows": 8,  "time": 137, "rocks": 14},
        {"cols": 18, "rows": 10, "time": 169, "rocks": 18},
        {"cols": 18, "rows": 10, "time": 300, "rocks": 8, "boss": True, "hp": 150},
    ],
}

BOSS_HP_PER_PAIR = 3
BOSS_ATTACK_INTERVAL = 15.0

SURVIVAL_COLS = 12
SURVIVAL_ROWS = 8
SURVIVAL_START_TIME = 45.0
SURVIVAL_PAIR_TIME = 2.0
SURVIVAL_SPAWN_START = 15.0
SURVIVAL_SPAWN_MIN = 6.0
SURVIVAL_STONE_EVERY = 60.0
GOLD_INTERVAL = 12.0
GOLD_FREEZE_TIME = 6.0
GOLD_MAX = 3

MIX_BASE = 100

current_pack = "kids"
preview_level = 0

LEVELS = LEVEL_SETS["mid"]
VS_LEVELS = [
    {"cols": 6,  "rows": 4, "time": 60, "pack": "kids",  "rocks": 0},
    {"cols": 8,  "rows": 5, "time": 75, "pack": "kids",  "rocks": 0},
    {"cols": 8,  "rows": 6, "time": 90, "pack": "mid",   "rocks": 4},
    {"cols": 10, "rows": 6, "time": 110, "pack": "mid",  "rocks": 6},
    {"cols": 10, "rows": 6, "time": 130, "pack": "adult","rocks": 8},
]

COLS = LEVEL_SETS["kids"][0]["cols"]
ROWS = LEVEL_SETS["kids"][0]["rows"]
GAME_TIME = LEVEL_SETS["kids"][0]["time"]
current_level = 0

PRICES = {"hint": 30, "shuffle": 50, "bomb": 80}
badges = {"hint": 1, "shuffle": 1, "bomb": 1}
SKILL_KEYS = {"hint": "H", "shuffle": "R", "bomb": "B"}

VS_SKILLS = {
    "fog":   {"cd": 28.0, "duration": 5.0},
    "shake": {"cd": 35.0, "duration": 5.0},
    "lock":  {"cd": 45.0, "duration": 7.0},
}
vs_my_cd = {"fog": 0.0, "shake": 0.0, "lock": 0.0}
vs_fog_t = 0.0
vs_shake_t = 0.0
vs_lock_t = 0.0
vs_attack_msg = ""
vs_attack_timer = 0.0
vs_my_attack_msg = ""
vs_my_attack_timer = 0.0

boss_hp = 0
boss_hp_max = 0
boss_attack_timer = 0.0

golden_cells = set()
golden_timer = 0.0
freeze_t = 0.0
freeze_msg_t = 0.0

survival_mode = False
survival_score = 0
survival_elapsed = 0.0
survival_spawn_t = 0.0
survival_stone_t = 0.0
survival_spawn_interval = SURVIVAL_SPAWN_START

SURVIVAL_RECORD_FILE = "survival_record.txt"
survival_best_score = 0

def load_survival_record():
    try:
        with open(SURVIVAL_RECORD_FILE, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        return int(lines[0]) if lines else 0
    except Exception:
        return 0

def save_survival_record(s):
    try:
        with open(SURVIVAL_RECORD_FILE, "w") as f:
            f.write(f"{s}\n")
    except Exception:
        pass

survival_best_score = load_survival_record()

fullscreen = False
clock = pygame.time.Clock()

PROGRESS_FILE = "progress.txt"
NET_PORT = 5555
DISCOVERY_PORT = 5556

def load_save():
    try:
        with open(PROGRESS_FILE, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        kids  = int(lines[0]) if len(lines) > 0 else 0
        total = int(lines[1]) if len(lines) > 1 else 0
        mid   = int(lines[6]) if len(lines) > 6 else 0
        adult = int(lines[7]) if len(lines) > 7 else 0
        return kids, mid, adult, total
    except Exception:
        return 0, 0, 0, 0

max_unlocked = {"kids": 0, "mid": 0, "adult": 0}
(kids_u, mid_u, adult_u, total_score) = load_save()
max_unlocked["kids"]  = max(0, min(kids_u,  len(LEVEL_SETS["kids"])  - 1))
max_unlocked["mid"]   = max(0, min(mid_u,   len(LEVEL_SETS["mid"])   - 1))
max_unlocked["adult"] = max(0, min(adult_u, len(LEVEL_SETS["adult"]) - 1))

def save_game():
    try:
        with open(PROGRESS_FILE, "w") as f:
            f.write(f"{max_unlocked['kids']}\n{total_score}\n0\n0\n0\n0\n"
                    f"{max_unlocked['mid']}\n{max_unlocked['adult']}\n")
    except Exception:
        pass

SOUNDS = {}
sound_enabled = True
MUSIC_PATH = None
music_playing = False

def _gen_tone(freq, dur_ms, vol=0.25, fade_ms=25):
    sr = 44100; n = int(sr * dur_ms / 1000); fade_n = max(1, int(sr * fade_ms / 1000))
    buf = array.array('h')
    for i in range(n):
        t = i / sr; val = math.sin(2 * math.pi * freq * t)
        att = 1.0
        if i < fade_n: att = i / fade_n
        rem = n - i
        if rem < fade_n: att = min(att, rem / fade_n)
        buf.append(int(val * vol * 32767 * att))
    return pygame.mixer.Sound(buffer=buf.tobytes())

def _gen_noise(dur_ms, vol=0.35, fade_ms=30):
    sr = 44100; n = int(sr * dur_ms / 1000); fade_n = max(1, int(sr * fade_ms / 1000))
    buf = array.array('h')
    for i in range(n):
        val = random.uniform(-1, 1)
        att = 1.0
        if i < fade_n: att = i / fade_n
        rem = n - i
        if rem < fade_n: att = min(att, rem / fade_n)
        buf.append(int(val * vol * 32767 * att))
    return pygame.mixer.Sound(buffer=buf.tobytes())

def _load_user_sound(name):
    if not os.path.isdir(SOUNDS_DIR): return None
    for ext in (".ogg", ".wav", ".mp3"):
        p = os.path.join(SOUNDS_DIR, name + ext)
        if os.path.isfile(p):
            try: return pygame.mixer.Sound(p)
            except Exception: pass
    return None

def _build_sounds():
    global MUSIC_PATH
    if not pygame.mixer.get_init(): return
    fallbacks = {
        "click":   lambda: _gen_tone(800, 45, 0.20),
        "match":   lambda: _gen_tone(1046, 90, 0.25),
        "hint":    lambda: _gen_tone(1320, 110, 0.22),
        "shuffle": lambda: _gen_tone(500, 140, 0.25),
        "bomb":    lambda: _gen_noise(220, 0.35),
        "win":     lambda: _gen_tone(1568, 220, 0.28),
        "lose":    lambda: _gen_tone(196, 320, 0.28),
        "vs_hit":  lambda: _gen_tone(320, 180, 0.30),
        "freeze":  lambda: _gen_tone(880, 220, 0.28),
    }
    for name, fb in fallbacks.items():
        s = _load_user_sound(name)
        if s is None:
            try: s = fb()
            except Exception: s = None
        SOUNDS[name] = s
    if os.path.isdir(SOUNDS_DIR):
        for ext in (".ogg", ".wav", ".mp3"):
            p = os.path.join(SOUNDS_DIR, "menu_music" + ext)
            if os.path.isfile(p):
                MUSIC_PATH = p; break

_build_sounds()

def play(name):
    if not sound_enabled: return
    s = SOUNDS.get(name)
    if s is None: return
    try: s.play()
    except Exception: pass

def ensure_menu_music(on):
    global music_playing
    if MUSIC_PATH is None: return
    try:
        if on:
            if not music_playing:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(0.5 if sound_enabled else 0.0)
                pygame.mixer.music.play(-1)
                music_playing = True
            else:
                pygame.mixer.music.unpause()
        else:
            if music_playing:
                pygame.mixer.music.pause()
    except Exception: pass

def toggle_sound():
    global sound_enabled
    sound_enabled = not sound_enabled
    try:
        if music_playing:
            pygame.mixer.music.set_volume(0.5 if sound_enabled else 0.0)
    except Exception: pass

LANGUAGES = {
    "ru": {
        "score": "Счёт", "you_win": "Ты победил!", "you_lose": "Ты проиграл",
        "try_again": "Ещё раз", "play": "Играть", "levels": "Уровни",
        "language": "Язык", "exit": "Выход", "back": "Назад",
        "level": "Уровень", "paused": "Пауза", "continue": "Продолжить",
        "restart": "Заново", "to_menu": "В меню", "locked": "Закрыто",
        "size": "Размер", "lvl_time": "Время",
        "difficulty": "Сложность", "rocks_lbl": "Камней",
        "diff_easy": "Легко", "diff_medium": "Средне", "diff_hard": "Сложно",
        "pack_title": "Выбери сложность",
        "pack_1": "Сложность 1", "pack_2": "Сложность 2", "pack_3": "Сложность 3",
        "survival": "Выживание",
        "survival_rec": "Рекорд: {s}",
        "survival_hud": "Выживание — {m} мин",
        "mp_menu_btn": "Сетевая игра", "mp_title": "Сетевая игра",
        "mp_host": "Создать игру", "mp_join": "Подключиться",
        "mp_wait": "Ожидание игрока...", "mp_your_ip": "Твой IP",
        "mp_enter_ip": "Введи IP хоста", "mp_connect": "Подключиться",
        "mp_scan": "Сканировать", "mp_scanning": "Ищу игры в сети...",
        "mp_found": "Найдено игр: {n}", "mp_none": "Игр не найдено. Попробуй ещё или введи IP вручную.",
        "mp_scan_hint": "Нажми «Сканировать» или введи IP вручную",
        "mp_connecting": "Подключение...", "mp_connected": "Подключено!",
        "mp_wait_host": "Ожидание хоста...", "mp_start": "Начать игру",
        "mp_cancel": "Отмена", "mp_hint_keys": "Enter — подключиться, Esc — назад",
        "mp_play": "Сетевая игра", "mp_peer_paused": "Соперник поставил на паузу",
        "mp_round_win": "Ты победил в раунде!", "mp_round_lose": "Соперник победил",
        "mp_round_draw": "Ничья", "mp_next_level": "Следующий уровень",
        "mp_final_title": "Матч окончен", "mp_peer": "Соперник", "mp_you": "Ты",
        "mp_wait_next": "Ждём, пока хост продолжит...",
        "mp_mode_coop": "Co-op", "mp_mode_vs": "Versus",
        "mp_mode_title": "Выбери режим:",
        "vs_win": "Ты выиграл раунд!", "vs_lose": "Соперник выиграл раунд",
        "vs_draw": "Раунд — ничья", "vs_round": "Раунд",
        "vs_you_won": "Ты выиграл матч!", "vs_peer_won": "Соперник выиграл матч",
        "vs_draw_match": "Матч — ничья",
        "vs_peer_fog":   "Соперник: ТУМАН!",
        "vs_peer_shake": "Соперник: ТРЯСКА!",
        "vs_peer_lock":  "Соперник: БЛОК!",
        "vs_you_fog":    "Ты наслал туман",
        "vs_you_shake":  "Ты наслал тряску",
        "vs_you_lock":   "Ты заблокировал соперника",
        "next": "Дальше",
        "boss": "БОСС",
        "boss_hp": "HP босса",
        "boss_msg_rocks":   "БОСС: камни!",
        "boss_msg_time":    "БОСС: −10 сек!",
        "boss_msg_fog":     "БОСС: туман!",
        "boss_msg_shake":   "БОСС: тряска!",
        "boss_msg_lock":    "БОСС: блок!",
        "freeze_msg": "ЗАМОРОЗКА 6с",
        "soon": "Скоро",
    },
    "en": {
        "score": "Score", "you_win": "You Win!", "you_lose": "You Lose",
        "try_again": "Try again", "play": "Play", "levels": "Levels",
        "language": "Language", "exit": "Exit", "back": "Back",
        "level": "Level", "paused": "Paused", "continue": "Continue",
        "restart": "Restart", "to_menu": "Main Menu", "locked": "Locked",
        "size": "Size", "lvl_time": "Time",
        "difficulty": "Difficulty", "rocks_lbl": "Rocks",
        "diff_easy": "Easy", "diff_medium": "Medium", "diff_hard": "Hard",
        "pack_title": "Choose difficulty",
        "pack_1": "Difficulty 1", "pack_2": "Difficulty 2", "pack_3": "Difficulty 3",
        "survival": "Survival",
        "survival_rec": "Best: {s}",
        "survival_hud": "Survival — {m} min",
        "mp_menu_btn": "Multiplayer", "mp_title": "Multiplayer",
        "mp_host": "Host game", "mp_join": "Join game",
        "mp_wait": "Waiting for player...", "mp_your_ip": "Your IP",
        "mp_enter_ip": "Enter host IP", "mp_connect": "Connect",
        "mp_scan": "Scan", "mp_scanning": "Scanning network...",
        "mp_found": "Games found: {n}", "mp_none": "No games found. Try again or enter IP manually.",
        "mp_scan_hint": "Press 'Scan' or enter IP manually",
        "mp_connecting": "Connecting...", "mp_connected": "Connected!",
        "mp_wait_host": "Waiting for host...", "mp_start": "Start game",
        "mp_cancel": "Cancel", "mp_hint_keys": "Enter — connect, Esc — back",
        "mp_play": "Multiplayer", "mp_peer_paused": "Peer paused the game",
        "mp_round_win": "You won the round!", "mp_round_lose": "Opponent won",
        "mp_round_draw": "Draw", "mp_next_level": "Next level",
        "mp_final_title": "Match over", "mp_peer": "Opponent", "mp_you": "You",
        "mp_wait_next": "Waiting for host...",
        "mp_mode_coop": "Co-op", "mp_mode_vs": "Versus",
        "mp_mode_title": "Choose mode:",
        "vs_win": "You won the round!", "vs_lose": "Opponent won the round",
        "vs_draw": "Round draw", "vs_round": "Round",
        "vs_you_won": "You won the match!", "vs_peer_won": "Opponent won the match",
        "vs_draw_match": "Match draw",
        "vs_peer_fog":   "Opponent: FOG!",
        "vs_peer_shake": "Opponent: SHAKE!",
        "vs_peer_lock":  "Opponent: LOCK!",
        "vs_you_fog":    "You cast fog",
        "vs_you_shake":  "You cast shake",
        "vs_you_lock":   "You locked opponent",
        "next": "Next",
        "boss": "BOSS",
        "boss_hp": "Boss HP",
        "boss_msg_rocks":   "BOSS: rocks!",
        "boss_msg_time":    "BOSS: −10 sec!",
        "boss_msg_fog":     "BOSS: fog!",
        "boss_msg_shake":   "BOSS: shake!",
        "boss_msg_lock":    "BOSS: lock!",
        "freeze_msg": "FROZEN 6s",
        "soon": "Soon",
    },
}
current_lang = "ru"
def t(key): return LANGUAGES[current_lang].get(key, key)

def toggle_lang():
    global current_lang
    current_lang = "en" if current_lang == "ru" else "ru"

def difficulty_of(level_index):
    if level_index <= 1: return t("diff_easy")
    if level_index <= 3: return t("diff_medium")
    return t("diff_hard")

def pack_name(p):
    if p == "kids":  return t("pack_1")
    if p == "mid":   return t("pack_2")
    if p == "adult": return t("pack_3")
    return p

try:
    FONT_BIG = pygame.font.SysFont("arial", 72, bold=True)
    FONT_MED = pygame.font.SysFont("arial", 30, bold=True)
    FONT_SM  = pygame.font.SysFont("arial", 22, bold=True)
    FONT_XS  = pygame.font.SysFont("arial", 16, bold=True)
except Exception:
    FONT_BIG = pygame.font.Font(None, 72)
    FONT_MED = pygame.font.Font(None, 30)
    FONT_SM  = pygame.font.Font(None, 22)
    FONT_XS  = pygame.font.Font(None, 16)

def _pil_to_surface(pil_img):
    with io.BytesIO() as f:
        pil_img.save(f, format="PNG"); f.seek(0)
        return pygame.image.load(f).convert_alpha()

def _load_image_any(path, size):
    if not os.path.isfile(path): return None
    ext = os.path.splitext(path)[1].lower()
    if ext == ".gif":
        try:
            from PIL import Image
        except Exception:
            return None
        try:
            im = Image.open(path); frames = []; total = 0
            try:
                while True:
                    im.seek(im.tell())
                    frame = im.convert("RGBA")
                    surf = _pil_to_surface(frame)
                    surf = pygame.transform.smoothscale(surf, (size, size))
                    try: dur = im.info.get("duration", 100) or 100
                    except Exception: dur = 100
                    frames.append((surf, dur)); total += dur
                    im.seek(im.tell() + 1)
            except EOFError:
                pass
            if frames:
                return ("gif", frames, total)
        except Exception:
            return None
        return None
    else:
        try:
            img = pygame.image.load(path).convert_alpha()
            return ("static", pygame.transform.smoothscale(img, (size, size)))
        except Exception:
            return None

def blit_icon_entry(surface, entry, x, y):
    if entry is None: return
    kind = entry[0]
    if kind == "static":
        surface.blit(entry[1], (x, y))
    elif kind == "gif":
        frames = entry[1]; total = entry[2]
        t_ms = pygame.time.get_ticks() % total if total > 0 else 0
        acc = 0
        for surf, dur in frames:
            if acc <= t_ms < acc + dur:
                surface.blit(surf, (x, y)); return
            acc += dur
        if frames:
            surface.blit(frames[-1][0], (x, y))

NUM_TILES = 15
MIX_TILE_MIN = MIX_BASE + 1
MIX_TILE_MAX = MIX_BASE + 45

PARTICLE_COLORS = {
    1: (255, 160, 60), 2: (80, 200, 100), 3: (170, 120, 70), 4: (120, 180, 250),
    5: (250, 140, 200), 6: (120, 220, 120), 7: (255, 150, 50), 8: (240, 90, 110),
    9: (255, 210, 60), 10: (230, 230, 250), 11: (250, 220, 80), 12: (220, 80, 80),
    13: (250, 220, 40), 14: (240, 130, 220), 15: (220, 60, 60),
}

def particle_color(tile_id):
    if tile_id >= MIX_BASE:
        idx = ((tile_id - MIX_BASE - 1) % 15) + 1
        return PARTICLE_COLORS.get(idx, (255, 255, 255))
    return PARTICLE_COLORS.get(tile_id, (255, 255, 255))

icon_cache = {}

def _split_tile(tile):
    if tile >= MIX_BASE:
        idx = tile - MIX_BASE
        if idx <= 15: return ("kids", idx)
        if idx <= 30: return ("mid", idx - 15)
        return ("adult", idx - 30)
    return (current_pack, tile)

def get_icon(tile, size):
    pack, num = _split_tile(tile)
    key = (pack, num, size)
    if key not in icon_cache:
        entry = None
        for ext in (".png", ".gif"):
            p = os.path.join(ASSETS_DIR, "sets", pack, f"{num}{ext}")
            e = _load_image_any(p, size)
            if e is not None:
                entry = e; break
        if entry is None and tile == -1:
            for ext in (".png", ".gif"):
                p = os.path.join(ASSETS_DIR, "system", f"rock{ext}")
                e = _load_image_any(p, size)
                if e is not None:
                    entry = e; break
        icon_cache[key] = entry
    return icon_cache[key]

system_cache = {}

def get_system_icon(name, size):
    key = (name, size)
    if key in system_cache:
        return system_cache[key]
    entry = None
    for ext in (".png", ".gif"):
        p = os.path.join(ASSETS_DIR, "system", f"{name}{ext}")
        e = _load_image_any(p, size)
        if e is not None:
            entry = e; break
    system_cache[key] = entry
    return entry

_logo_cache = None
_logo_loaded = False

def get_logo():
    global _logo_cache, _logo_loaded
    if _logo_loaded:
        return _logo_cache
    _logo_loaded = True
    for ext in (".png", ".gif"):
        p = os.path.join(ASSETS_DIR, "system", f"logo{ext}")
        if os.path.isfile(p):
            try:
                _logo_cache = pygame.image.load(p).convert_alpha()
                return _logo_cache
            except Exception:
                pass
    _logo_cache = None
    return None

_bg_cache = {}

def _load_bg_surface(path):
    for ext in (".png", ".jpg", ".jpeg"):
        p = path + ext
        if os.path.isfile(p):
            try:
                return pygame.image.load(p).convert()
            except Exception:
                pass
    return None

def get_bg(name, pack=None):
    key = (name, pack)
    if key in _bg_cache:
        return _bg_cache[key]
    surf = None
    if pack:
        base = os.path.join(ASSETS_DIR, "sets", pack, name)
        surf = _load_bg_surface(base)
    if surf is None:
        base = os.path.join(ASSETS_DIR, "system", name)
        surf = _load_bg_surface(base)
    _bg_cache[key] = surf
    return surf

def draw_bg(surface, name, sw, sh, pack=None, default_color=BG_COLOR):
    bg = get_bg(name, pack)
    if bg is None:
        surface.fill(default_color); return
    try:
        surface.blit(pygame.transform.smoothscale(bg, (sw, sh)), (0, 0))
    except Exception:
        surface.fill(default_color)

def draw_game_bg(surface, sw, sh):
    """Фон для игрового поля — в выживании свой, иначе фон набора."""
    if survival_mode:
        # В выживании ищем system/bg_survival.* , иначе fallback на bg_game
        if get_bg("bg_survival") is not None:
            draw_bg(surface, "bg_survival", sw, sh)
        else:
            draw_bg(surface, "bg_game", sw, sh, pack=current_pack)
    else:
        draw_bg(surface, "bg_game", sw, sh, pack=current_pack)

# ============================================================
# NETWORK
# ============================================================
net_state = "idle"
net_error = ""
net_status_msg = ""
net_is_host = False
my_ip = ""
net_sock = None
net_conn = None
udp_sock = None
ip_input = ""
net_mode = "coop"

net_play = False
net_rx_queue = []
net_rx_lock = threading.Lock()

scan_state = "idle"
scan_results = []
scan_lock = threading.Lock()

_udp_recent = {}
_udp_recent_lock = threading.Lock()

mp_level_index = 0
mp_my_score = 0
mp_peer_score = 0
vs_my_rounds = 0
vs_peer_rounds = 0
vs_peer_board = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        try: return socket.gethostbyname(socket.gethostname())
        except Exception: return "127.0.0.1"

def net_close():
    global net_sock, net_conn, net_state, net_status_msg, net_error, net_play, udp_sock
    for obj in (net_conn, net_sock, udp_sock):
        try:
            if obj: obj.close()
        except Exception: pass
    net_conn = None; net_sock = None; udp_sock = None
    net_state = "idle"; net_status_msg = ""; net_error = ""; net_play = False
    with net_rx_lock: net_rx_queue.clear()

def net_send(msg):
    if net_conn is None: return
    try: net_conn.sendall((msg + "\n").encode("utf-8"))
    except Exception: pass

def net_recv_loop():
    global net_state, net_error
    buf = b""
    try:
        while net_conn is not None:
            data = net_conn.recv(2048)
            if not data: break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                msg = line.decode("utf-8", errors="ignore").strip()
                if msg:
                    with net_rx_lock: net_rx_queue.append(msg)
    except Exception: pass
    if net_state == "connected":
        net_state = "error"; net_error = "Connection lost"

def net_accept_loop():
    global net_conn, net_state, net_status_msg
    try:
        conn, addr = net_sock.accept()
        net_conn = conn; net_state = "connected"; net_status_msg = f"{addr[0]}"
        threading.Thread(target=net_recv_loop, daemon=True).start()
    except Exception as e:
        if net_state == "hosting":
            net_state = "error"; net_error = str(e)

def net_udp_responder():
    global udp_sock
    while True:
        s = udp_sock
        if s is None: break
        try: data, addr = s.recvfrom(256)
        except Exception: break
        if data.strip() == b"PUNG?":
            ip = addr[0]; now = _time.time()
            with _udp_recent_lock:
                last = _udp_recent.get(ip, 0)
                if now - last < 5.0: continue
                _udp_recent[ip] = now
            try: s.sendto(b"PUNG!Pung game", addr)
            except Exception: pass

def net_host_start():
    global net_state, net_sock, net_is_host, net_status_msg, my_ip, udp_sock
    net_close()
    net_is_host = True; my_ip = get_local_ip()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", NET_PORT)); s.listen(1)
        net_sock = s; net_state = "hosting"; net_status_msg = t("mp_wait")
        threading.Thread(target=net_accept_loop, daemon=True).start()
    except Exception as e:
        net_state = "error"; net_error = str(e); return
    try:
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        u.bind(("0.0.0.0", DISCOVERY_PORT)); udp_sock = u
        threading.Thread(target=net_udp_responder, daemon=True).start()
    except Exception:
        udp_sock = None

def net_client_worker(ip):
    global net_sock, net_conn, net_state, net_status_msg
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0); s.connect((ip, NET_PORT)); s.settimeout(None)
        net_sock = s; net_conn = s; net_state = "connected"; net_status_msg = t("mp_connected")
        threading.Thread(target=net_recv_loop, daemon=True).start()
    except Exception as e:
        net_state = "error"; net_error = str(e)

def net_client_start(ip):
    global net_state, net_is_host, net_status_msg
    net_close()
    net_is_host = False; net_state = "connecting"; net_status_msg = t("mp_connecting")
    threading.Thread(target=net_client_worker, args=(ip,), daemon=True).start()

def _subnet_broadcasts(ip):
    out = {"255.255.255.255", "127.0.0.1"}
    try:
        parts = ip.split(".")
        if len(parts) == 4:
            a, b, c = parts[0], parts[1], parts[2]
            if a == "10":
                for d in range(0, 4): out.add(f"{a}.{b}.{d}.255")
            else:
                out.add(f"{a}.{b}.{c}.255")
    except Exception: pass
    return list(out)

def net_scan_worker():
    global scan_state, scan_results
    results = []; seen = set()
    my = get_local_ip(); targets = _subnet_broadcasts(my)
    u = None
    try:
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        u.settimeout(0.15)
        for wave in range(3):
            for tgt in targets:
                try: u.sendto(b"PUNG?", (tgt, DISCOVERY_PORT))
                except Exception: pass
            t_end = _time.time() + 0.25
            while _time.time() < t_end:
                try:
                    data, addr = u.recvfrom(256); ip = addr[0]
                    if ip in seen: continue
                    if data.startswith(b"PUNG!"):
                        seen.add(ip)
                        name = data[5:].decode("utf-8", errors="ignore").strip() or "Pung"
                        results.append((ip, name))
                except socket.timeout: break
                except Exception: break
        u.settimeout(0.25); t_end = _time.time() + 2.5
        while _time.time() < t_end:
            try:
                data, addr = u.recvfrom(256); ip = addr[0]
                if ip in seen: continue
                if data.startswith(b"PUNG!"):
                    seen.add(ip)
                    name = data[5:].decode("utf-8", errors="ignore").strip() or "Pung"
                    results.append((ip, name))
            except socket.timeout: continue
            except Exception: break
    except Exception: pass
    finally:
        try:
            if u: u.close()
        except Exception: pass
    with scan_lock: scan_results = results
    scan_state = "done"

def net_scan_start():
    global scan_state, scan_results
    with scan_lock: scan_results = []
    scan_state = "scanning"
    threading.Thread(target=net_scan_worker, daemon=True).start()

# ============================================================
# GAME STATE
# ============================================================
app_state = "menu"

def _make_board_for(cols, rows, rocks=0, mixed=False):
    total = cols * rows
    if (total - rocks) % 2 != 0:
        rocks += 1
    max_rocks = max(0, total - 4)
    rocks = max(0, min(rocks, max_rocks))
    playable = total - rocks
    pairs = playable // 2
    tiles = []
    if mixed:
        tmin, tmax = MIX_TILE_MIN, MIX_TILE_MAX
    else:
        tmin, tmax = 1, NUM_TILES
    for _ in range(pairs):
        tt = random.randint(tmin, tmax)
        tiles.append(tt); tiles.append(tt)
    for _ in range(rocks):
        tiles.append(-1)
    random.shuffle(tiles)
    return [tiles[i * cols:(i + 1) * cols] for i in range(rows)]

def generate_board():
    lvls = LEVEL_SETS[current_pack]
    rocks = 0
    if current_level < len(lvls):
        rocks = lvls[current_level].get("rocks", 0)
    return _make_board_for(COLS, ROWS, rocks)

board = generate_board()
selected = None
time_left = GAME_TIME
animations = []
particles = []
hint_pair = None
hint_timer = 0.0

def reset_badges():
    badges["hint"] = 1; badges["shuffle"] = 1; badges["bomb"] = 1

def reset_gold():
    global golden_cells, golden_timer, freeze_t, freeze_msg_t
    golden_cells = set()
    golden_timer = GOLD_INTERVAL
    freeze_t = 0.0
    freeze_msg_t = 0.0

def board_to_csv(b, cols, rows):
    return ",".join(str(b[r][c]) for r in range(rows) for c in range(cols))

def csv_to_board(s, cols, rows):
    nums = [int(x) for x in s.split(",")]
    return [nums[i*cols:(i+1)*cols] for i in range(rows)]

def is_boss_level_for(pack, idx):
    lvls = LEVEL_SETS.get(pack, [])
    if idx < 0 or idx >= len(lvls): return False
    return lvls[idx].get("boss", False)

def is_boss_level():
    if net_play: return False
    if survival_mode: return False
    return is_boss_level_for(current_pack, current_level)

def start_level(index):
    global current_level, COLS, ROWS, GAME_TIME
    global board, selected, time_left, app_state, animations, particles
    global hint_pair, hint_timer, net_play, survival_mode
    global boss_hp, boss_hp_max, boss_attack_timer
    global vs_fog_t, vs_shake_t, vs_lock_t, vs_attack_msg, vs_attack_timer
    global vs_my_attack_msg, vs_my_attack_timer
    lvls = LEVEL_SETS[current_pack]
    index = max(0, min(index, len(lvls) - 1))
    if index > max_unlocked[current_pack]: return
    net_play = False
    survival_mode = False
    current_level = index
    lvl = lvls[current_level]
    COLS = lvl["cols"]; ROWS = lvl["rows"]; GAME_TIME = lvl["time"]
    board = generate_board()
    if count_available_moves() < 1:
        do_auto_shuffle_local()
    selected = None; time_left = GAME_TIME; app_state = "playing"
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0
    reset_badges(); reset_gold()
    vs_fog_t = 0.0; vs_shake_t = 0.0; vs_lock_t = 0.0
    vs_attack_msg = ""; vs_attack_timer = 0.0
    vs_my_attack_msg = ""; vs_my_attack_timer = 0.0
    if lvl.get("boss"):
        boss_hp = int(lvl.get("hp", 0)); boss_hp_max = boss_hp
        boss_attack_timer = BOSS_ATTACK_INTERVAL
    else:
        boss_hp = 0; boss_hp_max = 0; boss_attack_timer = 0.0

def start_survival():
    global COLS, ROWS, GAME_TIME, board, selected, time_left, app_state
    global animations, particles, hint_pair, hint_timer, net_play, survival_mode
    global boss_hp, boss_hp_max, boss_attack_timer
    global survival_elapsed, survival_spawn_t, survival_stone_t, survival_spawn_interval
    global survival_score
    net_play = False
    survival_mode = True
    COLS = SURVIVAL_COLS
    ROWS = SURVIVAL_ROWS
    GAME_TIME = SURVIVAL_START_TIME
    board = _make_board_for(COLS, ROWS, rocks=0, mixed=True)
    selected = None; time_left = SURVIVAL_START_TIME; app_state = "playing"
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0
    reset_badges(); reset_gold()
    boss_hp = 0; boss_hp_max = 0; boss_attack_timer = 0.0
    survival_elapsed = 0.0
    survival_score = 0
    survival_spawn_interval = SURVIVAL_SPAWN_START
    survival_spawn_t = SURVIVAL_SPAWN_START
    survival_stone_t = SURVIVAL_STONE_EVERY

def restart_level():
    if net_play: return
    if survival_mode:
        start_survival(); return
    start_level(current_level)

def go_to_menu():
    global app_state, selected, animations, particles, hint_pair, hint_timer, survival_mode
    selected = None; app_state = "menu"; survival_mode = False
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0

def go_to_pack_select():
    global app_state, selected, animations, particles, hint_pair, hint_timer, survival_mode
    selected = None; app_state = "pack_select"; survival_mode = False
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0

def go_to_levels():
    global app_state, selected, animations, particles, hint_pair, hint_timer, survival_mode
    selected = None; app_state = "levels"; survival_mode = False
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0

def go_to_prelevel(index):
    global app_state, preview_level, selected, animations, particles, hint_pair, hint_timer, survival_mode
    preview_level = max(0, min(index, len(LEVEL_SETS[current_pack]) - 1))
    selected = None; app_state = "prelevel"; survival_mode = False
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0

def unlock_next_if_needed():
    lvls = LEVEL_SETS[current_pack]
    if current_level == max_unlocked[current_pack] and current_level + 1 < len(lvls):
        max_unlocked[current_pack] = current_level + 1
        save_game()

def shuffle_remaining():
    global golden_cells
    positions, values = [], []
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] > 0:
                positions.append((r, c)); values.append(board[r][c])
    random.shuffle(values)
    for (r, c), v in zip(positions, values):
        board[r][c] = v
    golden_cells = set()

def do_seeded_shuffle(seed):
    rng = random.Random(seed)
    positions, values = [], []
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] > 0:
                positions.append((r, c)); values.append(board[r][c])
    rng.shuffle(values)
    for (r, c), v in zip(positions, values):
        board[r][c] = v

def count_available_moves():
    by_type = {}
    for r in range(ROWS):
        for c in range(COLS):
            v = board[r][c]
            if v <= 0: continue
            by_type.setdefault(v, []).append((r, c))
    total = 0
    for positions in by_type.values():
        n = len(positions)
        for i in range(n):
            for j in range(i + 1, n):
                if find_path(positions[i], positions[j]):
                    total += 1
                    if total >= 3:
                        return total
    return total

def do_auto_shuffle_local():
    for _ in range(30):
        shuffle_remaining()
        if count_available_moves() > 0:
            return True
    return False

def try_auto_shuffle_if_stuck():
    global app_state
    if board_empty(): return False
    cnt = count_available_moves()
    if cnt > 0: return False
    if net_play:
        if not net_is_host: return False
        for _ in range(30):
            seed = random.randint(0, 2**31 - 1)
            backup = [row[:] for row in board]
            do_seeded_shuffle(seed)
            if count_available_moves() > 0:
                net_send(f"SHUFFLE {seed}"); play("shuffle")
                return True
            for r in range(ROWS):
                for c in range(COLS):
                    board[r][c] = backup[r][c]
        return False
    else:
        if do_auto_shuffle_local():
            play("shuffle"); return True
        return False

def check_and_handle_stuck():
    if not net_play or not net_is_host: return
    if net_mode != "coop": return
    try_auto_shuffle_if_stuck()

def find_hint():
    by_type = {}
    for r in range(ROWS):
        for c in range(COLS):
            v = board[r][c]
            if v <= 0: continue
            by_type.setdefault(v, []).append((r, c))
    for positions in by_type.values():
        n = len(positions)
        for i in range(n):
            for j in range(i + 1, n):
                if find_path(positions[i], positions[j]): return (positions[i], positions[j])
    return None

def find_any_removable_pair():
    by_type = {}
    for r in range(ROWS):
        for c in range(COLS):
            v = board[r][c]
            if v <= 0: continue
            by_type.setdefault(v, []).append((r, c))
    for v, positions in by_type.items():
        if len(positions) >= 2: return (positions[0], positions[1], v)
    return None

def trigger_hint():
    global hint_pair, hint_timer
    h = find_hint()
    if h:
        hint_pair = h; hint_timer = 2.0; return True
    return False

def skill_can_use(name):
    if net_play: return False
    if survival_mode: return False
    if badges[name] > 0: return True
    return total_score >= PRICES[name]

def skill_charge(name):
    global total_score
    if badges[name] > 0: badges[name] -= 1
    elif total_score >= PRICES[name]:
        total_score -= PRICES[name]; save_game()

def try_use_hint():
    if net_play: return
    if survival_mode: return
    if not skill_can_use("hint"): return
    if trigger_hint(): skill_charge("hint"); play("hint")

def try_use_shuffle():
    if net_play: return
    if survival_mode: return
    if not skill_can_use("shuffle"): return
    skill_charge("shuffle"); shuffle_remaining(); play("shuffle")
    try_auto_shuffle_if_stuck()

def try_use_bomb():
    global total_score, boss_hp, app_state
    if net_play: return
    if survival_mode: return
    if not skill_can_use("bomb"): return
    pair = find_any_removable_pair()
    if not pair: return
    a, b, tile = pair
    skill_charge("bomb")
    board[a[0]][a[1]] = 0; board[b[0]][b[1]] = 0
    total_score += 1; save_game()
    if is_boss_level():
        boss_hp = max(0, boss_hp - BOSS_HP_PER_PAIR)
    path = [(a[0] + 1, a[1] + 1), (b[0] + 1, b[1] + 1)]
    start_animation(a, b, path, tile); play("bomb")
    if is_boss_level() and boss_hp <= 0:
        app_state = "win"; unlock_next_if_needed(); play("win"); return
    try_auto_shuffle_if_stuck()

def find_path(a, b):
    ar, ac = a[0] + 1, a[1] + 1
    br, bc = b[0] + 1, b[1] + 1

    def free(r, c):
        if r < 0 or r >= ROWS + 2 or c < 0 or c >= COLS + 2: return False
        if r == 0 or r == ROWS + 1 or c == 0 or c == COLS + 1: return True
        if (r, c) == (ar, ac) or (r, c) == (br, bc): return True
        v = board[r - 1][c - 1]
        if v < 0: return False
        return v == 0

    def line_clear(r1, c1, r2, c2):
        if r1 == r2:
            lo, hi = min(c1, c2), max(c1, c2)
            for c in range(lo + 1, hi):
                if not free(r1, c): return False
            return True
        if c1 == c2:
            lo, hi = min(r1, r2), max(r1, r2)
            for r in range(lo + 1, hi):
                if not free(r, c1): return False
            return True
        return False

    if ar == br and line_clear(ar, ac, br, bc): return [(ar, ac), (br, bc)]
    if ac == bc and line_clear(ar, ac, br, bc): return [(ar, ac), (br, bc)]
    for (cr, cc) in [(ar, bc), (br, ac)]:
        if free(cr, cc) and line_clear(ar, ac, cr, cc) and line_clear(cr, cc, br, bc):
            return [(ar, ac), (cr, cc), (br, bc)]
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        r, c = ar + dr, ac + dc
        while free(r, c):
            if r == br and line_clear(r, c, br, bc): return [(ar, ac), (r, c), (br, bc)]
            if c == bc and line_clear(r, c, br, bc): return [(ar, ac), (r, c), (br, bc)]
            for (cr, cc) in [(r, bc), (br, c)]:
                if free(cr, cc) and line_clear(r, c, cr, cc) and line_clear(cr, cc, br, bc):
                    return [(ar, ac), (r, c), (cr, cc), (br, bc)]
            r += dr; c += dc
    return None

def board_empty():
    for row in board:
        for v in row:
            if v > 0: return False
    return True

def board_empty_ref(b):
    for row in b:
        for v in row:
            if v > 0: return False
    return True

def path_length(pts):
    total = 0.0
    for i in range(len(pts) - 1):
        total += math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1])
    return total

def point_at_distance(pts, d):
    if d <= 0: return pts[0]
    total = 0.0
    for i in range(len(pts) - 1):
        dx = pts[i+1][0] - pts[i][0]; dy = pts[i+1][1] - pts[i][1]
        seg = math.hypot(dx, dy)
        if total + seg >= d and seg > 0:
            tt = (d - total) / seg
            return (pts[i][0] + dx * tt, pts[i][1] + dy * tt)
        total += seg
    return pts[-1]

def spawn_explosion(x, y, tile_id):
    color = particle_color(tile_id)
    for _ in range(22):
        ang = random.random() * math.tau
        speed = random.uniform(80, 340)
        particles.append({
            'x': x, 'y': y,
            'vx': math.cos(ang) * speed, 'vy': math.sin(ang) * speed,
            'life': random.uniform(0.4, 0.9), 'max_life': 0.9,
            'color': color, 'radius': random.uniform(2, 6),
        })

def start_animation(a, b, path, tile):
    animations.append({
        'a': a, 'b': b, 'tile': tile, 'path': path,
        'progress': 0.0, 'duration': 0.35, 'spawned': False,
    })

def update_animations(dt, tile_size, offset_x, offset_y):
    for anim in animations[:]:
        anim['progress'] += dt / anim['duration']
        if anim['progress'] >= 1.0 and not anim['spawned']:
            anim['spawned'] = True
            path_px = [(offset_x + (c - 1) * tile_size + tile_size // 2,
                        offset_y + (r - 1) * tile_size + tile_size // 2)
                       for (r, c) in anim['path']]
            total = path_length(path_px)
            mx, my = point_at_distance(path_px, total / 2)
            spawn_explosion(mx, my, anim['tile'])
        if anim['progress'] >= 1.0:
            animations.remove(anim)

def update_particles(dt):
    for p in particles[:]:
        p['life'] -= dt
        if p['life'] <= 0:
            particles.remove(p); continue
        p['x'] += p['vx'] * dt; p['y'] += p['vy'] * dt
        p['vy'] += 500 * dt
        p['vx'] *= 0.97; p['vy'] *= 0.97

def apply_remote_match_coop(r1, c1, r2, c2):
    global mp_peer_score
    if not (0 <= r1 < ROWS and 0 <= c1 < COLS and 0 <= r2 < ROWS and 0 <= c2 < COLS): return
    tile = board[r1][c1]
    if tile <= 0: return
    if board[r2][c2] != tile: return
    board[r1][c1] = 0; board[r2][c2] = 0
    path = [(r1 + 1, c1 + 1), (r2 + 1, c2 + 1)]
    start_animation((r1, c1), (r2, c2), path, tile); play("match")
    if net_play:
        mp_peer_score += 1; check_and_handle_stuck()

def apply_remote_match_vs(r1, c1, r2, c2):
    global vs_peer_board, mp_peer_score
    if vs_peer_board is None: return
    if not (0 <= r1 < ROWS and 0 <= c1 < COLS and 0 <= r2 < ROWS and 0 <= c2 < COLS): return
    tile = vs_peer_board[r1][c1]
    if tile <= 0: return
    if vs_peer_board[r2][c2] != tile: return
    vs_peer_board[r1][c1] = 0; vs_peer_board[r2][c2] = 0
    mp_peer_score += 1

def _start_mp_level(idx, cols, rows, time_s, board_csv):
    global COLS, ROWS, GAME_TIME, board, selected, time_left, app_state
    global animations, particles, hint_pair, hint_timer, net_play, survival_mode
    global mp_level_index, mp_my_score, mp_peer_score, vs_peer_board
    COLS = cols; ROWS = rows; GAME_TIME = time_s
    board = csv_to_board(board_csv, cols, rows)
    vs_peer_board = csv_to_board(board_csv, cols, rows) if net_mode == "versus" else None
    time_left = GAME_TIME; selected = None
    animations = []; particles = []; hint_pair = None; hint_timer = 0.0
    net_play = True; survival_mode = False
    mp_level_index = idx; mp_my_score = 0; mp_peer_score = 0
    reset_badges(); reset_gold(); app_state = "playing"

def handle_net_msg(msg):
    global app_state, mp_peer_score, net_mode, current_pack
    global vs_fog_t, vs_shake_t, vs_lock_t
    global vs_my_rounds, vs_peer_rounds
    global vs_attack_msg, vs_attack_timer

    if msg.startswith("START_COOP "):
        parts = msg[11:].split(" ", 4)
        if len(parts) < 5: return
        try:
            net_mode = "coop"; current_pack = "mid"
            idx = int(parts[0]); cols = int(parts[1]); rows = int(parts[2])
            time_s = int(parts[3]); csv = parts[4]
            _start_mp_level(idx, cols, rows, time_s, csv)
        except Exception: pass
    elif msg.startswith("START_VS "):
        parts = msg[9:].split(" ", 4)
        if len(parts) < 5: return
        try:
            net_mode = "versus"
            idx = int(parts[0]); cols = int(parts[1]); rows = int(parts[2])
            time_s = int(parts[3]); csv = parts[4]
            current_pack = VS_LEVELS[idx].get("pack", "kids") if 0 <= idx < len(VS_LEVELS) else "kids"
            _start_mp_level(idx, cols, rows, time_s, csv)
        except Exception: pass
    elif msg.startswith("MATCH "):
        parts = msg[6:].split()
        if len(parts) < 4: return
        try:
            r1, c1, r2, c2 = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            if net_mode == "versus": apply_remote_match_vs(r1, c1, r2, c2)
            else: apply_remote_match_coop(r1, c1, r2, c2)
        except Exception: pass
    elif msg.startswith("SHUFFLE "):
        try:
            seed = int(msg[8:].strip()); do_seeded_shuffle(seed); play("shuffle")
        except Exception: pass
    elif msg == "VS_FOG":
        vs_fog_t = VS_SKILLS["fog"]["duration"]
        vs_attack_msg = t("vs_peer_fog"); vs_attack_timer = 2.5; play("vs_hit")
    elif msg == "VS_SHAKE":
        vs_shake_t = VS_SKILLS["shake"]["duration"]
        vs_attack_msg = t("vs_peer_shake"); vs_attack_timer = 2.5; play("vs_hit")
    elif msg == "VS_LOCK":
        vs_lock_t = VS_SKILLS["lock"]["duration"]
        vs_attack_msg = t("vs_peer_lock"); vs_attack_timer = 2.5; play("vs_hit")
    elif msg == "PAUSE":
        if net_play and app_state == "playing": app_state = "remote_paused"
    elif msg == "RESUME":
        if net_play and app_state == "remote_paused": app_state = "playing"
    elif msg == "QUIT":
        net_close(); go_to_menu()

# ============================================================
# BOSS ATTACKS
# ============================================================
def boss_do_attack():
    global boss_attack_timer, time_left
    global vs_fog_t, vs_shake_t, vs_lock_t, vs_attack_msg, vs_attack_timer
    atk = random.choice(["rocks", "time", "fog", "shake", "lock"])
    if atk == "rocks":
        empties = [(r, c) for r in range(ROWS) for c in range(COLS) if board[r][c] == 0]
        if len(empties) >= 2:
            random.shuffle(empties)
            for (r, c) in empties[:2]:
                board[r][c] = -1
            try_auto_shuffle_if_stuck()
        vs_attack_msg = t("boss_msg_rocks")
    elif atk == "time":
        time_left = max(0.0, time_left - 10.0)
        vs_attack_msg = t("boss_msg_time")
    elif atk == "fog":
        vs_fog_t = 5.0
        vs_attack_msg = t("boss_msg_fog")
    elif atk == "shake":
        vs_shake_t = 5.0
        vs_attack_msg = t("boss_msg_shake")
    elif atk == "lock":
        vs_lock_t = 5.0
        vs_attack_msg = t("boss_msg_lock")
    vs_attack_timer = 2.5
    boss_attack_timer = BOSS_ATTACK_INTERVAL
    play("vs_hit")

# ============================================================
# SURVIVAL HELPERS
# ============================================================
def survival_spawn_tiles():
    empties = [(r, c) for r in range(ROWS) for c in range(COLS) if board[r][c] == 0]
    if len(empties) < 4:
        return
    random.shuffle(empties)
    for _ in range(2):
        if len(empties) < 2: break
        tile_id = random.randint(MIX_TILE_MIN, MIX_TILE_MAX)
        a = empties.pop(); b = empties.pop()
        board[a[0]][a[1]] = tile_id
        board[b[0]][b[1]] = tile_id
    try_auto_shuffle_if_stuck()

def survival_spawn_stone():
    empties = [(r, c) for r in range(ROWS) for c in range(COLS) if board[r][c] == 0]
    if not empties: return
    random.shuffle(empties)
    r, c = empties[0]
    board[r][c] = -1
    try_auto_shuffle_if_stuck()

# ============================================================
# GOLDEN TILES
# ============================================================
def spawn_golden_tile():
    global golden_cells
    if len(golden_cells) >= GOLD_MAX: return False
    normal = []
    for r in range(ROWS):
        for c in range(COLS):
            v = board[r][c]
            if v > 0 and (r, c) not in golden_cells:
                normal.append((r, c))
    if not normal: return False
    r, c = random.choice(normal)
    tile_id = board[r][c]
    golden_cells.add((r, c))
    has_pair = False
    for rr in range(ROWS):
        for cc in range(COLS):
            if (rr, cc) == (r, c): continue
            if board[rr][cc] == tile_id:
                has_pair = True; break
        if has_pair: break
    if not has_pair:
        empty = [(rr, cc) for rr in range(ROWS) for cc in range(COLS) if board[rr][cc] == 0]
        if empty:
            er, ec = random.choice(empty)
            board[er][ec] = tile_id
            golden_cells.add((er, ec))
    return True

def is_golden(r, c):
    return (r, c) in golden_cells

# ============================================================
# LAYOUT
# ============================================================
def compute_layout():
    sw, sh = screen.get_size()
    if is_boss_level():
        hud_h = max(90, sh // 9)
    else:
        hud_h = max(60, sh // 12)
    # В режиме выживания панели скиллов нет — всё место полю
    if survival_mode:
        skill_h = 0
    else:
        skill_h = max(90, sh // 8)
    play_h = sh - hud_h - skill_h
    tile_size = min(sw // (COLS + 2), play_h // (ROWS + 2))
    board_w = COLS * tile_size; board_h = ROWS * tile_size
    offset_x = (sw - board_w) // 2
    offset_y = hud_h + (play_h - board_h) // 2
    return sw, sh, hud_h, skill_h, tile_size, offset_x, offset_y

def compute_vs_layout():
    sw, sh = screen.get_size()
    hud_h = max(70, sh // 10); skill_h = max(90, sh // 8)
    play_h = sh - hud_h - skill_h
    half_w = sw // 2; pad = 20
    tile_size = min((half_w - pad * 2) // (COLS + 2), (play_h - pad * 2) // (ROWS + 2))
    tile_size = max(20, tile_size)
    board_w = COLS * tile_size; board_h = ROWS * tile_size
    my_ox = half_w // 2 - board_w // 2
    peer_ox = half_w + half_w // 2 - board_w // 2
    common_oy = hud_h + (play_h - board_h) // 2
    return sw, sh, hud_h, skill_h, tile_size, my_ox, common_oy, peer_ox, common_oy, half_w

def timer_bar_rect(sw, hud_h, boss=False):
    bar_w = min(int(sw * 0.40), 460)
    bar_h = int(hud_h * (0.35 if boss else 0.50))
    if boss:
        return pygame.Rect((sw - bar_w) // 2, int(hud_h * 0.10), bar_w, bar_h)
    return pygame.Rect((sw - bar_w) // 2, (hud_h - bar_h) // 2, bar_w, bar_h)

def hud_menu_button_rect(sw, hud_h):
    btn_size = hud_h - 20
    if btn_size < 30: btn_size = 30
    return pygame.Rect(sw - btn_size - 12, (hud_h - btn_size) // 2, btn_size, btn_size)

def skill_button_rects(sw, sh, skill_h):
    btn_w = min(260, (sw - 80) // 3 - 10); btn_h = skill_h - 20
    gap = 20; total_w = btn_w * 3 + gap * 2
    x0 = sw // 2 - total_w // 2; y0 = sh - skill_h + 10
    return (
        pygame.Rect(x0, y0, btn_w, btn_h),
        pygame.Rect(x0 + btn_w + gap, y0, btn_w, btn_h),
        pygame.Rect(x0 + (btn_w + gap) * 2, y0, btn_w, btn_h),
    )

def vs_skill_button_rects(sw, sh, skill_h):
    btn_w = min(220, (sw - 80) // 3 - 10); btn_h = skill_h - 20
    gap = 20; total_w = btn_w * 3 + gap * 2
    x0 = sw // 2 - total_w // 2; y0 = sh - skill_h + 10
    return [
        ("fog",   pygame.Rect(x0, y0, btn_w, btn_h)),
        ("shake", pygame.Rect(x0 + btn_w + gap, y0, btn_w, btn_h)),
        ("lock",  pygame.Rect(x0 + (btn_w + gap) * 2, y0, btn_w, btn_h)),
    ]

def overlay_button_rect(sw, sh):
    btn_w, btn_h = 340, 70
    return pygame.Rect(sw // 2 - btn_w // 2, sh // 2 + 100, btn_w, btn_h)

def menu_button_rects(sw, sh):
    btn_w = min(360, sw - 80); btn_h = 74; gap = 18
    total_h = btn_h * 4 + gap * 3
    x = sw // 2 - btn_w // 2; y0 = sh // 2 - total_h // 2 + 70
    return (
        pygame.Rect(x, y0, btn_w, btn_h),
        pygame.Rect(x, y0 + (btn_h + gap), btn_w, btn_h),
        pygame.Rect(x, y0 + (btn_h + gap) * 2, btn_w, btn_h),
        pygame.Rect(x, y0 + (btn_h + gap) * 3, btn_w, btn_h),
    )

def menu_sound_button_rect(sw, sh):
    return pygame.Rect(sw - 48 - 16, 16, 48, 48)

def pack_button_rects(sw, sh):
    bw = min(400, sw - 80); bh = 78; gap = 18
    total_h = bh * 4 + gap * 3
    x = sw // 2 - bw // 2
    y0 = sh // 2 - total_h // 2 + 10
    back_w, back_h = 200, 54
    back_r = pygame.Rect(sw // 2 - back_w // 2, y0 + total_h + 20, back_w, back_h)
    return (
        pygame.Rect(x, y0, bw, bh),
        pygame.Rect(x, y0 + bh + gap, bw, bh),
        pygame.Rect(x, y0 + (bh + gap) * 2, bw, bh),
        pygame.Rect(x, y0 + (bh + gap) * 3, bw, bh),
        back_r,
    )

def level_button_rects(sw, sh):
    lvls = LEVEL_SETS[current_pack]
    n = len(lvls)
    gap = 12; margin = 60
    btn_w = min(160, (sw - margin * 2 - gap * (n - 1)) // n)
    btn_h = 170
    total_w = btn_w * n + gap * (n - 1)
    x0 = sw // 2 - total_w // 2; y0 = sh // 2 - btn_h // 2
    rects = [pygame.Rect(x0 + i * (btn_w + gap), y0, btn_w, btn_h) for i in range(n)]
    back_w, back_h = 200, 60
    back_r = pygame.Rect(sw // 2 - back_w // 2, y0 + btn_h + 50, back_w, back_h)
    return rects, back_r

def prelevel_button_rects(sw, sh):
    btn_w, btn_h = 260, 72; gap = 40
    total_w = btn_w * 2 + gap
    x0 = sw // 2 - total_w // 2; y0 = sh // 2 + 190
    return pygame.Rect(x0, y0, btn_w, btn_h), pygame.Rect(x0 + btn_w + gap, y0, btn_w, btn_h)

def mp_menu_button_rects(sw, sh):
    btn_w, btn_h = 340, 80; gap = 20
    total_h = btn_h * 3 + gap * 2
    x = sw // 2 - btn_w // 2; y0 = sh // 2 - total_h // 2 + 60
    return (
        pygame.Rect(x, y0, btn_w, btn_h),
        pygame.Rect(x, y0 + btn_h + gap, btn_w, btn_h),
        pygame.Rect(x, y0 + (btn_h + gap) * 2, btn_w, btn_h),
    )

def mp_host_start_button_rect(sw, sh):
    return pygame.Rect(sw // 2 - 150, sh // 2 + 160, 300, 70)

def mp_host_mode_rects(sw, sh):
    btn_w, btn_h = 240, 60; gap = 20
    total_w = btn_w * 2 + gap
    x0 = sw // 2 - total_w // 2; y0 = sh // 2 + 70
    return pygame.Rect(x0, y0, btn_w, btn_h), pygame.Rect(x0 + btn_w + gap, y0, btn_w, btn_h)

def mp_cancel_button_rect(sw, sh):
    return pygame.Rect(sw // 2 - 130, sh // 2 + 250, 260, 70)

def mp_connect_buttons(sw, sh):
    btn_w, btn_h = 200, 60; gap = 20
    total_w = btn_w * 3 + gap * 2
    x0 = sw // 2 - total_w // 2; y0 = sh - 90
    return (
        pygame.Rect(x0, y0, btn_w, btn_h),
        pygame.Rect(x0 + btn_w + gap, y0, btn_w, btn_h),
        pygame.Rect(x0 + (btn_w + gap) * 2, y0, btn_w, btn_h),
    )

def mp_ip_field_rect(sw, sh):
    return pygame.Rect(sw // 2 - 210, sh - 180, 420, 60)

def mp_scan_list_rects(sw, sh):
    item_w = 480; item_h = 52; gap = 8
    x0 = sw // 2 - item_w // 2; y0 = 190
    return [pygame.Rect(x0, y0 + i * (item_h + gap), item_w, item_h) for i in range(4)]

def pause_button_rects(sw, sh):
    btn_w, btn_h = 320, 72; gap = 20
    total_h = btn_h * 3 + gap * 2
    x = sw // 2 - btn_w // 2; y0 = sh // 2 - total_h // 2 + 50
    return (
        pygame.Rect(x, y0, btn_w, btn_h),
        pygame.Rect(x, y0 + btn_h + gap, btn_w, btn_h),
        pygame.Rect(x, y0 + (btn_h + gap) * 2, btn_w, btn_h),
    )

def pause_button_rects_net(sw, sh):
    btn_w, btn_h = 320, 72; gap = 20
    total_h = btn_h * 2 + gap
    x = sw // 2 - btn_w // 2; y0 = sh // 2 - total_h // 2 + 50
    return pygame.Rect(x, y0, btn_w, btn_h), pygame.Rect(x, y0 + btn_h + gap, btn_w, btn_h)

# ============================================================
# DRAWING
# ============================================================
def draw_star_shape(surface, cx, cy, size, color):
    pts = []
    for i in range(10):
        ang = -math.pi/2 + i * math.pi / 5
        rr = size * (0.5 if i % 2 == 0 else 0.22)
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, (140, 90, 10), pts, 2)

def draw_gold_overlay(surface, x, y, tile_size, pulse):
    alpha = int(170 + 85 * pulse)
    glow = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    pygame.draw.rect(glow, (255, 210, 40, alpha),
                     (2, 2, tile_size - 4, tile_size - 4), width=7, border_radius=8)
    pygame.draw.rect(glow, (200, 140, 10, alpha),
                     (2, 2, tile_size - 4, tile_size - 4), width=2, border_radius=8)
    surface.blit(glow, (x, y))
    star_size = max(8, tile_size // 6)
    sx = x + tile_size - star_size - 4
    sy = y + 4 + star_size // 2
    draw_star_shape(surface, sx + star_size // 2, sy, star_size, (255, 230, 80))

def draw_tile_at(surface, tile, cx, cy, tile_size):
    x = cx - tile_size / 2; y = cy - tile_size / 2
    if tile == -1:
        blit_icon_entry(surface, get_icon(-1, tile_size - 4), x + 2, y + 2); return
    pygame.draw.rect(surface, TILE_BG, (x + 2, y + 2, tile_size - 4, tile_size - 4), border_radius=8)
    blit_icon_entry(surface, get_icon(tile, tile_size - 16), x + 8, y + 8)

def draw_board_ref(surface, b, tile_size, offset_x, offset_y, dim=False, shake=False):
    sx, sy = offset_x, offset_y
    if shake:
        t_sh = pygame.time.get_ticks() / 1000.0
        sx += int(math.sin(t_sh * 40) * tile_size * 0.15)
        sy += int(math.cos(t_sh * 33) * tile_size * 0.12)
    for row in range(ROWS):
        for col in range(COLS):
            tile = b[row][col]
            if tile == 0: continue
            x = sx + col * tile_size; y = sy + row * tile_size
            if tile == -1:
                blit_icon_entry(surface, get_icon(-1, tile_size - 4), x + 2, y + 2); continue
            pygame.draw.rect(surface, TILE_BG, (x + 2, y + 2, tile_size - 4, tile_size - 4), border_radius=8)
            blit_icon_entry(surface, get_icon(tile, tile_size - 16), x + 8, y + 8)
    if dim:
        ov = pygame.Surface((COLS * tile_size, ROWS * tile_size), pygame.SRCALPHA)
        ov.fill((255, 255, 255, 245)); surface.blit(ov, (sx, sy))

def draw_board(surface, tile_size, offset_x, offset_y, shake=False):
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.010)
    gold_pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
    sx, sy = offset_x, offset_y
    if shake:
        t_sh = pygame.time.get_ticks() / 1000.0
        sx += int(math.sin(t_sh * 40) * tile_size * 0.15)
        sy += int(math.cos(t_sh * 33) * tile_size * 0.12)
    for row in range(ROWS):
        for col in range(COLS):
            tile = board[row][col]
            if tile == 0: continue
            x = sx + col * tile_size; y = sy + row * tile_size
            if tile == -1:
                blit_icon_entry(surface, get_icon(-1, tile_size - 4), x + 2, y + 2); continue
            pygame.draw.rect(surface, TILE_BG, (x + 2, y + 2, tile_size - 4, tile_size - 4), border_radius=8)
            blit_icon_entry(surface, get_icon(tile, tile_size - 16), x + 8, y + 8)
            if is_golden(row, col):
                draw_gold_overlay(surface, x, y, tile_size, gold_pulse)
            if selected == (row, col):
                pygame.draw.rect(surface, (255, 230, 80),
                                 (x + 2, y + 2, tile_size - 4, tile_size - 4), width=4, border_radius=8)
            if hint_pair and (row, col) in hint_pair:
                alpha = int(160 + 95 * pulse)
                glow = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 40, 40, alpha),
                                 (2, 2, tile_size - 4, tile_size - 4), width=7, border_radius=8)
                pygame.draw.rect(glow, (90, 0, 0, alpha),
                                 (2, 2, tile_size - 4, tile_size - 4), width=2, border_radius=8)
                surface.blit(glow, (x, y))

def draw_animations(surface, tile_size, offset_x, offset_y):
    for anim in animations:
        path_px = [(offset_x + (c - 1) * tile_size + tile_size // 2,
                    offset_y + (r - 1) * tile_size + tile_size // 2) for (r, c) in anim['path']]
        total = path_length(path_px)
        half = total * min(anim['progress'], 1.0) / 2.0
        ax, ay = point_at_distance(path_px, half)
        bx, by = point_at_distance(path_px, total - half)
        draw_tile_at(surface, anim['tile'], ax, ay, tile_size)
        draw_tile_at(surface, anim['tile'], bx, by, tile_size)

def draw_particles(surface):
    for p in particles:
        alpha = max(0.0, p['life'] / p['max_life'])
        r = max(1, int(p['radius'] * alpha))
        pygame.draw.circle(surface, p['color'], (int(p['x']), int(p['y'])), r)

def draw_cloud_overlay(surface, board_rect, t_remain, t_total):
    if t_total <= 0: return
    k = 1.0 - (t_remain / t_total)
    appear = min(1.0, k / 0.2) if k < 0.2 else 1.0
    leave = 1.0
    if k > 0.8: leave = max(0.0, 1.0 - (k - 0.8) / 0.2)
    alpha = int(255 * appear * leave)
    cloud = pygame.Surface((board_rect.width, board_rect.height), pygame.SRCALPHA)
    cloud.fill((255, 255, 255, alpha))
    for i in range(6):
        cx = int((i + 0.5) * board_rect.width / 6)
        r = int(board_rect.width * 0.12)
        pygame.draw.circle(cloud, (255, 255, 255, alpha), (cx, int(r * 0.3)), r)
    surface.blit(cloud, (board_rect.x, board_rect.y))

def draw_hamburger(surface, rect, color):
    cx, cy = rect.centerx, rect.centery
    w = rect.width // 2; h = max(3, rect.width // 12); gap = rect.width // 5
    for k in (-1, 0, 1):
        pygame.draw.rect(surface, color, pygame.Rect(cx - w, cy + k * gap - h // 2, w * 2, h), border_radius=2)

def draw_coin(surface, cx, cy, r):
    pygame.draw.circle(surface, (255, 210, 40), (cx, cy), r)
    pygame.draw.circle(surface, (180, 130, 10), (cx, cy), r, 2)

def draw_skill_button(surface, rect, kind, label_key):
    active = skill_can_use(kind)
    bg = TILE_BG if active else (170, 170, 170)
    border = (30, 60, 90) if active else (100, 100, 100)
    pygame.draw.rect(surface, bg, rect, border_radius=12)
    pygame.draw.rect(surface, border, rect, width=4, border_radius=12)

    icon_size = 44
    price_txt = FONT_MED.render(str(PRICES[kind]), True, (30, 60, 90) if active else (90, 90, 90))
    coin_r = 12
    gap1 = 14
    gap2 = 10
    total_w = icon_size + gap1 + price_txt.get_width() + gap2 + coin_r * 2
    start_x = rect.centerx - total_w // 2
    icon_cy = rect.centery
    entry = get_system_icon(f"skill_{kind}", icon_size)
    if entry is not None:
        blit_icon_entry(surface, entry, start_x, icon_cy - icon_size // 2)
    price_x = start_x + icon_size + gap1
    surface.blit(price_txt, (price_x, icon_cy - price_txt.get_height() // 2))
    coin_x = price_x + price_txt.get_width() + gap2 + coin_r
    draw_coin(surface, coin_x, icon_cy, coin_r)

    badge_val = badges[kind]
    bx, by = rect.x + 14, rect.y + 14; br = 12
    pygame.draw.circle(surface, (40, 40, 60), (bx, by), br)
    pygame.draw.circle(surface, (255, 255, 255), (bx, by), br, 2)
    bt = FONT_XS.render(str(badge_val), True, (255, 255, 255))
    surface.blit(bt, (bx - bt.get_width() // 2, by - bt.get_height() // 2))
    letter = SKILL_KEYS[kind]
    kw, kh = 24, 20; kx = rect.x + 8; ky = rect.bottom - kh - 6
    pygame.draw.rect(surface, (30, 60, 90) if active else (100, 100, 100), (kx, ky, kw, kh), border_radius=4)
    lt = FONT_XS.render(letter, True, (255, 255, 255))
    surface.blit(lt, (kx + kw // 2 - lt.get_width() // 2, ky + kh // 2 - lt.get_height() // 2))

def draw_vs_skill_button(surface, rect, kind):
    cd = vs_my_cd.get(kind, 0.0); ready = cd <= 0.0
    bg = TILE_BG if ready else (170, 170, 170)
    border = (120, 40, 90) if ready else (100, 100, 100)
    pygame.draw.rect(surface, bg, rect, border_radius=12)
    pygame.draw.rect(surface, border, rect, width=4, border_radius=12)
    icon_cx = rect.x + 46; icon_cy = rect.centery; icon_size = 36
    entry = get_system_icon(f"skill_{kind}", icon_size)
    if entry is not None:
        blit_icon_entry(surface, entry, icon_cx - icon_size // 2, icon_cy - icon_size // 2)
    label_map = {"fog": "Туман", "shake": "Тряска", "lock": "Блок"}
    lab = FONT_SM.render(label_map.get(kind, kind), True, (30, 60, 90) if ready else (90, 90, 90))
    surface.blit(lab, (rect.centerx - lab.get_width() // 2 + 10, rect.centery - lab.get_height() // 2))
    if not ready:
        bar_w = rect.width - 8
        pygame.draw.rect(surface, (80, 80, 80), pygame.Rect(rect.x + 4, rect.bottom - 8, bar_w, 4), border_radius=2)
        max_cd = VS_SKILLS[kind]["cd"]
        frac = 1.0 - (cd / max_cd) if max_cd > 0 else 1.0
        pygame.draw.rect(surface, (80, 180, 100),
                         pygame.Rect(rect.x + 4, rect.bottom - 8, int(bar_w * frac), 4), border_radius=2)

def draw_hud(surface, sw, hud_h, time_left):
    boss = is_boss_level() and boss_hp_max > 0
    bar = timer_bar_rect(sw, hud_h, boss=boss)
    frozen = freeze_t > 0
    pygame.draw.rect(surface, (90, 30, 30), bar, border_radius=bar.height // 2)
    if frozen:
        pygame.draw.rect(surface, (30, 60, 140), bar, border_radius=bar.height // 2)
    frac = max(0.0, min(1.0, time_left / GAME_TIME)) if GAME_TIME > 0 else 0
    fill_w = int(bar.width * frac)
    if fill_w > 4:
        col = (90, 180, 240) if frozen else (230, 60, 60)
        pygame.draw.rect(surface, col, (bar.x, bar.y, fill_w, bar.height), border_radius=bar.height // 2)
    secs = int(math.ceil(time_left))
    txt = FONT_SM.render(f"{secs}s", True, (255, 255, 255))
    surface.blit(txt, (bar.centerx - txt.get_width() // 2, bar.centery - txt.get_height() // 2))

    if boss:
        hp_bar = pygame.Rect(bar.x, bar.y + bar.height + 8, bar.width, max(12, hud_h // 5))
        pygame.draw.rect(surface, (40, 20, 20), hp_bar, border_radius=hp_bar.height // 2)
        hp_frac = max(0.0, min(1.0, boss_hp / boss_hp_max)) if boss_hp_max > 0 else 0
        hp_fill_w = int(hp_bar.width * hp_frac)
        if hp_fill_w > 4:
            pygame.draw.rect(surface, (200, 40, 40),
                             (hp_bar.x, hp_bar.y, hp_fill_w, hp_bar.height),
                             border_radius=hp_bar.height // 2)
        pygame.draw.rect(surface, (255, 200, 200), hp_bar, width=2, border_radius=hp_bar.height // 2)
        hp_txt = FONT_XS.render(f"{t('boss')}: {boss_hp}/{boss_hp_max}", True, (255, 255, 255))
        surface.blit(hp_txt, (hp_bar.centerx - hp_txt.get_width() // 2,
                              hp_bar.centery - hp_txt.get_height() // 2))

    if net_play and net_mode == "coop":
        lvl_lbl = f"{t('mp_play')} — {t('level')} {mp_level_index + 1}/{len(LEVELS)}"
    elif net_play and net_mode == "versus":
        lvl_lbl = f"VS — {t('vs_round')} {mp_level_index + 1}/{len(VS_LEVELS)}"
    elif survival_mode:
        minutes = int(survival_elapsed // 60)
        lvl_lbl = t("survival_hud").format(m=minutes)
    else:
        lvls = LEVEL_SETS[current_pack]
        if is_boss_level():
            lvl_lbl = f"{pack_name(current_pack)} — {t('boss')}"
        else:
            lvl_lbl = f"{pack_name(current_pack)} — {t('level')} {current_level + 1}/{len(lvls)}"
    lvl_txt = FONT_XS.render(lvl_lbl, True, (255, 220, 120))
    surface.blit(lvl_txt, (12, hud_h // 2 - lvl_txt.get_height() - 4))
    if net_play and net_mode == "coop":
        score_txt = FONT_MED.render(f"{t('mp_you')}: {mp_my_score}", True, (255, 255, 255))
        surface.blit(score_txt, (12, hud_h // 2 + 4))
        peer_txt = FONT_XS.render(f"{t('mp_peer')}: {mp_peer_score}", True, (220, 220, 220))
        surface.blit(peer_txt, (12, hud_h // 2 + score_txt.get_height() + 6))
    elif net_play and net_mode == "versus":
        score_txt = FONT_MED.render(f"{t('mp_you')}: {vs_my_rounds} — {t('mp_peer')}: {vs_peer_rounds}", True, (255, 255, 255))
        surface.blit(score_txt, (12, hud_h // 2 + 4))
    elif survival_mode:
        score_txt = FONT_MED.render(f"{t('score')}: {survival_score}", True, (20, 25, 35))
        surface.blit(score_txt, (12, hud_h // 2 + 4))
    else:
        score_txt = FONT_MED.render(f"{t('score')}: {total_score}", True, (20, 25, 35))
        surface.blit(score_txt, (12, hud_h // 2 + 4))
    menu_r = hud_menu_button_rect(sw, hud_h)
    pygame.draw.rect(surface, TILE_BG, menu_r, border_radius=8)
    pygame.draw.rect(surface, (30, 60, 90), menu_r, width=3, border_radius=8)
    draw_hamburger(surface, menu_r, (30, 60, 90))

def draw_skill_panel(surface, sw, sh, skill_h):
    hint_r, shuffle_r, bomb_r = skill_button_rects(sw, sh, skill_h)
    draw_skill_button(surface, hint_r,    "hint",    "hint")
    draw_skill_button(surface, shuffle_r, "shuffle", "shuffle")
    draw_skill_button(surface, bomb_r,    "bomb",    "bomb")

def draw_vs_skill_panel(surface, sw, sh, skill_h):
    for kind, r in vs_skill_button_rects(sw, sh, skill_h):
        draw_vs_skill_button(surface, r, kind)

def draw_attack_banner(surface, sw, hud_h):
    global vs_attack_msg, vs_attack_timer
    if vs_attack_timer <= 0 or not vs_attack_msg: return
    alpha = int(max(0, min(255, min(1.0, vs_attack_timer / 0.7) * 255)))
    txt = FONT_MED.render(vs_attack_msg, True, (255, 255, 255))
    pad = 20
    box_w = txt.get_width() + pad * 2; box_h = txt.get_height() + pad
    bx = sw // 2 - box_w // 2; by = hud_h + 10
    srf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(srf, (200, 30, 30, min(230, alpha)), (0, 0, box_w, box_h), border_radius=14)
    pygame.draw.rect(srf, (255, 255, 255, alpha), (0, 0, box_w, box_h), width=3, border_radius=14)
    surface.blit(srf, (bx, by)); surface.blit(txt, (bx + pad, by + pad // 2))

def draw_my_attack_banner(surface, sw, hud_h):
    global vs_my_attack_msg, vs_my_attack_timer
    if vs_my_attack_timer <= 0 or not vs_my_attack_msg: return
    alpha = int(max(0, min(255, min(1.0, vs_my_attack_timer / 0.7) * 255)))
    txt = FONT_SM.render(vs_my_attack_msg, True, (255, 255, 255))
    pad = 12
    box_w = txt.get_width() + pad * 2; box_h = txt.get_height() + pad
    bx = sw // 2 - box_w // 2; by = hud_h + 70
    srf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(srf, (40, 140, 60, min(220, alpha)), (0, 0, box_w, box_h), border_radius=10)
    surface.blit(srf, (bx, by)); surface.blit(txt, (bx + pad, by + pad // 2))

def draw_freeze_banner(surface, sw, hud_h):
    global freeze_msg_t
    if freeze_msg_t <= 0: return
    alpha = int(max(0, min(255, min(1.0, freeze_msg_t / 0.7) * 255)))
    txt = FONT_MED.render(t("freeze_msg"), True, (255, 255, 255))
    pad = 20
    box_w = txt.get_width() + pad * 2; box_h = txt.get_height() + pad
    bx = sw // 2 - box_w // 2; by = hud_h + 10
    srf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    pygame.draw.rect(srf, (30, 90, 200, min(230, alpha)), (0, 0, box_w, box_h), border_radius=14)
    pygame.draw.rect(srf, (220, 240, 255, alpha), (0, 0, box_w, box_h), width=3, border_radius=14)
    surface.blit(srf, (bx, by)); surface.blit(txt, (bx + pad, by + pad // 2))

def draw_overlay(surface, sw, sh, text, subtext, button_label):
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170)); surface.blit(overlay, (0, 0))
    t1 = FONT_BIG.render(text, True, (255, 255, 255))
    surface.blit(t1, (sw // 2 - t1.get_width() // 2, sh // 2 - 100))
    if subtext:
        t2 = FONT_MED.render(subtext, True, (255, 230, 120))
        surface.blit(t2, (sw // 2 - t2.get_width() // 2, sh // 2 + 10))
    btn = overlay_button_rect(sw, sh)
    pygame.draw.rect(surface, (80, 200, 100), btn, border_radius=12)
    pygame.draw.rect(surface, TILE_BG, btn, width=4, border_radius=12)
    t3 = FONT_MED.render(button_label, True, (255, 255, 255))
    surface.blit(t3, (btn.centerx - t3.get_width() // 2, btn.centery - t3.get_height() // 2))

def draw_mp_result_overlay(surface, sw, sh, is_last):
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190)); surface.blit(overlay, (0, 0))
    if is_last: title_txt = t("mp_final_title"); title_color = (255, 220, 120)
    elif mp_my_score > mp_peer_score: title_txt = t("mp_round_win"); title_color = (180, 255, 180)
    elif mp_my_score < mp_peer_score: title_txt = t("mp_round_lose"); title_color = (255, 180, 180)
    else: title_txt = t("mp_round_draw"); title_color = (230, 230, 230)
    t1 = FONT_BIG.render(title_txt, True, title_color)
    surface.blit(t1, (sw // 2 - t1.get_width() // 2, sh // 2 - 140))
    t2 = FONT_MED.render(f"{t('mp_you')}: {mp_my_score}   —   {t('mp_peer')}: {mp_peer_score}", True, (255, 255, 255))
    surface.blit(t2, (sw // 2 - t2.get_width() // 2, sh // 2 - 20))
    if net_is_host:
        btn = overlay_button_rect(sw, sh)
        pygame.draw.rect(surface, (80, 200, 100), btn, border_radius=12)
        pygame.draw.rect(surface, TILE_BG, btn, width=4, border_radius=12)
        label = t("to_menu") if is_last else t("mp_next_level")
        t3 = FONT_MED.render(label, True, (255, 255, 255))
        surface.blit(t3, (btn.centerx - t3.get_width() // 2, btn.centery - t3.get_height() // 2))
    else:
        t3 = FONT_MED.render(t("mp_wait_next"), True, (200, 220, 255))
        surface.blit(t3, (sw // 2 - t3.get_width() // 2, sh // 2 + 120))

def draw_vs_result_overlay(surface, sw, sh, is_last):
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190)); surface.blit(overlay, (0, 0))
    if is_last:
        if vs_my_rounds > vs_peer_rounds: title = t("vs_you_won"); col = (180, 255, 180)
        elif vs_my_rounds < vs_peer_rounds: title = t("vs_peer_won"); col = (255, 180, 180)
        else: title = t("vs_draw_match"); col = (230, 230, 230)
    else:
        if mp_my_score > mp_peer_score: title = t("vs_win"); col = (180, 255, 180)
        elif mp_my_score < mp_peer_score: title = t("vs_lose"); col = (255, 180, 180)
        else: title = t("vs_draw"); col = (230, 230, 230)
    t1 = FONT_BIG.render(title, True, col)
    surface.blit(t1, (sw // 2 - t1.get_width() // 2, sh // 2 - 140))
    t2 = FONT_MED.render(f"{t('mp_you')}: {vs_my_rounds}    {t('mp_peer')}: {vs_peer_rounds}", True, (255, 255, 255))
    surface.blit(t2, (sw // 2 - t2.get_width() // 2, sh // 2 - 20))
    if net_is_host:
        btn = overlay_button_rect(sw, sh)
        pygame.draw.rect(surface, (80, 200, 100), btn, border_radius=12)
        pygame.draw.rect(surface, TILE_BG, btn, width=4, border_radius=12)
        label = t("to_menu") if is_last else t("mp_next_level")
        t3 = FONT_MED.render(label, True, (255, 255, 255))
        surface.blit(t3, (btn.centerx - t3.get_width() // 2, btn.centery - t3.get_height() // 2))
    else:
        t3 = FONT_MED.render(t("mp_wait_next"), True, (200, 220, 255))
        surface.blit(t3, (sw // 2 - t3.get_width() // 2, sh // 2 + 120))

def draw_menu(surface, sw, sh):
    draw_bg(surface, "bg_menu", sw, sh)
    logo = get_logo()
    if logo is not None:
        lw, lh = logo.get_size()
        max_w = min(600, sw - 100)
        if lw > max_w:
            scale = max_w / lw
            logo = pygame.transform.smoothscale(logo, (max_w, int(lh * scale)))
        rect = logo.get_rect(center=(sw // 2, sh // 2 - 200))
        surface.blit(logo, rect)
    else:
        title = FONT_BIG.render("Pung", True, (255, 255, 255))
        surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 250))
    score_txt = FONT_MED.render(f"{t('score')}: {total_score}", True, (255, 220, 120))
    surface.blit(score_txt, (sw // 2 - score_txt.get_width() // 2, sh // 2 - 150))
    play_r, mp_r, lang_r, exit_r = menu_button_rects(sw, sh)
    _mp_label = t("soon") if IS_ANDROID else t("mp_menu_btn")
    _mp_color = (140, 140, 140) if IS_ANDROID else (120, 100, 220)
    for rect, label, color in [
        (play_r, t("play"),        (80, 200, 100)),
        (mp_r,   _mp_label,        _mp_color),
        (lang_r, t("language"),    (60, 140, 220)),
        (exit_r, t("exit"),        (200, 80, 80))]:
        pygame.draw.rect(surface, color, rect, border_radius=14)
        pygame.draw.rect(surface, TILE_BG, rect, width=4, border_radius=14)
        txt = FONT_MED.render(label, True, (255, 255, 255))
        surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
    snd_r = menu_sound_button_rect(sw, sh)
    pygame.draw.rect(surface, TILE_BG, snd_r, border_radius=10)
    pygame.draw.rect(surface, (30, 60, 90), snd_r, width=3, border_radius=10)
    snd_entry = get_system_icon("sound_off" if sound_enabled else "sound_on", snd_r.width)
    if snd_entry is None:
        snd_entry = get_system_icon("sound_on" if sound_enabled else "sound_off", snd_r.width)
    if snd_entry is not None:
        blit_icon_entry(surface, snd_entry, snd_r.x, snd_r.y)
    credits = FONT_XS.render("was created by Sidius", True, (230, 230, 230))
    surface.blit(credits, (16, sh - credits.get_height() - 12))

def draw_pack_select(surface, sw, sh):
    draw_bg(surface, "bg_menu", sw, sh)
    title = FONT_BIG.render(t("pack_title"), True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 260))
    kids_r, mid_r, ad_r, sv_r, back_r = pack_button_rects(sw, sh)
    for rect, key, color in [
        (kids_r,  "kids",  (80, 200, 100)),
        (mid_r,   "mid",   (100, 160, 220)),
        (ad_r,    "adult", (200, 100, 130))]:
        pygame.draw.rect(surface, color, rect, border_radius=14)
        pygame.draw.rect(surface, TILE_BG, rect, width=4, border_radius=14)
        nm = FONT_MED.render(pack_name(key), True, (255, 255, 255))
        surface.blit(nm, (rect.centerx - nm.get_width() // 2, rect.centery - nm.get_height() // 2))
        total = len(LEVEL_SETS[key]) - 1
        done = min(max_unlocked[key], total)
        ptxt = FONT_XS.render(f"{done} / {total}", True, (240, 240, 240))
        surface.blit(ptxt, (rect.right - ptxt.get_width() - 12, rect.y + 8))
    pygame.draw.rect(surface, (150, 40, 40), sv_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, sv_r, width=4, border_radius=14)
    sv_txt = FONT_MED.render(t("survival"), True, (255, 255, 255))
    surface.blit(sv_txt, (sv_r.centerx - sv_txt.get_width() // 2, sv_r.y + 12))
    rec_txt_str = t("survival_rec").format(s=survival_best_score)
    rec_txt = FONT_XS.render(rec_txt_str, True, (255, 220, 220))
    surface.blit(rec_txt, (sv_r.centerx - rec_txt.get_width() // 2, sv_r.bottom - rec_txt.get_height() - 10))
    pygame.draw.rect(surface, (150, 150, 150), back_r, border_radius=12)
    pygame.draw.rect(surface, TILE_BG, back_r, width=4, border_radius=12)
    bt = FONT_MED.render(t("back"), True, (255, 255, 255))
    surface.blit(bt, (back_r.centerx - bt.get_width() // 2, back_r.centery - bt.get_height() // 2))

def draw_check_mark(surface, cx, cy, size, color):
    thick = max(3, size // 8)
    pygame.draw.line(surface, color, (cx - size // 2, cy), (cx - size // 8, cy + size // 3), thick)
    pygame.draw.line(surface, color, (cx - size // 8, cy + size // 3), (cx + size // 2, cy - size // 3), thick)

def draw_lock_icon_level(surface, cx, cy, size, color):
    body_r = pygame.Rect(cx - size // 2, cy - int(size*0.75) // 4, size, int(size*0.75))
    pygame.draw.rect(surface, color, body_r, border_radius=4)
    arc_r = int(size * 0.35)
    arc_rect = pygame.Rect(cx - arc_r, cy - int(size*0.75) // 4 - arc_r, arc_r * 2, arc_r * 2)
    pygame.draw.arc(surface, color, arc_rect, math.pi * 0.05, math.pi * 0.95, max(3, size // 7))

def draw_levels_screen(surface, sw, sh):
    draw_bg(surface, "bg_menu", sw, sh)
    lvls = LEVEL_SETS[current_pack]
    title = FONT_BIG.render(f"{t('levels')} — {pack_name(current_pack)}", True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 260))
    rects, back_r = level_button_rects(sw, sh)
    mu = max_unlocked[current_pack]
    for i, rect in enumerate(rects):
        lvl = lvls[i]
        is_boss = lvl.get("boss", False)
        locked = (i > mu); passed = (i < mu); is_cur = (i == current_level) and not locked
        if locked:   color = (110, 110, 120)
        elif is_boss: color = (140, 60, 90)
        elif passed: color = (60, 180, 90)
        elif is_cur: color = (80, 180, 220)
        else:        color = (60, 130, 180)
        pygame.draw.rect(surface, color, rect, border_radius=14)
        pygame.draw.rect(surface, TILE_BG, rect, width=4, border_radius=14)
        if is_boss:
            num_txt = FONT_MED.render(t("boss"), True, (255, 255, 255))
            surface.blit(num_txt, (rect.centerx - num_txt.get_width() // 2, rect.y + 12))
        else:
            num_txt = FONT_BIG.render(str(i + 1), True, (255, 255, 255))
            surface.blit(num_txt, (rect.centerx - num_txt.get_width() // 2, rect.y + 6))
        if locked:
            lock_size = rect.width // 5
            draw_lock_icon_level(surface, rect.centerx, rect.y + 115, lock_size, (230, 230, 230))
        else:
            size_txt = FONT_SM.render(f"{lvl['cols']}x{lvl['rows']}", True, (255, 255, 255))
            surface.blit(size_txt, (rect.centerx - size_txt.get_width() // 2, rect.y + 76))
            time_txt = FONT_SM.render(f"{lvl['time']}s", True, (255, 230, 120))
            surface.blit(time_txt, (rect.centerx - time_txt.get_width() // 2, rect.y + 104))
            if is_boss:
                hp_txt = FONT_XS.render(f"HP: {lvl.get('hp', 0)}", True, (255, 200, 200))
                surface.blit(hp_txt, (rect.centerx - hp_txt.get_width() // 2, rect.y + 134))
            else:
                rk = lvl.get("rocks", 0)
                if rk > 0:
                    rock_txt = FONT_XS.render(f"{t('rocks_lbl')}: {rk}", True, (220, 220, 220))
                    surface.blit(rock_txt, (rect.centerx - rock_txt.get_width() // 2, rect.y + 134))
            if passed:
                draw_check_mark(surface, rect.right - 22, rect.y + 22, 20, (255, 255, 255))
    pygame.draw.rect(surface, (150, 150, 150), back_r, border_radius=12)
    pygame.draw.rect(surface, TILE_BG, back_r, width=4, border_radius=12)
    bt = FONT_MED.render(t("back"), True, (255, 255, 255))
    surface.blit(bt, (back_r.centerx - bt.get_width() // 2, back_r.centery - bt.get_height() // 2))

def draw_prelevel_screen(surface, sw, sh, idx):
    draw_bg(surface, "bg_menu", sw, sh)
    lvls = LEVEL_SETS[current_pack]
    idx = max(0, min(idx, len(lvls) - 1)); lvl = lvls[idx]
    is_boss = lvl.get("boss", False)
    if is_boss:
        title = FONT_BIG.render(f"{t('boss')} — {pack_name(current_pack)}", True, (255, 180, 180))
    else:
        title = FONT_BIG.render(f"{t('level')} {idx + 1}", True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 280))
    info_w, info_h = 460, 170
    info_rect = pygame.Rect(sw // 2 - info_w // 2, sh // 2 - 180, info_w, info_h)
    pygame.draw.rect(surface, (50, 90, 130), info_rect, border_radius=16)
    pygame.draw.rect(surface, TILE_BG, info_rect, width=4, border_radius=16)
    if is_boss:
        lines = [
            (f"{t('size')}: {lvl['cols']}×{lvl['rows']}", (255, 255, 255), FONT_MED),
            (f"{t('lvl_time')}: {lvl['time']}s", (255, 230, 120), FONT_MED),
            (f"{t('boss_hp')}: {lvl.get('hp', 0)}", (255, 180, 180), FONT_SM),
            (f"{t('difficulty')}: {t('diff_hard')}", (220, 220, 220), FONT_SM),
        ]
    else:
        lines = [
            (f"{t('size')}: {lvl['cols']}×{lvl['rows']}", (255, 255, 255), FONT_MED),
            (f"{t('lvl_time')}: {lvl['time']}s", (255, 230, 120), FONT_MED),
            (f"{t('rocks_lbl')}: {lvl.get('rocks', 0)}", (220, 220, 220), FONT_SM),
            (f"{t('difficulty')}: {difficulty_of(idx)}", (220, 220, 220), FONT_SM),
        ]
    for i, (txt, col, font) in enumerate(lines):
        tt = font.render(txt, True, col)
        surface.blit(tt, (info_rect.centerx - tt.get_width() // 2, info_rect.y + 14 + i * 34))
    play_r, back_r = prelevel_button_rects(sw, sh)
    pygame.draw.rect(surface, (80, 200, 100), play_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, play_r, width=4, border_radius=14)
    pt = FONT_MED.render(t("play"), True, (255, 255, 255))
    surface.blit(pt, (play_r.centerx - pt.get_width() // 2, play_r.centery - pt.get_height() // 2))
    pygame.draw.rect(surface, (150, 150, 150), back_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, back_r, width=4, border_radius=14)
    bt = FONT_MED.render(t("back"), True, (255, 255, 255))
    surface.blit(bt, (back_r.centerx - bt.get_width() // 2, back_r.centery - bt.get_height() // 2))

def draw_pause_overlay(surface, sw, sh, net_mode_on=False):
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180)); surface.blit(overlay, (0, 0))
    title = FONT_BIG.render(t("paused"), True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 200))
    if net_mode_on:
        cont_r, menu_r = pause_button_rects_net(sw, sh)
        buttons = [(cont_r, t("continue"), (80, 200, 100)), (menu_r, t("to_menu"), (200, 80, 80))]
    else:
        cont_r, rest_r, menu_r = pause_button_rects(sw, sh)
        buttons = [(cont_r, t("continue"), (80, 200, 100)),
                   (rest_r, t("restart"),  (230, 160, 60)),
                   (menu_r, t("to_menu"),  (200, 80, 80))]
    for rect, label, color in buttons:
        pygame.draw.rect(surface, color, rect, border_radius=12)
        pygame.draw.rect(surface, TILE_BG, rect, width=4, border_radius=12)
        txt = FONT_MED.render(label, True, (255, 255, 255))
        surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

def draw_remote_paused_overlay(surface, sw, sh):
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180)); surface.blit(overlay, (0, 0))
    title = FONT_BIG.render(t("paused"), True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 120))
    sub = FONT_MED.render(t("mp_peer_paused"), True, (255, 220, 120))
    surface.blit(sub, (sw // 2 - sub.get_width() // 2, sh // 2 + 10))

def draw_mp_menu(surface, sw, sh):
    draw_bg(surface, "bg_menu", sw, sh)
    title = FONT_BIG.render(t("mp_title"), True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 240))
    host_r, join_r, back_r = mp_menu_button_rects(sw, sh)
    for rect, label, color in [(host_r, t("mp_host"), (80, 200, 100)),
                                (join_r, t("mp_join"), (60, 140, 220)),
                                (back_r, t("back"),    (150, 150, 150))]:
        pygame.draw.rect(surface, color, rect, border_radius=14)
        pygame.draw.rect(surface, TILE_BG, rect, width=4, border_radius=14)
        txt = FONT_MED.render(label, True, (255, 255, 255))
        surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

def draw_mp_host(surface, sw, sh):
    draw_bg(surface, "bg_menu", sw, sh)
    title = FONT_BIG.render(t("mp_host"), True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, sh // 2 - 260))
    ip_lbl = FONT_MED.render(t("mp_your_ip"), True, (255, 220, 120))
    surface.blit(ip_lbl, (sw // 2 - ip_lbl.get_width() // 2, sh // 2 - 150))
    ip_txt = FONT_BIG.render(my_ip if my_ip else "—", True, (255, 255, 255))
    surface.blit(ip_txt, (sw // 2 - ip_txt.get_width() // 2, sh // 2 - 100))
    if net_state == "connected":
        st = FONT_MED.render(t("mp_connected"), True, (180, 255, 180))
        surface.blit(st, (sw // 2 - st.get_width() // 2, sh // 2 - 20))
        mode_lbl = FONT_SM.render(t("mp_mode_title"), True, (255, 220, 120))
        surface.blit(mode_lbl, (sw // 2 - mode_lbl.get_width() // 2, sh // 2 + 30))
        coop_r, vs_r = mp_host_mode_rects(sw, sh)
        for r, sel, label in [(coop_r, net_mode == "coop", t("mp_mode_coop")),
                              (vs_r, net_mode == "versus", t("mp_mode_vs"))]:
            bg = ((80, 200, 100) if sel and r is coop_r else
                  (200, 100, 130) if sel else (60, 130, 180))
            pygame.draw.rect(surface, bg, r, border_radius=12)
            pygame.draw.rect(surface, TILE_BG, r, width=4, border_radius=12)
            lt = FONT_SM.render(label, True, (255, 255, 255))
            surface.blit(lt, (r.centerx - lt.get_width() // 2, r.centery - lt.get_height() // 2))
        start_r = mp_host_start_button_rect(sw, sh)
        pygame.draw.rect(surface, (80, 200, 100), start_r, border_radius=14)
        pygame.draw.rect(surface, TILE_BG, start_r, width=4, border_radius=14)
        st_txt = FONT_MED.render(t("mp_start"), True, (255, 255, 255))
        surface.blit(st_txt, (start_r.centerx - st_txt.get_width() // 2, start_r.centery - st_txt.get_height() // 2))
    else:
        status_color = (255, 230, 120); status = net_status_msg if net_status_msg else t("mp_wait")
        if net_state == "error" and net_error:
            status = net_error; status_color = (255, 150, 150)
        st = FONT_MED.render(status, True, status_color)
        surface.blit(st, (sw // 2 - st.get_width() // 2, sh // 2 + 30))
    cancel_r = mp_cancel_button_rect(sw, sh)
    pygame.draw.rect(surface, (200, 80, 80), cancel_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, cancel_r, width=4, border_radius=14)
    bt = FONT_MED.render(t("mp_cancel"), True, (255, 255, 255))
    surface.blit(bt, (cancel_r.centerx - bt.get_width() // 2, cancel_r.centery - bt.get_height() // 2))

def draw_mp_connect(surface, sw, sh):
    draw_bg(surface, "bg_menu", sw, sh)
    title = FONT_BIG.render(t("mp_join"), True, (255, 255, 255))
    surface.blit(title, (sw // 2 - title.get_width() // 2, 20))
    if scan_state == "scanning":
        status_txt = t("mp_scanning"); status_color = (255, 230, 120)
    elif scan_state == "done":
        with scan_lock: n = len(scan_results)
        if n > 0: status_txt = t("mp_found").format(n=n); status_color = (180, 255, 180)
        else: status_txt = t("mp_none"); status_color = (200, 200, 200)
    else:
        status_txt = t("mp_scan_hint"); status_color = (200, 200, 200)
    st = FONT_SM.render(status_txt, True, status_color)
    surface.blit(st, (sw // 2 - st.get_width() // 2, 110))
    list_rects = mp_scan_list_rects(sw, sh)
    with scan_lock: results = scan_results[:]
    for i, rect in enumerate(list_rects):
        if i >= len(results): break
        ip, name = results[i]
        pygame.draw.rect(surface, (60, 130, 200), rect, border_radius=10)
        pygame.draw.rect(surface, TILE_BG, rect, width=3, border_radius=10)
        lt = FONT_SM.render(f"{ip}  —  {name}", True, (255, 255, 255))
        surface.blit(lt, (rect.x + 16, rect.centery - lt.get_height() // 2))
    lbl = FONT_SM.render(t("mp_enter_ip"), True, (255, 220, 120))
    surface.blit(lbl, (sw // 2 - lbl.get_width() // 2, sh - 215))
    field = mp_ip_field_rect(sw, sh)
    pygame.draw.rect(surface, TILE_BG, field, border_radius=10)
    pygame.draw.rect(surface, (30, 60, 90), field, width=4, border_radius=10)
    caret = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
    txt = FONT_MED.render(ip_input + caret, True, (30, 60, 90))
    surface.blit(txt, (field.x + 16, field.centery - txt.get_height() // 2))
    hint = FONT_XS.render(t("mp_hint_keys"), True, (200, 200, 200))
    surface.blit(hint, (sw // 2 - hint.get_width() // 2, field.bottom + 6))
    status = ""; color = (200, 200, 200)
    if net_state == "connecting": status = t("mp_connecting"); color = (255, 230, 120)
    elif net_state == "connected": status = t("mp_wait_host"); color = (180, 255, 180)
    elif net_state == "error": status = net_error if net_error else "Error"; color = (255, 150, 150)
    if status:
        stt = FONT_SM.render(status, True, color)
        surface.blit(stt, (sw // 2 - stt.get_width() // 2, sh - 100))
    conn_r, scan_r, back_r = mp_connect_buttons(sw, sh)
    pygame.draw.rect(surface, (80, 200, 100), conn_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, conn_r, width=4, border_radius=14)
    ct = FONT_MED.render(t("mp_connect"), True, (255, 255, 255))
    surface.blit(ct, (conn_r.centerx - ct.get_width() // 2, conn_r.centery - ct.get_height() // 2))
    pygame.draw.rect(surface, (120, 100, 220), scan_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, scan_r, width=4, border_radius=14)
    stt2 = FONT_MED.render(t("mp_scan"), True, (255, 255, 255))
    surface.blit(stt2, (scan_r.centerx - stt2.get_width() // 2, scan_r.centery - stt2.get_height() // 2))
    pygame.draw.rect(surface, (150, 150, 150), back_r, border_radius=14)
    pygame.draw.rect(surface, TILE_BG, back_r, width=4, border_radius=14)
    bt = FONT_MED.render(t("back"), True, (255, 255, 255))
    surface.blit(bt, (back_r.centerx - bt.get_width() // 2, back_r.centery - bt.get_height() // 2))

def handle_click(mx, my, tile_size, offset_x, offset_y):
    global selected, hint_pair, hint_timer, total_score, mp_my_score, survival_score
    global boss_hp, app_state, time_left, freeze_t, freeze_msg_t
    if vs_shake_t > 0:
        mx += random.randint(-60, 60); my += random.randint(-60, 60)
    if vs_lock_t > 0: return
    col = (mx - offset_x) // tile_size
    row = (my - offset_y) // tile_size
    if not (0 <= row < ROWS and 0 <= col < COLS): return
    if board[row][col] <= 0: return
    if selected is None:
        selected = (row, col); play("click"); return
    if selected == (row, col):
        selected = None; return
    sr, sc = selected
    if board[row][col] == board[sr][sc]:
        path = find_path((sr, sc), (row, col))
        if path:
            tile_id = board[row][col]
            was_gold = is_golden(sr, sc) or is_golden(row, col)
            golden_cells.discard((sr, sc))
            golden_cells.discard((row, col))
            board[row][col] = 0; board[sr][sc] = 0
            start_animation((sr, sc), (row, col), path, tile_id)
            if was_gold:
                freeze_t = GOLD_FREEZE_TIME
                freeze_msg_t = 2.5
                play("freeze")
            if not net_play:
                if survival_mode:
                    survival_score += 1
                    time_left += SURVIVAL_PAIR_TIME
                else:
                    total_score += 1; save_game()
                if is_boss_level():
                    boss_hp = max(0, boss_hp - BOSS_HP_PER_PAIR)
                    if boss_hp <= 0:
                        selected = None; hint_pair = None; hint_timer = 0.0
                        app_state = "win"; unlock_next_if_needed(); play("win")
                        return
                selected = None; hint_pair = None; hint_timer = 0.0
                play("match")
                try_auto_shuffle_if_stuck()
                return
            else:
                mp_my_score += 1
                net_send(f"MATCH {sr} {sc} {row} {col}")
                if net_mode == "coop": check_and_handle_stuck()
            selected = None; hint_pair = None; hint_timer = 0.0
            play("match")
            return
    selected = (row, col); play("click")

def toggle_fullscreen():
    global screen, fullscreen
    fullscreen = not fullscreen
    if fullscreen: screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:          screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    icon_cache.clear(); system_cache.clear(); _bg_cache.clear()

def mp_start_game():
    global mp_level_index, vs_my_rounds, vs_peer_rounds
    global COLS, ROWS, GAME_TIME, current_pack
    mp_level_index = 0; vs_my_rounds = 0; vs_peer_rounds = 0
    if net_mode == "versus":
        lvl = VS_LEVELS[0]; current_pack = lvl.get("pack", "kids")
    else:
        current_pack = "mid"; lvl = LEVELS[0]
    COLS = lvl["cols"]; ROWS = lvl["rows"]; GAME_TIME = lvl["time"]
    b = _make_board_for(COLS, ROWS, lvl.get("rocks", 0))
    csv = board_to_csv(b, COLS, ROWS)
    prefix = "START_COOP" if net_mode == "coop" else "START_VS"
    net_send(f"{prefix} {mp_level_index} {COLS} {ROWS} {GAME_TIME} {csv}")
    _start_mp_level(mp_level_index, COLS, ROWS, GAME_TIME, csv)

def mp_next_level():
    global mp_level_index, COLS, ROWS, GAME_TIME, current_pack
    mp_level_index += 1
    if net_mode == "versus":
        if mp_level_index >= len(VS_LEVELS): return
        lvl = VS_LEVELS[mp_level_index]; current_pack = lvl.get("pack", "kids")
    else:
        if mp_level_index >= len(LEVELS): return
        lvl = LEVELS[mp_level_index]
    COLS = lvl["cols"]; ROWS = lvl["rows"]; GAME_TIME = lvl["time"]
    b = _make_board_for(COLS, ROWS, lvl.get("rocks", 0))
    csv = board_to_csv(b, COLS, ROWS)
    prefix = "START_COOP" if net_mode == "coop" else "START_VS"
    net_send(f"{prefix} {mp_level_index} {COLS} {ROWS} {GAME_TIME} {csv}")
    _start_mp_level(mp_level_index, COLS, ROWS, GAME_TIME, csv)

def net_pause_local():
    global app_state
    if net_play: net_send("PAUSE")
    app_state = "paused"

def net_resume_local():
    global app_state
    if net_play: net_send("RESUME")
    app_state = "playing"

def net_quit_to_menu():
    if net_play: net_send("QUIT")
    net_close(); go_to_menu()

running = True
while running:
    dt = clock.tick(60) / 1000.0
    for k in vs_my_cd:
        if vs_my_cd[k] > 0: vs_my_cd[k] = max(0.0, vs_my_cd[k] - dt)
    if vs_fog_t > 0: vs_fog_t = max(0.0, vs_fog_t - dt)
    if vs_shake_t > 0: vs_shake_t = max(0.0, vs_shake_t - dt)
    if vs_lock_t > 0: vs_lock_t = max(0.0, vs_lock_t - dt)
    if vs_attack_timer > 0: vs_attack_timer = max(0.0, vs_attack_timer - dt)
    if vs_my_attack_timer > 0: vs_my_attack_timer = max(0.0, vs_my_attack_timer - dt)
    if freeze_msg_t > 0: freeze_msg_t = max(0.0, freeze_msg_t - dt)

    music_should_play = (app_state != "playing")
    ensure_menu_music(music_should_play)

    with net_rx_lock:
        msgs = net_rx_queue[:]; net_rx_queue.clear()
    for m in msgs: handle_net_msg(m)

    if net_play and net_state == "error":
        net_close(); go_to_menu()

    is_vs = (app_state in ("playing", "vs_result", "mp_result", "paused", "remote_paused")) \
            and net_play and net_mode == "versus"

    if is_vs:
        sw, sh, hud_h, skill_h, tile_size, my_ox, my_oy, peer_ox, peer_oy, half_w = compute_vs_layout()
        offset_x, offset_y = my_ox, my_oy
    else:
        sw, sh, hud_h, skill_h, tile_size, offset_x, offset_y = compute_layout()

    if app_state == "menu":
        play_r, mp_r, lang_r, exit_r = menu_button_rects(sw, sh)
        snd_r = menu_sound_button_rect(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_l: toggle_lang()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if play_r.collidepoint(mx, my): go_to_pack_select()
                elif mp_r.collidepoint(mx, my) and not IS_ANDROID: net_close(); app_state = "mp_menu"
                elif lang_r.collidepoint(mx, my): toggle_lang()
                elif exit_r.collidepoint(mx, my): running = False
                elif snd_r.collidepoint(mx, my): toggle_sound()
        draw_menu(screen, sw, sh); pygame.display.flip(); continue

    if app_state == "pack_select":
        kids_r, mid_r, ad_r, sv_r, back_r = pack_button_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_l: toggle_lang()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: go_to_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if kids_r.collidepoint(mx, my): current_pack = "kids"; go_to_levels()
                elif mid_r.collidepoint(mx, my): current_pack = "mid"; go_to_levels()
                elif ad_r.collidepoint(mx, my): current_pack = "adult"; go_to_levels()
                elif sv_r.collidepoint(mx, my): start_survival(); continue
                elif back_r.collidepoint(mx, my): go_to_menu()
        draw_pack_select(screen, sw, sh); pygame.display.flip(); continue

    if app_state == "levels":
        rects, back_r = level_button_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_l: toggle_lang()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: go_to_pack_select()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                clicked = False
                for i, r in enumerate(rects):
                    if r.collidepoint(mx, my):
                        clicked = True
                        if i <= max_unlocked[current_pack]: go_to_prelevel(i)
                        break
                if not clicked and back_r.collidepoint(mx, my): go_to_pack_select()
        draw_levels_screen(screen, sw, sh); pygame.display.flip(); continue

    if app_state == "prelevel":
        play_r, back_r = prelevel_button_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_l: toggle_lang()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: go_to_levels()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): start_level(preview_level)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if play_r.collidepoint(mx, my): start_level(preview_level)
                elif back_r.collidepoint(mx, my): go_to_levels()
        draw_prelevel_screen(screen, sw, sh, preview_level); pygame.display.flip(); continue

    if app_state == "mp_menu":
        host_r, join_r, back_r = mp_menu_button_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: net_close(); running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_l: toggle_lang()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: net_close(); go_to_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if host_r.collidepoint(mx, my): net_host_start(); app_state = "mp_host"
                elif join_r.collidepoint(mx, my):
                    ip_input = ""; net_close(); net_scan_start(); app_state = "mp_connect"
                elif back_r.collidepoint(mx, my): net_close(); go_to_menu()
        draw_mp_menu(screen, sw, sh); pygame.display.flip(); continue

    if app_state == "mp_host":
        cancel_r = mp_cancel_button_rect(sw, sh)
        start_r = mp_host_start_button_rect(sw, sh)
        coop_r, vs_r = mp_host_mode_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: net_close(); running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: net_close(); app_state = "mp_menu"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and net_state == "connected":
                    mp_start_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if net_state == "connected":
                    if coop_r.collidepoint(mx, my): net_mode = "coop"
                    elif vs_r.collidepoint(mx, my): net_mode = "versus"
                    elif start_r.collidepoint(mx, my): mp_start_game(); continue
                if cancel_r.collidepoint(mx, my): net_close(); app_state = "mp_menu"
        draw_mp_host(screen, sw, sh); pygame.display.flip(); continue

    if app_state == "mp_connect":
        conn_r, scan_r, back_r = mp_connect_buttons(sw, sh)
        list_rects = mp_scan_list_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: net_close(); running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: net_close(); app_state = "mp_menu"
                elif event.key == pygame.K_BACKSPACE: ip_input = ip_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if ip_input.strip() and net_state != "connected":
                        net_client_start(ip_input.strip())
                elif event.unicode and len(ip_input) < 15:
                    if event.unicode in "0123456789.": ip_input += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                clicked_list = False
                with scan_lock: results_snapshot = scan_results[:]
                for i, r in enumerate(list_rects):
                    if i >= len(results_snapshot): break
                    if r.collidepoint(mx, my):
                        ip, _name = results_snapshot[i]
                        ip_input = ip; net_client_start(ip); clicked_list = True; break
                if clicked_list: continue
                if conn_r.collidepoint(mx, my):
                    if ip_input.strip() and net_state != "connected":
                        net_client_start(ip_input.strip())
                elif scan_r.collidepoint(mx, my):
                    if scan_state != "scanning": net_scan_start()
                elif back_r.collidepoint(mx, my): net_close(); app_state = "mp_menu"
        draw_mp_connect(screen, sw, sh); pygame.display.flip(); continue

    if app_state == "paused":
        if net_play:
            cont_r, menu_r = pause_button_rects_net(sw, sh); rest_r = None
        else:
            cont_r, rest_r, menu_r = pause_button_rects(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE:
                    if net_play: net_resume_local()
                    else: app_state = "playing"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if cont_r.collidepoint(mx, my):
                    if net_play: net_resume_local()
                    else: app_state = "playing"
                elif (not net_play) and rest_r is not None and rest_r.collidepoint(mx, my):
                    restart_level()
                elif menu_r.collidepoint(mx, my):
                    if net_play: net_quit_to_menu()
                    else: go_to_menu()
        if is_vs:
            draw_game_bg(screen, sw, sh)
            draw_board_ref(screen, board, tile_size, my_ox, my_oy, dim=(vs_fog_t > 0))
            if vs_peer_board is not None:
                draw_board_ref(screen, vs_peer_board, tile_size, peer_ox, peer_oy)
            pygame.draw.line(screen, (100, 120, 160), (half_w, hud_h), (half_w, sh - skill_h), 3)
        else:
            draw_game_bg(screen, sw, sh)
            draw_board(screen, tile_size, offset_x, offset_y)
        draw_particles(screen)
        draw_hud(screen, sw, hud_h, time_left)
        if not net_play and not survival_mode: draw_skill_panel(screen, sw, sh, skill_h)
        elif net_mode == "versus": draw_vs_skill_panel(screen, sw, sh, skill_h)
        draw_pause_overlay(screen, sw, sh, net_mode_on=net_play)
        pygame.display.flip(); continue

    if app_state == "remote_paused":
        for event in pygame.event.get():
            if event.type == pygame.QUIT: net_close(); running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: net_quit_to_menu()
        if is_vs:
            draw_game_bg(screen, sw, sh)
            draw_board_ref(screen, board, tile_size, my_ox, my_oy, dim=(vs_fog_t > 0))
            if vs_peer_board is not None:
                draw_board_ref(screen, vs_peer_board, tile_size, peer_ox, peer_oy)
            pygame.draw.line(screen, (100, 120, 160), (half_w, hud_h), (half_w, sh - skill_h), 3)
        else:
            draw_game_bg(screen, sw, sh)
            draw_board(screen, tile_size, offset_x, offset_y)
        draw_particles(screen)
        draw_hud(screen, sw, hud_h, time_left)
        if not net_play and not survival_mode: draw_skill_panel(screen, sw, sh, skill_h)
        elif net_mode == "versus": draw_vs_skill_panel(screen, sw, sh, skill_h)
        draw_remote_paused_overlay(screen, sw, sh)
        pygame.display.flip(); continue

    if app_state in ("mp_result", "vs_result"):
        is_last = (mp_level_index >= (len(VS_LEVELS) if net_mode == "versus" else len(LEVELS)) - 1)
        btn = overlay_button_rect(sw, sh)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: net_close(); running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: toggle_fullscreen()
                elif event.key == pygame.K_m: toggle_sound()
                elif event.key == pygame.K_ESCAPE: net_quit_to_menu()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if net_is_host:
                        if is_last: net_quit_to_menu()
                        else: mp_next_level()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if net_is_host and btn.collidepoint(mx, my):
                    if is_last: net_quit_to_menu()
                    else: mp_next_level()
        if net_mode == "versus":
            draw_game_bg(screen, sw, sh)
            draw_board_ref(screen, board, tile_size, my_ox, my_oy)
            if vs_peer_board is not None:
                draw_board_ref(screen, vs_peer_board, tile_size, peer_ox, peer_oy)
            pygame.draw.line(screen, (100, 120, 160), (half_w, hud_h), (half_w, sh - skill_h), 3)
        else:
            draw_game_bg(screen, sw, sh)
            draw_board(screen, tile_size, offset_x, offset_y)
        draw_particles(screen)
        draw_hud(screen, sw, hud_h, time_left)
        if net_mode == "versus": draw_vs_result_overlay(screen, sw, sh, is_last)
        else:                    draw_mp_result_overlay(screen, sw, sh, is_last)
        pygame.display.flip(); continue

    overlay_rect = overlay_button_rect(sw, sh) if (app_state in ("win", "lose") and not net_play) else None
    hint_r, shuffle_r, bomb_r = skill_button_rects(sw, sh, skill_h)
    menu_r = hud_menu_button_rect(sw, hud_h)

    if app_state == "playing":
        if freeze_t > 0:
            freeze_t = max(0.0, freeze_t - dt)
        else:
            time_left -= dt

        if not net_play:
            golden_timer -= dt
            if golden_timer <= 0:
                golden_timer = GOLD_INTERVAL
                spawn_golden_tile()

        if survival_mode:
            survival_elapsed += dt
            minutes = int(survival_elapsed // 60.0)
            survival_spawn_interval = max(SURVIVAL_SPAWN_MIN, SURVIVAL_SPAWN_START - 4.0 * minutes)
            survival_spawn_t -= dt
            if survival_spawn_t <= 0:
                survival_spawn_t = survival_spawn_interval
                survival_spawn_tiles()
            survival_stone_t -= dt
            if survival_stone_t <= 0:
                survival_stone_t = SURVIVAL_STONE_EVERY
                survival_spawn_stone()

        if is_boss_level() and boss_hp > 0 and time_left > 0:
            boss_attack_timer -= dt
            if boss_attack_timer <= 0:
                boss_do_attack()

        if time_left <= 0:
            time_left = 0
            if net_play:
                if net_mode == "versus":
                    my_left = sum(1 for rr in board for v in rr if v > 0)
                    peer_left = sum(1 for rr in (vs_peer_board or board) for v in rr if v > 0)
                    if my_left < peer_left: vs_my_rounds += 1
                    elif my_left > peer_left: vs_peer_rounds += 1
                    app_state = "vs_result"
                else: app_state = "mp_result"
            elif survival_mode:
                if survival_score > survival_best_score:
                    survival_best_score = survival_score
                    save_survival_record(survival_best_score)
                app_state = "lose"; play("lose")
            else:
                app_state = "lose"; play("lose")
        elif not net_play and is_boss_level() and boss_hp <= 0:
            app_state = "win"; unlock_next_if_needed(); play("win")
        elif board_empty() and not animations and not survival_mode:
            if net_play:
                if net_mode == "versus": vs_my_rounds += 1; app_state = "vs_result"
                else: app_state = "mp_result"
            else:
                app_state = "win"; unlock_next_if_needed(); play("win")
        if net_play and net_mode == "versus" and app_state == "playing" and vs_peer_board is not None:
            if board_empty_ref(vs_peer_board):
                vs_peer_rounds += 1; app_state = "vs_result"
    if hint_timer > 0:
        hint_timer -= dt
        if hint_timer <= 0: hint_pair = None
    update_animations(dt, tile_size, my_ox if is_vs else offset_x,
                      my_oy if is_vs else offset_y)
    update_particles(dt)

    vs_skill_rects = vs_skill_button_rects(sw, sh, skill_h) if is_vs else []

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11: toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE:
                if app_state == "playing":
                    if net_play: net_pause_local()
                    else: app_state = "paused"
                else:
                    if net_play: net_quit_to_menu()
                    else: go_to_levels()
            elif event.key == pygame.K_r and app_state == "playing": try_use_shuffle()
            elif event.key == pygame.K_h and app_state == "playing": try_use_hint()
            elif event.key == pygame.K_b and app_state == "playing": try_use_bomb()
            elif event.key == pygame.K_m: toggle_sound()
            elif event.key == pygame.K_l: toggle_lang()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if overlay_rect is not None:
                if overlay_rect.collidepoint(mx, my):
                    if app_state == "win":
                        if net_play: net_quit_to_menu()
                        else: go_to_levels()
                    else:
                        if net_play: net_quit_to_menu()
                        else: restart_level()
                continue
            if app_state == "playing":
                if is_vs:
                    clicked_skill = False
                    for kind, r in vs_skill_rects:
                        if r.collidepoint(mx, my):
                            if vs_my_cd.get(kind, 0.0) <= 0.0:
                                vs_my_cd[kind] = VS_SKILLS[kind]["cd"]
                                if kind == "fog": net_send("VS_FOG"); vs_my_attack_msg = t("vs_you_fog")
                                elif kind == "shake": net_send("VS_SHAKE"); vs_my_attack_msg = t("vs_you_shake")
                                elif kind == "lock": net_send("VS_LOCK"); vs_my_attack_msg = t("vs_you_lock")
                                vs_my_attack_timer = 2.0; play("vs_hit")
                            clicked_skill = True; break
                    if clicked_skill: continue
                else:
                    if (not net_play) and (not survival_mode) and hint_r.collidepoint(mx, my): try_use_hint(); continue
                    if (not net_play) and (not survival_mode) and shuffle_r.collidepoint(mx, my): try_use_shuffle(); continue
                    if (not net_play) and (not survival_mode) and bomb_r.collidepoint(mx, my): try_use_bomb(); continue
                if menu_r.collidepoint(mx, my):
                    if net_play: net_pause_local()
                    else: app_state = "paused"
                    continue
                handle_click(mx, my, tile_size,
                             my_ox if is_vs else offset_x,
                             my_oy if is_vs else offset_y)

    boss_now = (not net_play) and is_boss_level()

    if is_vs:
        draw_game_bg(screen, sw, sh)
        my_board_rect = pygame.Rect(my_ox, my_oy, COLS * tile_size, ROWS * tile_size)
        draw_board_ref(screen, board, tile_size, my_ox, my_oy, shake=(vs_shake_t > 0))
        if vs_fog_t > 0:
            draw_cloud_overlay(screen, my_board_rect, vs_fog_t, VS_SKILLS["fog"]["duration"])
        if vs_peer_board is not None:
            draw_board_ref(screen, vs_peer_board, tile_size, peer_ox, peer_oy)
        lbl1 = FONT_SM.render(t("mp_you"), True, (255, 255, 255)); screen.blit(lbl1, (my_ox, my_oy - 30))
        lbl2 = FONT_SM.render(t("mp_peer"), True, (200, 200, 200)); screen.blit(lbl2, (peer_ox, peer_oy - 30))
        pygame.draw.line(screen, (100, 120, 160), (half_w, hud_h), (half_w, sh - skill_h), 3)
        draw_animations(screen, tile_size, my_ox, my_oy)
        draw_particles(screen)
    else:
        draw_game_bg(screen, sw, sh)
        draw_board(screen, tile_size, offset_x, offset_y, shake=(vs_shake_t > 0))
        if boss_now and vs_fog_t > 0:
            board_rect = pygame.Rect(offset_x, offset_y, COLS * tile_size, ROWS * tile_size)
            draw_cloud_overlay(screen, board_rect, vs_fog_t, VS_SKILLS["fog"]["duration"])
        draw_animations(screen, tile_size, offset_x, offset_y)
        draw_particles(screen)

    if (is_vs or boss_now) and vs_lock_t > 0:
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA); ov.fill((180, 20, 20, 60)); screen.blit(ov, (0, 0))
        if boss_now and not is_vs:
            lock_txt = FONT_BIG.render(t("boss_msg_lock"), True, (255, 255, 255))
        else:
            lock_txt = FONT_BIG.render(t("vs_peer_lock"), True, (255, 255, 255))
        screen.blit(lock_txt, (sw // 2 - lock_txt.get_width() // 2, sh // 2 - lock_txt.get_height() // 2))

    draw_hud(screen, sw, hud_h, time_left)
    if not net_play:
        if not survival_mode:
            draw_skill_panel(screen, sw, sh, skill_h)
        if boss_now:
            draw_attack_banner(screen, sw, hud_h)
        if freeze_msg_t > 0:
            draw_freeze_banner(screen, sw, hud_h)
    elif net_mode == "versus":
        draw_vs_skill_panel(screen, sw, sh, skill_h)
        draw_attack_banner(screen, sw, hud_h)
        draw_my_attack_banner(screen, sw, hud_h)

    if app_state == "win":
        draw_overlay(screen, sw, sh, t("you_win"), f"{t('score')}: {total_score}", t("next"))
    elif app_state == "lose":
        if survival_mode:
            draw_overlay(screen, sw, sh, t("you_lose"), f"{t('score')}: {survival_score}", t("try_again"))
        else:
            draw_overlay(screen, sw, sh, t("you_lose"), f"{t('score')}: {total_score}", t("try_again"))

    pygame.display.flip()

net_close()
pygame.quit()
sys.exit()