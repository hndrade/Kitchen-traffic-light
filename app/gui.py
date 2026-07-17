"""Configuration window for the weekly kitchen schedule."""
import re
import tkinter as tk
from tkinter import messagebox, ttk

from app.config import DAYS, load_config, save_config
from app.scheduler import Scheduler
from app.startup import set_start_with_windows

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Cozinha - Horários")
        self.root.resizable(False, False)

        self.config = load_config()
        self.day_widgets = {}

        self._build_ui()
        self._load_into_ui()

        self.scheduler = Scheduler(get_config=lambda: self.config)
        self.scheduler.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0)

        ttk.Label(frame, text="Dia", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=4, pady=4)
        ttk.Label(frame, text="Ativo", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(frame, text="Abre", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=4, pady=4)
        ttk.Label(frame, text="Fecha", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=4, pady=4)

        for i, day in enumerate(DAYS, start=1):
            ttk.Label(frame, text=day).grid(row=i, column=0, sticky="w", padx=4, pady=2)

            enabled_var = tk.BooleanVar()
            ttk.Checkbutton(frame, variable=enabled_var).grid(row=i, column=1, pady=2)

            open_var = tk.StringVar()
            ttk.Entry(frame, textvariable=open_var, width=6, justify="center").grid(row=i, column=2, padx=4, pady=2)

            close_var = tk.StringVar()
            ttk.Entry(frame, textvariable=close_var, width=6, justify="center").grid(row=i, column=3, padx=4, pady=2)

            self.day_widgets[day] = {"enabled": enabled_var, "open": open_var, "close": close_var}

        self.start_with_windows_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, text="Iniciar com o Windows", variable=self.start_with_windows_var
        ).grid(row=len(DAYS) + 1, column=0, columnspan=4, sticky="w", pady=(10, 4))

        ttk.Button(frame, text="Salvar", command=self._on_save).grid(
            row=len(DAYS) + 2, column=0, columnspan=4, pady=(6, 0), sticky="ew"
        )

        self.status_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.status_var, foreground="green").grid(
            row=len(DAYS) + 3, column=0, columnspan=4, pady=(6, 0)
        )

    def _load_into_ui(self):
        for day, widgets in self.day_widgets.items():
            entry = self.config["schedule"][day]
            widgets["enabled"].set(entry["enabled"])
            widgets["open"].set(entry["open"])
            widgets["close"].set(entry["close"])
        self.start_with_windows_var.set(self.config.get("start_with_windows", False))

    def _on_save(self):
        new_schedule = {}
        for day, widgets in self.day_widgets.items():
            open_value = widgets["open"].get().strip()
            close_value = widgets["close"].get().strip()
            for label, value in (("abertura", open_value), ("fechamento", close_value)):
                if not TIME_RE.match(value):
                    messagebox.showerror(
                        "Horário inválido",
                        f"O horário de {label} de {day} deve estar no formato HH:MM.",
                    )
                    return
            new_schedule[day] = {
                "enabled": widgets["enabled"].get(),
                "open": open_value,
                "close": close_value,
            }

        self.config["schedule"] = new_schedule
        self.config["start_with_windows"] = self.start_with_windows_var.get()
        save_config(self.config)

        try:
            set_start_with_windows(self.config["start_with_windows"])
        except ImportError:
            pass  # winreg only exists on Windows; ignore elsewhere.

        self.status_var.set("Configuração salva.")
        self.root.after(2500, lambda: self.status_var.set(""))

    def _on_close(self):
        self.scheduler.stop()
        self.root.destroy()


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
