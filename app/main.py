from psycopg2 import pool
from database import *
from datetime import date, datetime, timedelta
from r2 import imageExists
import os

def clearConsole():
    os.system('cls')

def showClients():
    conn = connectToDB()
    with conn.cursor() as curs:
        try:
            curs.execute(f"SELECT * FROM client")
            rows = curs.fetchall()
        except Exception as e:
            print(f"SQL ERROR: {e}")
            conn.rollback()

    releaseConn(conn)
    
    return rows

def getNameFromId(idClient):
    conn = connectToDB()
    with conn.cursor() as curs:
        try:
            curs.execute("SELECT \"firstName\", \"lastName\" FROM client WHERE \"idClient\" = %s", (idClient,))
            row = curs.fetchone()
            name = f"{row[0]} {row[1]}"
            releaseConn(conn)
            return name
        except Exception as e:
            print(f"SQL ERROR: {e}")
            conn.rollback()
    releaseConn(conn)
    

def getUserRecipes(idClient: int):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM recette WHERE \"idClient\" = %s ORDER BY \"idRecette\"", (idClient,))
        rows = curs.fetchall()
        releaseConn(conn)
        return rows

def addRecipe(idClient, desc):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM recette WHERE \"idClient\" = %s ORDER BY \"idRecette\" DESC", (idClient,))
        newRecipeId = curs.fetchone()[1]
        newRecipeId += 1

        try:
            curs.execute("INSERT INTO recette VALUES(%s, %s, %s)", (idClient, newRecipeId, desc))
            print(f"New recipe ({newRecipeId}) added to UserID: {idClient}")
            conn.commit()
        except Exception as e:
            print(f"SQL ERROR: {e}")
            conn.rollback()
    releaseConn(conn)


def delRecipe(idClient, idRecette):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT \"idRecette\" FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
        RecipeId = curs.fetchone()[0]

        try:
            curs.execute("DELETE FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
            print(f"New recipe ({RecipeId}) added to UserID: {idClient}")
            conn.commit()
        except Exception as e:
            print(f"SQL ERROR: {e}")
            conn.rollback()
    releaseConn(conn)

def modifyRecipe(idClient, idRecette, newDesc):
    conn = connectToDB()
    print(f"Modifying recipe {idRecette} from User {idClient}... to: {newDesc}")
    with conn.cursor() as curs:
        curs.execute("SELECT description FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
        row = curs.fetchone()
        curs.execute("UPDATE recette SET description = %s WHERE \"idClient\" = %s AND \"idRecette\" = %s", (newDesc, idClient, idRecette))
    conn.commit()
    releaseConn(conn)
    print(f"Recipe {idRecette} from User {idClient} has been modified")

def getRecipe(idClient, idRecette):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
        row = curs.fetchall()
    releaseConn(conn)
    return row

def getAllEpiceries():
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT nom FROM epicerie ORDER BY \"idEpicerie\"")
        rows = curs.fetchall()
    releaseConn(conn)
    return [row[0].lower() for row in rows]

def getUserInfo(idClient):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT *, EXTRACT(YEAR FROM AGE(\"birthDate\")) AS age FROM client WHERE \"idClient\" = %s", (idClient,))
        row = curs.fetchone()
    conn.commit()
    releaseConn(conn)
    return row

def setUserInfo(idClient, Courriel, Prénom, Nom, Birthday):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("UPDATE client SET \"email\" = %s, \"firstName\" = %s, \"lastName\" = %s, \"birthDate\" = %s WHERE \"idClient\" = %s",
                      (Courriel, Prénom, Nom, Birthday, idClient))
    conn.commit()
    releaseConn(conn)

def getFlyerWeek():
    current_date = datetime.now().weekday()
    last_thursday = datetime.now() - timedelta(days=(current_date - 3) % 7)
    next_wednesday = last_thursday + timedelta(days=6)
    return last_thursday, next_wednesday

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

def getLeaderboard(page=1, limit=20):
    conn = connectToDB()
    offset = (page - 1) * limit
    with conn.cursor() as curs:
        curs.execute("""
            SELECT ROW_NUMBER() OVER (ORDER by COUNT(*) DESC) AS "classement",
	 		c."firstName"|| ' ' || c."lastName" AS Name,
			COUNT(*) AS "nbRecettes"
            FROM recette AS r
			LEFT JOIN client AS c ON c."idClient" = r."idClient"
            GROUP BY r."idClient", c."firstName", c."lastName"
            ORDER BY "nbRecettes" DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = curs.fetchall()
    releaseConn(conn)
    return rows
