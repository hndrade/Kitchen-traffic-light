"""Registers/unregisters the app to launch automatically with Windows."""
import sys
import os

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "KitchenTrafficLight"


def _run_command():
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return f'"{pythonw}" "{main_script}"'


def set_start_with_windows(enabled):
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _run_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
