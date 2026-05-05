# Librairie pour intéragir avec notre database
from psycopg2 import pool
import os
import platform
from dotenv import load_dotenv

load_dotenv()

connection_pool = pool.SimpleConnectionPool(
    1,  # min connections
    10, # max connections
    host=     os.environ.get("DB_HOST"),
    port=     os.environ.get("DB_PORT"),
    dbname=   os.environ.get("DB_NAME"),
    user=     os.environ.get("DB_USER"),
    password= os.environ.get("DB_PASSWORD")
)

# --- Gestion des slashs en fonction de l'OS
PLATFORM = platform.system()
SLASHS = "\\"

if PLATFORM == "Linux":
    SLASHS = "/"

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
configFile = DIR_PATH + SLASHS + "dbinfo.json"

# FONCTIONS ------------------------------------------------------------------------------------------
def connectToDB():
    return connection_pool.getconn()

def releaseConn(conn):
    connection_pool.putconn(conn)

def getURI():
    user =     os.environ.get("DB_USER")
    pwd =      os.environ.get("DB_PASSWORD")
    host =     os.environ.get("DB_HOST")
    port =     os.environ.get("DB_PORT")
    dbName =   os.environ.get("DB_NAME")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{dbName}"

def createUser(firstName, lastName, email, password_hash, birthday=None):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(   """
                            INSERT INTO client ("firstName", "lastName", "birthDate", "email", "password_hash")
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING "idClient"
                        """, (firstName, lastName, birthday, email, password_hash))
        
        userID = curs.fetchone()[0]
        conn.commit()
    releaseConn(conn)

    return userID

def createNotification(idClient, title, message):
    conn = connectToDB()
    with conn.cursor() as curs:
        try:
            curs.execute(
                'INSERT INTO notification ("idClient", title, message) VALUES (%s, %s, %s)',
                (idClient, title, message)
            )
            conn.commit()
        except Exception as e:
            print(f"SQL ERROR (createNotification): {e}")
            conn.rollback()
    releaseConn(conn)

def getNotifications(idClient):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'SELECT id, title, message, "isRead", "creationDate" AT TIME ZONE \'America/Montreal\' FROM notification '
            'WHERE "idClient" = %s ORDER BY "creationDate" DESC LIMIT 20',
            (idClient,)
        )
        rows = curs.fetchall()
    releaseConn(conn)
    return rows

def readNotification(idClient, idNotif):
    conn = connectToDB()

    with conn.cursor() as curs:
        curs.execute("UPDATE notification SET \"isRead\" = TRUE WHERE \"idClient\" = %s AND id = %s;", (idClient, idNotif))
        conn.commit()

    releaseConn(conn)

def getLeaderboard(page=1, limit=50):
    conn = connectToDB()
    offset = (page - 1) * limit
    with conn.cursor() as curs:
        curs.execute("""
            SELECT * FROM classement
                LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = curs.fetchall()
    releaseConn(conn)
    return rows

def getUserInfo(idClient):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT *, EXTRACT(YEAR FROM AGE(\"birthDate\")) AS age FROM client WHERE \"idClient\" = %s", (idClient,))
        row = curs.fetchone()
    conn.commit()
    releaseConn(conn)
    return row

def setUserInfo(idClient, Courriel, Prénom, Nom, Birthday, participe):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("UPDATE client SET \"email\" = %s, \"firstName\" = %s, \"lastName\" = %s, \"birthDate\" = %s, \"ranked\" = %s WHERE \"idClient\" = %s",
                      (Courriel, Prénom, Nom, Birthday, participe, idClient))
    conn.commit()
    releaseConn(conn)

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

def getUserByEmail(Email):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM client WHERE \"email\" = %s", (Email,))
        row = curs.fetchone()

    releaseConn(conn)
    return row
    

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


print("database.py done.")