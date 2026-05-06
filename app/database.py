# Librairie pour intéragir avec notre database
from psycopg2 import pool
import os
import platform
from dotenv import load_dotenv
from datetime import timezone

load_dotenv()

connection_pool = pool.SimpleConnectionPool(
    1,  # min connections
    20, # max connections
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

def updatePassword(idClient, password_hash):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE client SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL, '
                '"last_password_change" = NOW() WHERE "idClient" = %s',
                (password_hash, idClient)
            )
            conn.commit()
    finally:
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
    try:
        with conn.cursor() as curs:
            curs.execute("""
                            SELECT "idClient", email, "firstName", "lastName", "birthDate", ranked,
                                username, password_hash, "created_at", 
                                "last_login" AT TIME ZONE 'America/Montreal',
                                 role, is_verified, verification_token, reset_token, reset_token_expiry,
                                "last_password_change" AT TIME ZONE 'America/Montreal',
                                EXTRACT(YEAR FROM AGE("birthDate")) AS age
                            FROM client 
                            WHERE "idClient" = %s
                        """, (idClient,))
            row = curs.fetchone()
        conn.commit()
        return row
    finally:
        releaseConn(conn)

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
    

def getRecetteWithIngredients(idRecette, idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            # La recette
            curs.execute("""
                SELECT "idRecette", nom, portions, instructions, "createdAt"
                FROM recette
                WHERE "idRecette" = %s AND "idClient" = %s
            """, (idRecette, idClient))
            recette = curs.fetchone()

            # Les ingrédients
            curs.execute("""
                SELECT i.nom, ri.quantite, ri.unite
                FROM recette_ingredient ri
                JOIN ingredient i ON ri."idIngredient" = i."idIngredient"
                WHERE ri."idRecette" = %s
            """, (idRecette,))
            ingredients = curs.fetchall()

        return recette, ingredients
    finally:
        releaseConn(conn)

def getUserRecipes(idClient: int):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute("""SELECT \"idRecette\", nom, instructions, portions, TO_CHAR(\"createdAt\" AT TIME ZONE 'America/Montreal', 'DD/MM/YYYY HH24hMI') FROM recette
                      WHERE \"idClient\" = %s ORDER BY \"idRecette\" """, (idClient,))
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
        curs.execute("SELECT idRecette, nom, instructions, portions, createdAt AT TIME ZONE \'America/Montreal\' FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
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

def deleteUnverifiedAccounts():
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            """DELETE FROM client 
               WHERE is_verified = FALSE 
               AND "creationDate" < NOW() - INTERVAL '24 hours'"""
        )
        conn.commit()
    releaseConn(conn)

def getAllUsers(page=1, limit=20, search=''):
    offset = (page - 1) * limit
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idClient", email, "firstName", "lastName", role, is_verified, "last_password_change"
                FROM client 
                WHERE "firstName" ILIKE %s OR "lastName" ILIKE %s OR email ILIKE %s OR CAST("idClient" AS TEXT) LIKE %s
                ORDER BY "idClient"
                LIMIT %s OFFSET %s
            """, (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%', limit, offset))
            rows = curs.fetchall()
        return rows
    finally:
        releaseConn(conn)

def passwordTimeLimitRespected(userID):
    # Vérifier le délai de 24h
    clientInfo = getUserInfo(userID)
    last_change = clientInfo[15]
    if last_change:
        from datetime import datetime
        now = datetime.now(timezone.utc)
        diff = now - last_change.astimezone(timezone.utc)
        if diff.total_seconds() < 86400:
            return False
    return True

def passwordTimeLimitRemove(userID):
    conn = connectToDB()

    with conn.cursor() as curs:
        curs.execute('UPDATE client SET last_password_change = NULL WHERE \"userID\" = %s', (userID,))            
        rows = curs.fetchall()

    conn.commit()
    
    releaseConn(conn)
        
    return rows

def countAllUsers(search=''):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT COUNT(*) FROM client
                WHERE "firstName" ILIKE %s OR "lastName" ILIKE %s OR email ILIKE %s OR CAST("idClient" AS TEXT) LIKE %s
            """, (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'))
            return curs.fetchone()[0]
    finally:
        releaseConn(conn)

def updateLastLogin(idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE client SET last_login = NOW() WHERE "idClient" = %s',
                (idClient,)
            )
            conn.commit()
    finally:
        releaseConn(conn)

#================
# Notifications
#================

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

def deleteNotification(userID, notifID):
    conn = connectToDB()

    with conn.cursor() as curs:
        curs.execute('DELETE FROM notification WHERE \"userID\" = %s AND \"id\" = %s', (userID, notifID))            
        rows = curs.fetchall()

    conn.commit()
    
    releaseConn(conn)
        
    return rows

def getAdminStats():
    conn = connectToDB()

    with conn.cursor() as curs:
        curs.execute('SELECT * FROM ')            
        rows = curs.fetchall()

    conn.commit()
    
    releaseConn(conn)
        
    return rows

#================
# Ingrédients
#================

def getOrCreateIngredient(nom):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            # Cherche si l'ingrédient existe déjà
            curs.execute(
                'SELECT "idIngredient" FROM ingredient WHERE LOWER(nom) = LOWER(%s)',
                (nom,)
            )
            row = curs.fetchone()
            if row:
                return row[0]
            
            # Sinon on le crée
            curs.execute(
                'INSERT INTO ingredient (nom) VALUES (%s) RETURNING "idIngredient"',
                (nom,)
            )
            idIngredient = curs.fetchone()[0]
            conn.commit()
            return idIngredient
    finally:
        releaseConn(conn)

def createRecette(idClient, nom, portions, instructions):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                """INSERT INTO recette ("idClient", nom, portions, instructions) 
                   VALUES (%s, %s, %s, %s) RETURNING "idRecette" """,
                (idClient, nom, portions, instructions)
            )
            idRecette = curs.fetchone()[0]
            conn.commit()
            return idRecette
    finally:
        releaseConn(conn)

def addIngredientToRecette(idRecette, nom, quantite, unite):
    idIngredient = getOrCreateIngredient(nom)
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                """INSERT INTO recette_ingredient ("idRecette", "idIngredient", quantite, unite)
                   VALUES (%s, %s, %s, %s)""",
                (idRecette, idIngredient, quantite, unite)
            )
            conn.commit()
    finally:
        releaseConn(conn)


print("database.py done.")