#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semáforo da Cozinha — widget de área de trabalho (Windows).

Uma janela pequena, sempre no topo, mostrando um semáforo realista:
  - VERDE:    cozinha aberta (estado padrão)
  - AMARELO:  faltam 5 minutos para um período de fechamento
  - VERMELHO: cozinha fechada (limpeza em andamento)

Os horários de fechamento e os dias da semana são configuráveis pelo
ícone de engrenagem (⚙) e persistidos em settings.json ao lado do script
(ou do .exe, quando compilado).

Nos dias sem agendamento o widget inicia minimizado na bandeja do sistema
(ao lado do relógio); clique no ícone da bandeja para mostrar/ocultar.
Clique com o botão direito no semáforo para o menu (minimizar/config/sair).

Somente biblioteca padrão (Tkinter + ctypes/winreg). Execute com:
    pythonw semaforo.py
"""

import json
import os
import sys
import tkinter as tk
from datetime import datetime

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------------------
# Configuração / persistência
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):          # rodando como .exe (PyInstaller)
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# Semana em ordem brasileira: Seg Ter Qua Qui Sex Sáb Dom
DAY_LETTERS = ["S", "T", "Q", "Q", "S", "S", "D"]   # índice 0 = segunda ... 6 = domingo
DAY_NAMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

DEFAULT_SETTINGS = {
    "days": ["S", "T"],                              # letras posicionais (compatibilidade)
    "day_indices": [0, 1],                           # forma não ambígua: 0=Seg ... 6=Dom
    "schedules": [
        {"start": "09:30", "end": "10:30"},
        {"start": "14:00", "end": "15:00"},
    ],
    "scale": 1.0,                                    # tamanho do widget (0.6 a 2.0)
}

YELLOW_WARNING_MINUTES = 5
MIN_SCALE, MAX_SCALE = 0.6, 2.0


def clamp_scale(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0
    return max(MIN_SCALE, min(MAX_SCALE, value))


def letters_to_indices(letters):
    """Resolve a lista posicional de letras (ambígua: S/Q repetem) contra a
    sequência da semana, casando de forma gulosa em ordem."""
    indices = []
    pos = 0
    for letter in letters:
        while pos < 7 and DAY_LETTERS[pos] != letter:
            pos += 1
        if pos >= 7:
            break
        indices.append(pos)
        pos += 1
    return indices


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return json.loads(json.dumps(DEFAULT_SETTINGS))

    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    if isinstance(data.get("schedules"), list):
        schedules = []
        for item in data["schedules"]:
            try:
                parse_hhmm(item["start"])
                parse_hhmm(item["end"])
            except (KeyError, TypeError, ValueError):
                continue
            schedules.append({"start": item["start"], "end": item["end"]})
        settings["schedules"] = schedules
    if isinstance(data.get("day_indices"), list):
        settings["day_indices"] = sorted({i for i in data["day_indices"] if isinstance(i, int) and 0 <= i <= 6})
    elif isinstance(data.get("days"), list):
        settings["day_indices"] = letters_to_indices(data["days"])
    settings["days"] = [DAY_LETTERS[i] for i in settings["day_indices"]]
    settings["scale"] = clamp_scale(data.get("scale", DEFAULT_SETTINGS["scale"]))
    return settings


def save_settings(settings):
    settings = dict(settings)
    settings["days"] = [DAY_LETTERS[i] for i in settings["day_indices"]]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, ensure_ascii=False, indent=2)


def parse_hhmm(text):
    """'09:30' -> 570 (minutos desde meia-noite). Levanta ValueError se inválido."""
    parts = str(text).strip().split(":")
    if len(parts) != 2:
        raise ValueError(text)
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(text)
    return hours * 60 + minutes


# ---------------------------------------------------------------------------
# Lógica do semáforo
# ---------------------------------------------------------------------------

GREEN, YELLOW, RED = "green", "yellow", "red"

STATE_LABELS = {
    GREEN: "Verde — cozinha aberta",
    YELLOW: "Amarelo — fecha em instantes",
    RED: "Vermelho — cozinha fechada",
}


def compute_state(now, settings):
    """Retorna GREEN, YELLOW ou RED para o instante `now`."""
    if now.weekday() not in settings["day_indices"]:
        return GREEN
    minute_of_day = now.hour * 60 + now.minute
    for sched in settings["schedules"]:
        try:
            start = parse_hhmm(sched["start"])
            end = parse_hhmm(sched["end"])
        except (KeyError, ValueError):
            continue
        if end <= start:
            end += 24 * 60  # janela cruzando a meia-noite
        for candidate in (minute_of_day, minute_of_day + 24 * 60):
            if start <= candidate < end:
                return RED
        warn_start = start - YELLOW_WARNING_MINUTES
        for candidate in (minute_of_day, minute_of_day + 24 * 60):
            if warn_start <= candidate < start:
                return YELLOW
    return GREEN


def is_scheduled_day(now, settings):
    """True se hoje é um dia com períodos de fechamento configurados."""
    return bool(settings["schedules"]) and now.weekday() in settings["day_indices"]


# ---------------------------------------------------------------------------
# Inicialização automática com o Windows (chave Run do registro)
# ---------------------------------------------------------------------------

AUTOSTART_APP_NAME = "SemaforoCozinha"
AUTOSTART_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

if IS_WINDOWS:
    import winreg

    def autostart_command():
        if getattr(sys, "frozen", False):
            return '"%s"' % sys.executable
        pythonw = os.path.join(sys.exec_prefix, "pythonw.exe")
        interpreter = pythonw if os.path.exists(pythonw) else sys.executable
        return '"%s" "%s"' % (interpreter, os.path.abspath(__file__))

    def get_autostart():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY) as key:
                winreg.QueryValueEx(key, AUTOSTART_APP_NAME)
            return True
        except OSError:
            return False

    def set_autostart(enabled):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_APP_NAME, 0, winreg.REG_SZ,
                                  autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_APP_NAME)
                except FileNotFoundError:
                    pass
else:
    def get_autostart():
        return False

    def set_autostart(enabled):
        pass


# ---------------------------------------------------------------------------
# Ícone na bandeja do sistema (Shell_NotifyIcon via ctypes — só Windows)
# ---------------------------------------------------------------------------

def hex_to_rgb(color):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


# (cor apagada, cor acesa, cor do centro aceso, cor do halo)
BULB_COLORS = {
    RED:    ("#3a0d0d", "#e01818", "#ff7a5c", "#c03020"),
    YELLOW: ("#3d330c", "#f2b60d", "#ffe98a", "#c79a1e"),
    GREEN:  ("#0c2e14", "#17c93a", "#8affa8", "#1e9e3e"),
}

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _gdi32 = ctypes.windll.gdi32
    _shell32 = ctypes.windll.shell32
    _kernel32 = ctypes.windll.kernel32

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p,
                                 ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)

    _user32.DefWindowProcW.restype = ctypes.c_ssize_t
    _user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                       ctypes.c_size_t, ctypes.c_ssize_t]
    _user32.CreateWindowExW.restype = ctypes.c_void_p
    _user32.CreateWindowExW.argtypes = [wintypes.DWORD, ctypes.c_wchar_p,
                                        ctypes.c_wchar_p, wintypes.DWORD,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.c_void_p]
    _user32.CreateIconIndirect.restype = ctypes.c_void_p
    _user32.DestroyIcon.argtypes = [ctypes.c_void_p]
    _user32.DestroyWindow.argtypes = [ctypes.c_void_p]
    _kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    _gdi32.CreateBitmap.restype = ctypes.c_void_p
    _gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                                    ctypes.c_uint, ctypes.c_char_p]
    _gdi32.DeleteObject.argtypes = [ctypes.c_void_p]

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", ctypes.c_uint),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", ctypes.c_void_p),
            ("hIcon", ctypes.c_void_p),
            ("hCursor", ctypes.c_void_p),
            ("hbrBackground", ctypes.c_void_p),
            ("lpszMenuName", ctypes.c_wchar_p),
            ("lpszClassName", ctypes.c_wchar_p),
        ]

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", ctypes.c_void_p),
            ("hbmColor", ctypes.c_void_p),
        ]

    class NOTIFYICONDATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", ctypes.c_void_p),
            ("uID", ctypes.c_uint),
            ("uFlags", ctypes.c_uint),
            ("uCallbackMessage", ctypes.c_uint),
            ("hIcon", ctypes.c_void_p),
            ("szTip", ctypes.c_wchar * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", ctypes.c_wchar * 256),
            ("uVersion", ctypes.c_uint),
            ("szInfoTitle", ctypes.c_wchar * 64),
            ("dwInfoFlags", wintypes.DWORD),
        ]

    NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
    NIM_ADD, NIM_MODIFY, NIM_DELETE = 0x0, 0x1, 0x2
    WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x0202, 0x0203
    HWND_MESSAGE = ctypes.c_void_p(-3 & (2 ** (8 * ctypes.sizeof(ctypes.c_void_p)) - 1))

    class WinTray:
        """Ícone na área de notificação (perto do relógio) desenhado como um
        mini-semáforo com a luz do estado atual acesa."""

        WM_TRAY = 0x8000 + 20  # WM_APP + 20
        ICON_SIZE = 32

        def __init__(self, on_click):
            self.on_click = on_click
            self.hicon = None
            self._added = False
            self._tip = "Semáforo da Cozinha"

            hinstance = _kernel32.GetModuleHandleW(None)
            self._wndproc = WNDPROC(self._wnd_proc)  # manter referência viva
            wc = WNDCLASSW()
            wc.lpfnWndProc = self._wndproc
            wc.hInstance = hinstance
            wc.lpszClassName = "SemaforoCozinhaTray"
            if not _user32.RegisterClassW(ctypes.byref(wc)):
                raise ctypes.WinError()
            self.hwnd = _user32.CreateWindowExW(
                0, wc.lpszClassName, None, 0, 0, 0, 0, 0,
                HWND_MESSAGE, None, hinstance, None)
            if not self.hwnd:
                raise ctypes.WinError()
            # se o Explorer reiniciar, a bandeja é recriada — readicionar o ícone
            self._taskbar_created = _user32.RegisterWindowMessageW("TaskbarCreated")

        def _wnd_proc(self, hwnd, msg, wparam, lparam):
            if msg == self.WM_TRAY:
                if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    try:
                        self.on_click()
                    except Exception:
                        pass
                return 0
            if msg == self._taskbar_created and self.hicon:
                self._added = False
                self._notify(NIM_ADD)
                return 0
            return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        def _icon_pixels(self, state):
            """Bitmap BGRA 32x32 de um mini-semáforo com `state` aceso."""
            size = self.ICON_SIZE
            buf = bytearray(size * size * 4)

            def put(x, y, rgb, alpha=255):
                if 0 <= x < size and 0 <= y < size:
                    i = (y * size + x) * 4
                    buf[i], buf[i + 1], buf[i + 2], buf[i + 3] = rgb[2], rgb[1], rgb[0], alpha

            body, rim = (24, 26, 28), (70, 74, 78)
            for y in range(0, size):
                for x in range(10, 22):
                    edge = y in (0, size - 1) or x in (10, 21)
                    put(x, y, rim if edge else body)
            centers = ((RED, 6), (YELLOW, 16), (GREEN, 26))
            for name, cy in centers:
                off_hex, lit_hex = BULB_COLORS[name][0], BULB_COLORS[name][1]
                rgb = hex_to_rgb(lit_hex if name == state else off_hex)
                for dy in range(-4, 5):
                    for dx in range(-4, 5):
                        if dx * dx + dy * dy <= 18:
                            put(16 + dx, cy + dy, rgb)
            return bytes(buf)

        def _make_hicon(self, state):
            size = self.ICON_SIZE
            hbm_color = _gdi32.CreateBitmap(size, size, 1, 32, self._icon_pixels(state))
            hbm_mask = _gdi32.CreateBitmap(size, size, 1, 1, bytes(size * ((size + 15) // 16) * 2))
            info = ICONINFO(True, 0, 0, hbm_mask, hbm_color)
            hicon = _user32.CreateIconIndirect(ctypes.byref(info))
            _gdi32.DeleteObject(hbm_color)
            _gdi32.DeleteObject(hbm_mask)
            return hicon

        def _notify(self, action):
            data = NOTIFYICONDATA()
            data.cbSize = ctypes.sizeof(NOTIFYICONDATA)
            data.hWnd = self.hwnd
            data.uID = 1
            data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            data.uCallbackMessage = self.WM_TRAY
            data.hIcon = self.hicon
            data.szTip = self._tip[:127]
            if _shell32.Shell_NotifyIconW(action, ctypes.byref(data)):
                if action == NIM_ADD:
                    self._added = True

        def set_state(self, state):
            old = self.hicon
            self.hicon = self._make_hicon(state)
            self._tip = "Semáforo da Cozinha\n%s" % STATE_LABELS[state]
            self._notify(NIM_MODIFY if self._added else NIM_ADD)
            if old:
                _user32.DestroyIcon(old)

        def destroy(self):
            if self._added:
                data = NOTIFYICONDATA()
                data.cbSize = ctypes.sizeof(NOTIFYICONDATA)
                data.hWnd = self.hwnd
                data.uID = 1
                _shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
                self._added = False
            if self.hicon:
                _user32.DestroyIcon(self.hicon)
                self.hicon = None
            _user32.DestroyWindow(self.hwnd)


# ---------------------------------------------------------------------------
# Janela principal — o semáforo
# ---------------------------------------------------------------------------

TRANSPARENT_KEY = "#ff00fe"  # cor-chave para transparência no Windows


class TrafficLightWidget:
    BASE_WIDTH, BASE_HEIGHT = 150, 330

    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.state = None
        self.settings_window = None
        self._drag_offset = None

        self.scale = clamp_scale(self.settings.get("scale", 1.0))
        self.WIDTH = round(self.BASE_WIDTH * self.scale)
        self.HEIGHT = round(self.BASE_HEIGHT * self.scale)

        root.title("Semáforo da Cozinha")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.geometry("%dx%d+80+80" % (self.WIDTH, self.HEIGHT))

        self.canvas = tk.Canvas(
            root, width=self.WIDTH, height=self.HEIGHT,
            highlightthickness=0, bd=0, bg=TRANSPARENT_KEY,
        )
        self.canvas.pack(fill="both", expand=True)

        # Fundo transparente (recurso do Windows); em outros SOs fica escuro.
        try:
            root.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            self.canvas.configure(bg="#101010")

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonPress-3>", self._show_menu)

        self._draw_static()

        # --- bandeja do sistema + visibilidade inicial ---
        self.tray = None
        if IS_WINDOWS:
            try:
                self.tray = WinTray(self._on_tray_click)
            except Exception:
                self.tray = None

        now = datetime.now()
        self._user_override = None          # True/False = escolha manual do dia
        self._override_date = now.date()
        self._visible = True
        if self.tray and not is_scheduled_day(now, self.settings):
            self._visible = False
            root.withdraw()                 # dia sem agendamento: só a bandeja

        # --- menu de contexto (botão direito) ---
        self.menu = tk.Menu(root, tearoff=0)
        if self.tray:
            self.menu.add_command(label="Minimizar para a bandeja",
                                  command=self._minimize_to_tray)
        self.menu.add_command(label="Configurações…", command=self._open_settings)
        self.menu.add_separator()
        self.menu.add_command(label="Sair", command=self.quit)

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._tick()

    # -- desenho ------------------------------------------------------------

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kw):
        r = radius
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kw)

    def _draw_static(self):
        c = self.canvas
        W, H = self.BASE_WIDTH, self.BASE_HEIGHT
        cx = W // 2

        # --- poste (estilo de rua) ---
        pole_w = 18
        c.create_rectangle(cx - pole_w // 2, 270, cx + pole_w // 2, H,
                           fill="#3c3f42", outline="#26282a")
        c.create_rectangle(cx - pole_w // 2 + 3, 270, cx - pole_w // 2 + 6, H,
                           fill="#55595d", outline="")  # brilho lateral do poste
        # braçadeiras do poste
        for y in (280, 305):
            c.create_rectangle(cx - pole_w // 2 - 3, y, cx + pole_w // 2 + 3, y + 6,
                               fill="#2a2c2e", outline="#1a1b1c")

        # --- corpo do semáforo ---
        bx1, by1, bx2, by2 = 30, 8, W - 30, 276
        self._rounded_rect(bx1 - 3, by1 - 3, bx2 + 3, by2 + 3, 22,
                           fill="#0c0c0d", outline="")            # sombra/borda externa
        self._rounded_rect(bx1, by1, bx2, by2, 20,
                           fill="#1d1f21", outline="#3a3d40")     # caixa
        self._rounded_rect(bx1 + 4, by1 + 4, bx1 + 12, by2 - 4, 8,
                           fill="#2c2f32", outline="")            # realce lateral (falso degradê)
        # parafusos
        for bxx in (bx1 + 10, bx2 - 10):
            for byy in (by1 + 10, by2 - 10):
                c.create_oval(bxx - 3, byy - 3, bxx + 3, byy + 3,
                              fill="#4a4d50", outline="#141516")

        # --- lâmpadas (com viseiras) ---
        self.bulbs = {}
        bulb_r = 30
        for i, name in enumerate((RED, YELLOW, GREEN)):
            bcy = 52 + i * 88
            # viseira (aba) acima da lâmpada
            c.create_arc(cx - bulb_r - 8, bcy - bulb_r - 12,
                         cx + bulb_r + 8, bcy + bulb_r,
                         start=15, extent=150, style="chord",
                         fill="#141516", outline="#333639")
            c.create_arc(cx - bulb_r - 6, bcy - bulb_r - 8,
                         cx + bulb_r + 6, bcy + bulb_r - 4,
                         start=25, extent=130, style="arc",
                         outline="#3f4245", width=2)
            # aro da lâmpada
            c.create_oval(cx - bulb_r - 3, bcy - bulb_r - 3,
                          cx + bulb_r + 3, bcy + bulb_r + 3,
                          fill="#0e0f10", outline="#37393c")
            # halo (só aparece quando acesa) — atrás preenchido depois
            halo = c.create_oval(cx - bulb_r - 9, bcy - bulb_r - 9,
                                 cx + bulb_r + 9, bcy + bulb_r + 9,
                                 fill="", outline="", stipple="gray25")
            c.tag_lower(halo)
            body = c.create_oval(cx - bulb_r, bcy - bulb_r,
                                 cx + bulb_r, bcy + bulb_r,
                                 fill=BULB_COLORS[name][0], outline="#050505", width=2)
            inner = c.create_oval(cx - bulb_r + 9, bcy - bulb_r + 9,
                                  cx + bulb_r - 9, bcy + bulb_r - 9,
                                  fill="", outline="")
            gloss = c.create_oval(cx - bulb_r + 8, bcy - bulb_r + 6,
                                  cx - 2, bcy - 8,
                                  fill="#ffffff", outline="", stipple="gray25")
            self.bulbs[name] = {"halo": halo, "body": body, "inner": inner, "gloss": gloss}

        # --- engrenagem (discreta, canto inferior direito da caixa) ---
        self.gear = c.create_text(bx2 - 12, by2 - 14, text="⚙",
                                  font=("Segoe UI Symbol", 11), fill="#5a5e62",
                                  tags=("gear",))
        c.tag_bind("gear", "<ButtonPress-1>", self._open_settings)
        c.tag_bind("gear", "<Enter>",
                   lambda e: (c.itemconfigure(self.gear, fill="#c8ccd0"),
                              c.configure(cursor="hand2")))
        c.tag_bind("gear", "<Leave>",
                   lambda e: (c.itemconfigure(self.gear, fill="#5a5e62"),
                              c.configure(cursor="")))

        # aplica o tamanho escolhido: escala todas as coordenadas de uma vez
        if abs(self.scale - 1.0) > 1e-6:
            c.scale("all", 0, 0, self.scale, self.scale)
            c.itemconfigure(self.gear,
                            font=("Segoe UI Symbol", max(7, round(11 * self.scale))))

    def _apply_state(self, state):
        c = self.canvas
        for name, items in self.bulbs.items():
            off, lit, core, halo = BULB_COLORS[name]
            if name == state:
                c.itemconfigure(items["halo"], fill=halo)
                c.itemconfigure(items["body"], fill=lit)
                c.itemconfigure(items["inner"], fill=core, stipple="gray50")
                c.itemconfigure(items["gloss"], stipple="gray50")
            else:
                c.itemconfigure(items["halo"], fill="")
                c.itemconfigure(items["body"], fill=off)
                c.itemconfigure(items["inner"], fill="")
                c.itemconfigure(items["gloss"], stipple="gray25")

    # -- comportamento -------------------------------------------------------

    def _tick(self):
        now = datetime.now()
        if now.date() != self._override_date:   # novo dia: volta à regra automática
            self._override_date = now.date()
            self._user_override = None

        state = compute_state(now, self.settings)
        if state != self.state:
            self.state = state
            self._apply_state(state)
            if self.tray:
                try:
                    self.tray.set_state(state)
                except Exception:
                    pass

        if self.tray:
            if self._user_override is not None:
                desired = self._user_override
            else:
                desired = is_scheduled_day(now, self.settings)
            self._set_visible(desired)

        self.root.after(1000, self._tick)

    def _set_visible(self, visible):
        if visible == self._visible:
            return
        self._visible = visible
        if visible:
            self.root.deiconify()
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.lift()
        else:
            self.root.withdraw()

    def _on_tray_click(self):
        self._user_override = not self._visible
        self._set_visible(self._user_override)

    def _minimize_to_tray(self):
        self._user_override = False
        self._set_visible(False)

    def _show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _on_press(self, event):
        if "gear" in self.canvas.gettags("current"):
            self._drag_offset = None
            return
        self._drag_offset = (event.x, event.y)

    def _on_drag(self, event):
        if self._drag_offset is None:
            return
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self.root.geometry("+%d+%d" % (x, y))

    def _open_settings(self, _event=None):
        if self.settings_window is not None and self.settings_window.alive():
            self.settings_window.focus()
            return
        self.settings_window = SettingsWindow(self)

    def reload_settings(self, settings):
        new_scale = clamp_scale(settings.get("scale", self.scale))
        self.settings = settings
        if abs(new_scale - self.scale) > 1e-6:
            self.rebuild(new_scale)
        else:
            self.state = None  # força reavaliação/redesenho no próximo tick

    def rebuild(self, new_scale):
        """Redimensiona a janela/canvas e redesenha o semáforo na nova escala."""
        self.scale = clamp_scale(new_scale)
        self.WIDTH = round(self.BASE_WIDTH * self.scale)
        self.HEIGHT = round(self.BASE_HEIGHT * self.scale)
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.canvas.config(width=self.WIDTH, height=self.HEIGHT)
        self.root.geometry("%dx%d+%d+%d" % (self.WIDTH, self.HEIGHT, x, y))
        self.canvas.delete("all")
        self._draw_static()
        state = compute_state(datetime.now(), self.settings)
        self.state = state
        self._apply_state(state)

    def quit(self):
        if self.tray:
            try:
                self.tray.destroy()
            except Exception:
                pass
        self.root.destroy()


# ---------------------------------------------------------------------------
# Janela de configurações
# ---------------------------------------------------------------------------

BG, FG, ACCENT = "#1d1f21", "#d7dade", "#17c93a"
BTN_BG, BTN_ON = "#2c2f32", "#17632a"


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.schedules = [dict(s) for s in app.settings["schedules"]]
        self._orig_scale = app.scale       # para restaurar se fechar sem salvar
        self._saved = False

        self.win = tk.Toplevel(app.root)
        self.win.title("Configurações — Semáforo da Cozinha")
        self.win.configure(bg=BG, padx=16, pady=14)
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        # --- dias da semana ---
        tk.Label(self.win, text="Dias da semana", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        days_row = tk.Frame(self.win, bg=BG)
        days_row.pack(anchor="w", pady=(4, 12))
        self.day_vars = []
        for i, letter in enumerate(DAY_LETTERS):
            var = tk.BooleanVar(value=(i in app.settings["day_indices"]))
            btn = tk.Checkbutton(
                days_row, text=letter, variable=var, indicatoron=False,
                width=3, bg=BTN_BG, fg=FG, selectcolor=BTN_ON,
                activebackground=BTN_BG, activeforeground=FG,
                relief="flat", bd=0, font=("Segoe UI", 10, "bold"),
            )
            btn.grid(row=0, column=i, padx=2)
            self._tooltip(btn, DAY_NAMES[i])
            self.day_vars.append(var)

        # --- lista de horários ---
        tk.Label(self.win, text="Períodos de fechamento", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.list_frame = tk.Frame(self.win, bg=BG)
        self.list_frame.pack(anchor="w", fill="x", pady=(4, 4))
        self._rebuild_list()

        # --- linha de adição (aparece ao clicar em +) ---
        self.add_frame = tk.Frame(self.win, bg=BG)
        self._build_add_row()

        add_btn = tk.Button(self.win, text="+", command=self._toggle_add,
                            bg=BTN_BG, fg=FG, activebackground=BTN_ON,
                            activeforeground=FG, relief="flat", width=3,
                            font=("Segoe UI", 11, "bold"), cursor="hand2")
        add_btn.pack(anchor="w", pady=(2, 10))

        # --- tamanho do widget ---
        size_head = tk.Frame(self.win, bg=BG)
        size_head.pack(anchor="w", fill="x", pady=(4, 0))
        tk.Label(size_head, text="Tamanho do widget", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.size_label = tk.Label(size_head, text="%d%%" % round(app.scale * 100),
                                   bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold"))
        self.size_label.pack(side="right")
        self.scale_var = tk.IntVar(value=round(app.scale * 100))
        tk.Scale(
            self.win, from_=int(MIN_SCALE * 100), to=int(MAX_SCALE * 100),
            orient="horizontal", variable=self.scale_var, showvalue=False,
            command=self._on_size, bg=BG, fg=FG, troughcolor=BTN_BG,
            activebackground=ACCENT, highlightthickness=0, bd=0, sliderrelief="flat",
            length=210,
        ).pack(anchor="w", pady=(0, 8))

        # --- iniciar com o Windows ---
        self.autostart_var = tk.BooleanVar(value=get_autostart())
        if IS_WINDOWS:
            tk.Checkbutton(
                self.win, text="Iniciar com o Windows", variable=self.autostart_var,
                bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                activeforeground=FG, font=("Segoe UI", 9),
            ).pack(anchor="w", pady=(0, 6))

        self.error_label = tk.Label(self.win, text="", bg=BG, fg="#e05050",
                                    font=("Segoe UI", 9))
        self.error_label.pack(anchor="w")

        tk.Button(self.win, text="Salvar", command=self._save,
                  bg=ACCENT, fg="#0c2e14", activebackground="#5fe07f",
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=18, pady=4, cursor="hand2").pack(anchor="e", pady=(6, 0))

    # -- widgets auxiliares ---------------------------------------------------

    def _tooltip(self, widget, text):
        def enter(_e):
            self._tip = tk.Toplevel(widget)
            self._tip.overrideredirect(True)
            self._tip.attributes("-topmost", True)
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            self._tip.geometry("+%d+%d" % (x, y))
            tk.Label(self._tip, text=text, bg="#333639", fg=FG,
                     font=("Segoe UI", 8), padx=6, pady=2).pack()

        def leave(_e):
            tip = getattr(self, "_tip", None)
            if tip is not None:
                tip.destroy()
                self._tip = None

        widget.bind("<Enter>", enter, add="+")
        widget.bind("<Leave>", leave, add="+")

    def _rebuild_list(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.schedules:
            tk.Label(self.list_frame, text="(nenhum período configurado)",
                     bg=BG, fg="#8a8e93", font=("Segoe UI", 9, "italic")).pack(anchor="w")
        for idx, sched in enumerate(self.schedules):
            row = tk.Frame(self.list_frame, bg=BG)
            row.pack(anchor="w", fill="x", pady=1)
            tk.Label(row, text="%s às %s" % (sched["start"], sched["end"]),
                     bg=BG, fg=FG, font=("Consolas", 11), width=16,
                     anchor="w").pack(side="left")
            tk.Button(row, text="x", command=lambda i=idx: self._remove(i),
                      bg=BG, fg="#e05050", activebackground=BG,
                      activeforeground="#ff8080", relief="flat", bd=0,
                      font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left")

    def _spin(self, parent, to, value, increment=1):
        var = tk.StringVar(value="%02d" % value)
        spin = tk.Spinbox(parent, from_=0, to=to, wrap=True, width=3,
                          textvariable=var, format="%02.0f", increment=increment,
                          bg=BTN_BG, fg=FG, buttonbackground=BTN_BG,
                          insertbackground=FG, relief="flat",
                          font=("Consolas", 11), justify="center")
        spin.pack(side="left")
        return var

    def _build_add_row(self):
        f = self.add_frame

        def label(text):
            tk.Label(f, text=text, bg=BG, fg=FG,
                     font=("Consolas", 11)).pack(side="left")

        self.start_h = self._spin(f, 23, 9)
        label(":")
        self.start_m = self._spin(f, 59, 30, increment=5)
        label("  às  ")
        self.end_h = self._spin(f, 23, 10)
        label(":")
        self.end_m = self._spin(f, 59, 30, increment=5)
        tk.Button(f, text="OK", command=self._add,
                  bg=BTN_ON, fg=FG, activebackground=ACCENT, relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=8,
                  cursor="hand2").pack(side="left", padx=(10, 0))

    # -- ações -----------------------------------------------------------------

    def _toggle_add(self):
        if self.add_frame.winfo_ismapped():
            self.add_frame.pack_forget()
        else:
            self.add_frame.pack(anchor="w", pady=(2, 4))

    def _add(self):
        try:
            start = "%02d:%02d" % (int(self.start_h.get()), int(self.start_m.get()))
            end = "%02d:%02d" % (int(self.end_h.get()), int(self.end_m.get()))
            start_min, end_min = parse_hhmm(start), parse_hhmm(end)
        except ValueError:
            self.error_label.configure(text="Horário inválido.")
            return
        if end_min <= start_min:
            self.error_label.configure(text="O fim deve ser depois do início.")
            return
        self.error_label.configure(text="")
        self.schedules.append({"start": start, "end": end})
        self.schedules.sort(key=lambda s: parse_hhmm(s["start"]))
        self.add_frame.pack_forget()
        self._rebuild_list()

    def _remove(self, index):
        del self.schedules[index]
        self._rebuild_list()

    def _on_size(self, value):
        pct = int(float(value))
        self.size_label.configure(text="%d%%" % pct)
        self.app.rebuild(pct / 100.0)   # preview ao vivo

    def _save(self):
        settings = {
            "day_indices": [i for i, var in enumerate(self.day_vars) if var.get()],
            "schedules": self.schedules,
            "scale": clamp_scale(self.scale_var.get() / 100.0),
        }
        try:
            save_settings(settings)
        except OSError as exc:
            self.error_label.configure(text="Erro ao salvar: %s" % exc)
            return
        try:
            set_autostart(self.autostart_var.get())
        except OSError as exc:
            self.error_label.configure(text="Erro no registro: %s" % exc)
            return
        self._saved = True
        self.app.reload_settings(load_settings())
        self._close()

    def _close(self):
        # se fechou sem salvar, desfaz o preview de tamanho
        if not self._saved and abs(self.app.scale - self._orig_scale) > 1e-6:
            self.app.rebuild(self._orig_scale)
        self.win.destroy()
        self.app.settings_window = None

    def alive(self):
        return self.win.winfo_exists()

    def focus(self):
        self.win.lift()
        self.win.focus_force()


# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    widget = TrafficLightWidget(root)
    try:
        root.mainloop()
    finally:
        if widget.tray:
            try:
                widget.tray.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()
