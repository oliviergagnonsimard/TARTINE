# Librairie pour intéragir avec notre database
from psycopg2 import pool
import os
import platform
from dotenv import load_dotenv
from datetime import timezone, datetime
from matchingIngredients import matchIngredientsWithDiscounts

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
    user =   os.environ.get("DB_USER")
    pwd =    os.environ.get("DB_PASSWORD")
    host =   os.environ.get("DB_HOST")
    port =   os.environ.get("DB_PORT")
    dbName = os.environ.get("DB_NAME")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{dbName}"

def createUser(firstName, lastName, email, password_hash, birthday=None):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                INSERT INTO "user" ("firstName", "lastName", "birthDate", "email", "password_hash")
                VALUES (%s, %s, %s, %s, %s)
                RETURNING "idClient"
            """, (firstName, lastName, birthday, email, password_hash))
            userID = curs.fetchone()[0]
            conn.commit()
            return userID
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (createUser): {e}")
    finally:
        releaseConn(conn)

def updatePassword(idClient, password_hash):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE "user" SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL, '
                '"last_password_change" = NOW() WHERE "idClient" = %s',
                (password_hash, idClient)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updatePassword): {e}")
    finally:
        releaseConn(conn)

def getLeaderboard(page=1, limit=50):
    conn = connectToDB()
    offset = (page - 1) * limit
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT * FROM classement
                LIMIT %s OFFSET %s
            """, (limit, offset))
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getLeaderboard): {e}")
    finally:
        releaseConn(conn)

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
                FROM "user" 
                WHERE "idClient" = %s
            """, (idClient,))
            row = curs.fetchone()
            conn.commit()
            return row
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (getUserInfo): {e}")
    finally:
        releaseConn(conn)

def setUserInfo(idClient, Courriel, Prénom, Nom, Birthday, participe):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE "user" SET "email" = %s, "firstName" = %s, "lastName" = %s, "birthDate" = %s, "ranked" = %s WHERE "idClient" = %s',
                (Courriel, Prénom, Nom, Birthday, participe, idClient)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (setUserInfo): {e}")
    finally:
        releaseConn(conn)

def showClients():
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('SELECT * FROM "user"')
            return curs.fetchall()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (showClients): {e}")
    finally:
        releaseConn(conn)

def getNameFromId(idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('SELECT "firstName", "lastName" FROM "user" WHERE "idClient" = %s', (idClient,))
            row = curs.fetchone()
            if row:
                return f"{row[0]} {row[1]}"
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (getNameFromId): {e}")
    finally:
        releaseConn(conn)

def getUserByEmail(email):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('SELECT * FROM "user" WHERE "email" = %s', (email,))
            return curs.fetchone()
    except Exception as e:
        print(f"SQL ERROR (getUserByEmail): {e}")
    finally:
        releaseConn(conn)

def getRecetteWithIngredients(idRecette, idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idRecette", nom, portions, instructions, "createdAt"
                FROM recipe
                WHERE "idRecette" = %s AND "idClient" = %s
            """, (idRecette, idClient))
            recette = curs.fetchone()

            curs.execute("""
                SELECT i.nom, ri.quantite, ri.unite
                FROM recipe_ingredient ri
                JOIN ingredient i ON ri."idIngredient" = i."idIngredient"
                WHERE ri."idRecette" = %s
            """, (idRecette,))
            ingredients = curs.fetchall()

        return recette, ingredients
    except Exception as e:
        print(f"SQL ERROR (getRecetteWithIngredients): {e}")
    finally:
        releaseConn(conn)

