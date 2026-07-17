"""Wrapper around Windows toast notifications."""
from winotify import Notification


APP_ID = "Cozinha - Horários"


def notify(title, message):
    toast = Notification(app_id=APP_ID, title=title, msg=message, duration="short")
    toast.show()


def notify_kitchen_open():
    notify("Cozinha liberada!", "A cozinha está aberta agora.")


def notify_opens_soon():
    notify("Cozinha", "A cozinha abre em 5 minutos.")


def notify_closes_soon():
    notify("Cozinha", "A cozinha fecha em 5 minutos.")
