"""Configuration window for the weekly kitchen schedule."""
import re
import tkinter as tk
from tkinter import messagebox, ttk

from app.config import DAYS, DEFAULT_BLOCKS, load_config, save_config
from app.scheduler import Scheduler
from app.startup import set_start_with_windows

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
NUM_BLOCKS = len(DEFAULT_BLOCKS)


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
        col = 2
        for b in range(NUM_BLOCKS):
            ttk.Label(frame, text=f"Bloqueio {b + 1} início", font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col, padx=4, pady=4
            )
            ttk.Label(frame, text=f"Bloqueio {b + 1} fim", font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col + 1, padx=4, pady=4
            )
            col += 2
        num_columns = col

        for i, day in enumerate(DAYS, start=1):
            ttk.Label(frame, text=day).grid(row=i, column=0, sticky="w", padx=4, pady=2)

            enabled_var = tk.BooleanVar()
            ttk.Checkbutton(frame, variable=enabled_var).grid(row=i, column=1, pady=2)

            block_vars = []
            col = 2
            for _ in range(NUM_BLOCKS):
                start_var = tk.StringVar()
                ttk.Entry(frame, textvariable=start_var, width=6, justify="center").grid(
                    row=i, column=col, padx=4, pady=2
                )
                end_var = tk.StringVar()
                ttk.Entry(frame, textvariable=end_var, width=6, justify="center").grid(
                    row=i, column=col + 1, padx=4, pady=2
                )
                block_vars.append({"start": start_var, "end": end_var})
                col += 2

            self.day_widgets[day] = {"enabled": enabled_var, "blocks": block_vars}

        self.start_with_windows_var = tk.BooleanVar()
        ttk.Checkbutton(
            frame, text="Iniciar com o Windows", variable=self.start_with_windows_var
        ).grid(row=len(DAYS) + 1, column=0, columnspan=num_columns, sticky="w", pady=(10, 4))

        ttk.Button(frame, text="Salvar", command=self._on_save).grid(
            row=len(DAYS) + 2, column=0, columnspan=num_columns, pady=(6, 0), sticky="ew"
        )

        self.status_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.status_var, foreground="green").grid(
            row=len(DAYS) + 3, column=0, columnspan=num_columns, pady=(6, 0)
        )

    def _load_into_ui(self):
        for day, widgets in self.day_widgets.items():
            entry = self.config["schedule"][day]
            widgets["enabled"].set(entry["enabled"])
            for block_var, block in zip(widgets["blocks"], entry["blocks"]):
                block_var["start"].set(block["start"])
                block_var["end"].set(block["end"])
        self.start_with_windows_var.set(self.config.get("start_with_windows", False))

    def _on_save(self):
        new_schedule = {}
        for day, widgets in self.day_widgets.items():
            blocks = []
            for b, block_var in enumerate(widgets["blocks"], start=1):
                start_value = block_var["start"].get().strip()
                end_value = block_var["end"].get().strip()
                for label, value in (("início", start_value), ("fim", end_value)):
                    if not TIME_RE.match(value):
                        messagebox.showerror(
                            "Horário inválido",
                            f"O horário de {label} do bloqueio {b} de {day} deve estar no formato HH:MM.",
                        )
                        return
                blocks.append({"start": start_value, "end": end_value})
            new_schedule[day] = {
                "enabled": widgets["enabled"].get(),
                "blocks": blocks,
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
