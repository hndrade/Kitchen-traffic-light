#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semáforo da Cozinha — widget de área de trabalho (Windows).

Uma janela pequena, sempre no topo, mostrando um semáforo realista:
  - VERDE:    cozinha aberta (estado padrão)
  - AMARELO:  faltam 5 minutos para um período de fechamento
  - VERMELHO: cozinha fechada (limpeza em andamento)

Os horários de fechamento e os dias da semana são configuráveis pelo
ícone de engrenagem (⚙) e persistidos em settings.json ao lado do script.

Somente biblioteca padrão (Tkinter). Execute com:  pythonw semaforo.py
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuração / persistência
# ---------------------------------------------------------------------------

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

# Semana em ordem brasileira: Seg Ter Qua Qui Sex Sáb Dom
DAY_LETTERS = ["S", "T", "Q", "Q", "S", "S", "D"]   # índice 0 = segunda ... 6 = domingo
DAY_NAMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

DEFAULT_SETTINGS = {
    "days": ["S", "T", "Q", "Q", "S"],              # letras posicionais (compatibilidade)
    "day_indices": [0, 1, 2, 3, 4],                  # forma não ambígua: 0=Seg ... 6=Dom
    "schedules": [
        {"start": "09:30", "end": "10:30"},
        {"start": "14:00", "end": "15:30"},
    ],
}

YELLOW_WARNING_MINUTES = 5


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
                start = parse_hhmm(item["start"])
                end = parse_hhmm(item["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if start is not None and end is not None:
                schedules.append({"start": item["start"], "end": item["end"]})
        settings["schedules"] = schedules
    if isinstance(data.get("day_indices"), list):
        settings["day_indices"] = sorted({i for i in data["day_indices"] if isinstance(i, int) and 0 <= i <= 6})
    elif isinstance(data.get("days"), list):
        settings["day_indices"] = letters_to_indices(data["days"])
    settings["days"] = [DAY_LETTERS[i] for i in settings["day_indices"]]
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


# ---------------------------------------------------------------------------
# Janela principal — o semáforo
# ---------------------------------------------------------------------------

TRANSPARENT_KEY = "#ff00fe"  # cor-chave para transparência no Windows

# (cor apagada, cor acesa, cor do centro aceso, cor do halo)
BULB_COLORS = {
    RED:    ("#3a0d0d", "#e01818", "#ff7a5c", "#c03020"),
    YELLOW: ("#3d330c", "#f2b60d", "#ffe98a", "#c79a1e"),
    GREEN:  ("#0c2e14", "#17c93a", "#8affa8", "#1e9e3e"),
}


class TrafficLightWidget:
    WIDTH, HEIGHT = 150, 330

    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.state = None
        self.settings_window = None
        self._drag_offset = None

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

        self._draw_static()
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
        cx = self.WIDTH // 2

        # --- poste (estilo de rua) ---
        pole_w = 18
        c.create_rectangle(cx - pole_w // 2, 270, cx + pole_w // 2, self.HEIGHT,
                           fill="#3c3f42", outline="#26282a")
        c.create_rectangle(cx - pole_w // 2 + 3, 270, cx - pole_w // 2 + 6, self.HEIGHT,
                           fill="#55595d", outline="")  # brilho lateral do poste
        # braçadeiras do poste
        for y in (280, 305):
            c.create_rectangle(cx - pole_w // 2 - 3, y, cx + pole_w // 2 + 3, y + 6,
                               fill="#2a2c2e", outline="#1a1b1c")

        # --- corpo do semáforo ---
        bx1, by1, bx2, by2 = 30, 8, self.WIDTH - 30, 276
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
        state = compute_state(datetime.now(), self.settings)
        if state != self.state:
            self.state = state
            self._apply_state(state)
        self.root.after(1000, self._tick)

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
        self.settings = settings
        self.state = None  # força reavaliação/redesenho no próximo tick


# ---------------------------------------------------------------------------
# Janela de configurações
# ---------------------------------------------------------------------------

BG, FG, ACCENT = "#1d1f21", "#d7dade", "#17c93a"
BTN_BG, BTN_ON = "#2c2f32", "#17632a"


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.schedules = [dict(s) for s in app.settings["schedules"]]

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

    def _save(self):
        settings = {
            "day_indices": [i for i, var in enumerate(self.day_vars) if var.get()],
            "schedules": self.schedules,
        }
        try:
            save_settings(settings)
        except OSError as exc:
            self.error_label.configure(text="Erro ao salvar: %s" % exc)
            return
        self.app.reload_settings(load_settings())
        self._close()

    def _close(self):
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
    TrafficLightWidget(root)
    root.mainloop()


if __name__ == "__main__":
    main()