def getUserRecipes(idClient: int):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idRecette", ordre, nom, portions, 
                    TO_CHAR("createdAt" AT TIME ZONE 'America/Montreal', 'DD/MM/YYYY HH24hMI')
                FROM recipe
                WHERE "idClient" = %s 
                ORDER BY ordre ASC, "idRecette" ASC
            """, (idClient,))
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getUserRecipes): {e}")
    finally:
        releaseConn(conn)

def updateRecipesOrder(idClient, ordre):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            for item in ordre:
                curs.execute(
                    'UPDATE recipe SET ordre = %s WHERE "idRecette" = %s AND "idClient" = %s',
                    (item['ordre'], item['id'], idClient)
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateRecipesOrder): {e}")
    finally:
        releaseConn(conn)

def addRecipe(idClient, desc):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('SELECT * FROM recipe WHERE "idClient" = %s ORDER BY "idRecette" DESC', (idClient,))
            newRecipeId = curs.fetchone()[1] + 1
            curs.execute("INSERT INTO recipe VALUES(%s, %s, %s)", (idClient, newRecipeId, desc))
            conn.commit()
            print(f"New recipe ({newRecipeId}) added to UserID: {idClient}")
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (addRecipe): {e}")
    finally:
        releaseConn(conn)

def updateRecette(idClient, idRecette, nom, portions, instructions, ingredients):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                UPDATE recipe SET nom = %s, portions = %s, instructions = %s
                WHERE "idRecette" = %s AND "idClient" = %s
            """, (nom, portions, instructions, idRecette, idClient))

            curs.execute('DELETE FROM recipe_ingredient WHERE "idRecette" = %s', (idRecette,))

            # FIX: resolve ingredients within the same connection instead of opening new ones
            for ing in ingredients:
                if not ing['nom'].strip():
                    continue
                curs.execute(
                    'SELECT "idIngredient" FROM ingredient WHERE LOWER(nom) = LOWER(%s)',
                    (ing['nom'],)
                )
                row = curs.fetchone()
                if row:
                    idIngredient = row[0]
                else:
                    curs.execute(
                        'INSERT INTO ingredient (nom) VALUES (%s) RETURNING "idIngredient"',
                        (ing['nom'],)
                    )
                    idIngredient = curs.fetchone()[0]

                curs.execute(
                    """INSERT INTO recipe_ingredient ("idRecette", "idIngredient", quantite, unite)
                       VALUES (%s, %s, %s, %s)""",
                    (idRecette, idIngredient, ing['quantite'], ing['unite'])
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateRecette): {e}")
    finally:
        releaseConn(conn)

def deleteRecipe(idClient, idRecette):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'SELECT "idRecette" FROM recipe WHERE "idClient" = %s AND "idRecette" = %s',
                (idClient, idRecette)
            )
            row = curs.fetchone()
            if row is None:
                return  # FIX: conn will still be released via finally
            curs.execute(
                'DELETE FROM recipe WHERE "idClient" = %s AND "idRecette" = %s',
                (idClient, idRecette)
            )
            conn.commit()
            print(f"Recipe ({idRecette}) deleted from UserID: {idClient}")
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (deleteRecipe): {e}")
    finally:
        releaseConn(conn)  # FIX: always released, even on early return

def modifyRecipe(idClient, idRecette, newDesc):
    conn = connectToDB()
    print(f"Modifying recipe {idRecette} from User {idClient}... to: {newDesc}")
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE recipe SET description = %s WHERE "idClient" = %s AND "idRecette" = %s',
                (newDesc, idClient, idRecette)
            )
            conn.commit()
        print(f"Recipe {idRecette} from User {idClient} has been modified")
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (modifyRecipe): {e}")
    finally:
        releaseConn(conn)

def getRecipe(idClient, idRecette):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'SELECT "idRecette", nom, instructions, portions, "createdAt" AT TIME ZONE \'America/Montreal\' '
                'FROM recipe WHERE "idClient" = %s AND "idRecette" = %s',
                (idClient, idRecette)
            )
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getRecipe): {e}")
    finally:
        releaseConn(conn)

def getAllEpiceries():
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('SELECT nom FROM stores ORDER BY "idEpicerie"')
            rows = curs.fetchall()
            return [row[0].lower() for row in rows]
    except Exception as e:
        print(f"SQL ERROR (getAllEpiceries): {e}")
    finally:
        releaseConn(conn)

def deleteUnverifiedAccounts():
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                DELETE FROM "user"
                WHERE is_verified = FALSE 
                AND "creationDate" < NOW() - INTERVAL '24 hours'
            """)
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (deleteUnverifiedAccounts): {e}")
    finally:
        releaseConn(conn)

def getAllUsers(page=1, limit=20, search=''):
    offset = (page - 1) * limit
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idClient", email, "firstName", "lastName", role, is_verified, "last_password_change"
                FROM "user" 
                WHERE "firstName" ILIKE %s OR "lastName" ILIKE %s OR email ILIKE %s OR CAST("idClient" AS TEXT) LIKE %s
                ORDER BY "idClient"
                LIMIT %s OFFSET %s
            """, (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%', limit, offset))
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getAllUsers): {e}")
    finally:
        releaseConn(conn)

def passwordTimeLimitRespected(userID):
    clientInfo = getUserInfo(userID)
    last_change = clientInfo[15]
    if last_change:
        now = datetime.now(timezone.utc)
        diff = now - last_change.astimezone(timezone.utc)
        if diff.total_seconds() < 86400:
            return False
    return True

def passwordTimeLimitRemove(userID):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('UPDATE "user" SET last_password_change = NULL WHERE "idClient" = %s', (userID,))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (passwordTimeLimitRemove): {e}")
    finally:
        releaseConn(conn)

