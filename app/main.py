from database import *
from datetime import date, datetime, timedelta
from r2 import imageExists
import os

def clearConsole():
    os.system('cls')

def getFlyerWeek():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_day = today.weekday()
    last_thursday = today - timedelta(days=(current_day - 3) % 7)
    next_wednesday = last_thursday + timedelta(days=6)
    return last_thursday, next_wednesday

def getPrevWeekStart(current: str) -> str:
    d = date.fromisoformat(current)
    return (d - timedelta(weeks=1)).isoformat()

def getFlyerStartWeekStr():
    week = getFlyerWeek()
    return str(week[0].date())

def checkIfFlyersAlreadyDownloaded():
    epiceries = getAllEpiceries()
    weekStr = getFlyerStartWeekStr()

    for epicerie in epiceries:
        r2Path = f"circulaires/{epicerie}_{weekStr}/{epicerie}0.png"
        if not imageExists(r2Path):
            return False
    return True

def calculate_age(born):
    today = date.today()
    # The comparison returns True (1) if today is before the birthday, else False (0)
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))  




print("main.py done.")