def countAllUsers(search=''):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT COUNT(*) FROM "user"
                WHERE "firstName" ILIKE %s OR "lastName" ILIKE %s OR email ILIKE %s OR CAST("idClient" AS TEXT) LIKE %s
            """, (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'))
            return curs.fetchone()[0]
    except Exception as e:
        print(f"SQL ERROR (countAllUsers): {e}")
    finally:
        releaseConn(conn)

def updateLastLogin(idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE "user" SET last_login = NOW() WHERE "idClient" = %s',
                (idClient,)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateLastLogin): {e}")
    finally:
        releaseConn(conn)

#================
# Notifications
#================

def createNotification(idClient, title, message):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'INSERT INTO notification ("idClient", title, message) VALUES (%s, %s, %s)',
                (idClient, title, message)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (createNotification): {e}")
    finally:
        releaseConn(conn)

def getNotifications(idClient, hidden=True):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'SELECT id, title, message, "isRead", "creationDate" AT TIME ZONE \'America/Montreal\' FROM notification '
                'WHERE "idClient" = %s AND "hidden" = %s ORDER BY "creationDate" DESC LIMIT 20',
                (idClient, hidden)
            )
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getNotifications): {e}")
    finally:
        releaseConn(conn)

def readNotification(idClient, idNotif):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE notification SET "isRead" = TRUE WHERE "idClient" = %s AND id = %s',
                (idClient, idNotif)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (readNotification): {e}")
    finally:
        releaseConn(conn)

def dismissNotification(idClient, idNotif):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'UPDATE notification SET "hidden" = TRUE WHERE "idClient" = %s AND id = %s',
                (idClient, idNotif)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (dismissNotification): {e}")
    finally:
        releaseConn(conn)

def deleteNotification(userID, idNotif):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'DELETE FROM notification WHERE "idClient" = %s AND id = %s',
                (userID, idNotif)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (deleteNotification): {e}")
    finally:
        releaseConn(conn)

#================
# Ingrédients
#================

def getOrCreateIngredient(nom):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'SELECT "idIngredient" FROM ingredient WHERE LOWER(nom) = LOWER(%s)',
                (nom,)
            )
            row = curs.fetchone()
            if row:
                return row[0]
            curs.execute(
                'INSERT INTO ingredient (nom) VALUES (%s) RETURNING "idIngredient"',
                (nom,)
            )
            idIngredient = curs.fetchone()[0]
            conn.commit()
            return idIngredient
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (getOrCreateIngredient): {e}")
    finally:
        releaseConn(conn)

def createRecette(idClient, nom, portions, instructions):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                """INSERT INTO recipe ("idClient", nom, portions, instructions) 
                   VALUES (%s, %s, %s, %s) RETURNING "idRecette" """,
                (idClient, nom, portions, instructions)
            )
            idRecette = curs.fetchone()[0]
            conn.commit()
            return idRecette
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (createRecette): {e}")
    finally:
        releaseConn(conn)

def addIngredientToRecette(idRecette, nom, quantite, unite):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            # Resolve or create ingredient within the same connection
            curs.execute(
                'SELECT "idIngredient" FROM ingredient WHERE LOWER(nom) = LOWER(%s)',
                (nom,)
            )
            row = curs.fetchone()
            if row:
                idIngredient = row[0]
            else:
                curs.execute(
                    'INSERT INTO ingredient (nom) VALUES (%s) RETURNING "idIngredient"',
                    (nom,)
                )
                idIngredient = curs.fetchone()[0]

            curs.execute(
                """INSERT INTO recipe_ingredient ("idRecette", "idIngredient", quantite, unite)
                   VALUES (%s, %s, %s, %s)""",
                (idRecette, idIngredient, quantite, unite)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (addIngredientToRecette): {e}")
    finally:
        releaseConn(conn)

def insertDiscount(idEpicerie, week_start, product_name, discount_pct, original_price, discounted_price, page_number=None, quantity=None, unit_of_measure=None):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                INSERT INTO discount ("idEpicerie", week_start, product_name, discount_pct, original_price, discounted_price, page_number, quantity, unit_of_measure)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (idEpicerie, week_start, product_name, discount_pct, original_price, discounted_price, page_number, quantity, unit_of_measure))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (insertDiscount): {e}")
    finally:
        releaseConn(conn)

def clearDiscounts():
    conn = connectToDB()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM discount")
    conn.commit()
    cursor.close()
    conn.close()

def getDiscountsForWeek(week_start):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT d.id, d.product_name, d.discount_pct, d.original_price, d.discounted_price, s.nom
                FROM discount d
                JOIN stores s ON d."idEpicerie" = s."idEpicerie"
                WHERE d.week_start = %s
            """, (week_start,))
            return curs.fetchall()
    finally:
        releaseConn(conn)

def getIdEpicerie(nom):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute('SELECT "idEpicerie" FROM stores WHERE LOWER(nom) = LOWER(%s)', (nom,))
            row = curs.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"SQL ERROR (getIdEpicerie): {e}")
    finally:
        releaseConn(conn)


print("database.py done.")