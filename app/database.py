# Librairie pour intéragir avec notre database
from psycopg2 import pool
import os
import platform
from dotenv import load_dotenv
from datetime import timezone, datetime
from main import getFlyerStartWeekStr
from r2 import imageExists
from extensions import cache

FREE_RECIPE_LIMIT = 10

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

VALID_UNITS = ['unité', 'g', 'kg', 'lb', 'L', 'ml', 'paquet', 'sac', 'caisse',
               'botte', 'panier', 'pinte', 'chopine', 'canette', 'rouleau',
               'capsule', 'feuille', 'barre', 'biscuit', 'm']

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
                INSERT INTO users ("firstName", "lastName", "birthDate", "email", "password_hash")
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
                'UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL, '
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
                SELECT * FROM leaderboard
                LIMIT %s OFFSET %s
            """, (limit, offset))

            result = curs.fetchall()
            return result

    except Exception as e:
        print(f"SQL ERROR (getLeaderboard): {e}")
        return []

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
                FROM users 
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
                'UPDATE users SET "email" = %s, "firstName" = %s, "lastName" = %s, "birthDate" = %s, "ranked" = %s WHERE "idClient" = %s',
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
            curs.execute('SELECT * FROM users')
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
            curs.execute('SELECT "firstName", "lastName" FROM users WHERE "idClient" = %s', (idClient,))
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
            curs.execute('SELECT * FROM users WHERE "email" = %s', (email,))
            return curs.fetchone()
    except Exception as e:
        print(f"SQL ERROR (getUserByEmail): {e}")
    finally:
        releaseConn(conn)


# ====================================
# ====================================
#               RECIPES
# ====================================
# ====================================
def getRecipeWithIngredients(idRecette, idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idRecette", nom, instructions, portions, "createdAt" AT TIME ZONE 'America/Montreal'
                FROM recipe
                WHERE "idRecette" = %s AND "idClient" = %s
            """, (idRecette, idClient))
            recette = curs.fetchone()

            curs.execute("""
                SELECT ri.nom, ri.quantite, ri.unite, ri."idCatalog"
                FROM recipe_ingredient ri
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
                SELECT r."idRecette", r.ordre, r.nom, r.portions,
                       TO_CHAR(r."createdAt" AT TIME ZONE 'America/Montreal', 'DD/MM/YYYY HH24hMI'),
                       CASE
                           WHEN COUNT(ri."idRecette") > 0
                                AND COUNT(ri."idRecette") = COUNT(ri."idCatalog")
                           THEN TRUE
                           ELSE FALSE
                       END AS fully_validated
                FROM recipe r
                LEFT JOIN recipe_ingredient ri ON ri."idRecette" = r."idRecette"
                WHERE r."idClient" = %s
                GROUP BY r."idRecette", r.ordre, r.nom, r.portions, r."createdAt"
                ORDER BY r.ordre ASC, r."idRecette" ASC
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

def createRecipe(idClient, nom, portions, instructions):
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

def updateRecipe(idClient, idRecette, nom, portions, instructions, ingredients):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            portions = portions if portions != '' else None
            curs.execute("""
                UPDATE recipe SET nom = %s, portions = %s, instructions = %s
                WHERE "idRecette" = %s AND "idClient" = %s
            """, (nom, portions, instructions, idRecette, idClient))

            curs.execute('DELETE FROM recipe_ingredient WHERE "idRecette" = %s', (idRecette,))

            for ing in ingredients:
                if not ing['nom'].strip():
                    continue
                
                quantite = ing['quantite'] if ing['quantite'] != '' else None
                
                curs.execute(
                    """INSERT INTO recipe_ingredient ("idRecette", "idCatalog", nom, quantite, unite)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (idRecette, ing.get('idCatalog'), ing['nom'], quantite, ing['unite'])
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
                DELETE FROM users
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
                FROM users 
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
            curs.execute('UPDATE users SET last_password_change = NULL WHERE "idClient" = %s', (userID,))
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
                SELECT COUNT(*) FROM users
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
                'UPDATE users SET last_login = NOW() WHERE "idClient" = %s',
                (idClient,)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateLastLogin): {e}")
    finally:
        releaseConn(conn)

def getUserRole(idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'SELECT role FROM users WHERE "idClient" = %s',
                (idClient,)
            )
            return curs.fetchone()[0]
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateLastLogin): {e}")
    finally:
        releaseConn(conn)

def getUserRank(idClient):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                'SELECT classement, score FROM leaderboard WHERE idClient = %s',
                (idClient,)
            )
            return curs.fetchone()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateLastLogin): {e}")
    finally:
        releaseConn(conn)

# ====================================
# ====================================
#              CATALOGUE
# ====================================
# ====================================
def getCatalogItems():
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idIngredient", nom FROM catalog
                WHERE is_validated = TRUE
                ORDER BY nom ASC
            """)
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getCatalogItems): {e}")
    finally:
        releaseConn(conn)

def saveCatalogDiscountMatches(matches, week_start):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            # Vide les anciens matches de la semaine avant de réinssérer
            curs.execute('DELETE FROM catalog_discount WHERE week_start = %s', (week_start,))

            curs.execute('SELECT "idIngredient" FROM catalog')
            valid_catalog_ids = {row[0] for row in curs.fetchall()}

            for m in matches:
                catalog_id = m.get("catalog_id")
                discount_id = m.get("discount_id")

                if catalog_id not in valid_catalog_ids:
                    continue

                curs.execute("""
                    INSERT INTO catalog_discount ("idCatalog", "idDiscount", week_start)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (catalog_id, discount_id, week_start))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (saveCatalogDiscountMatches): {e}")
    finally:
        releaseConn(conn)

def getBestDiscountForRecipe(idRecette):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT 
                    d.discount_pct,
                    d.original_price,
                    d.discounted_price,
                    s.nom AS store,
                    cat.nom AS ingredient
                FROM recipe_ingredient ri
                JOIN catalog_discount cd ON cd."idCatalog" = ri."idCatalog"
                JOIN discount d ON d.id = cd."idDiscount"
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                JOIN catalog cat ON cat."idIngredient" = ri."idCatalog"
                WHERE ri."idRecette" = %s
                ORDER BY d.discount_pct DESC NULLS LAST
                LIMIT 1
            """, (idRecette,))
            return curs.fetchone()
    except Exception as e:
        print(f"SQL ERROR (getBestDiscountForRecipe): {e}")
    finally:
        releaseConn(conn)



# ====================================
# ====================================
#            NOTIFICATIONS
# ====================================
# ====================================

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

def notifyAllUsers(title, message):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                INSERT INTO notification ("idClient", title, message)
                SELECT "idClient", %s, %s FROM users
            """, (title, message))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (notifyAllUsers): {e}")
    finally:
        releaseConn(conn)

# ====================================
# ====================================
#            INGRÉDIENTS
# ====================================
# ====================================
def addIngredientToRecipe(idRecette, nom, quantite, unite, idCatalog=None):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute(
                """INSERT INTO recipe_ingredient ("idRecette", "idCatalog", nom, quantite, unite)
                   VALUES (%s, %s, %s, %s, %s)""",
                (idRecette, idCatalog, nom, quantite, unite)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (addIngredientToRecette): {e}")
    finally:
        releaseConn(conn)

def searchIngredients(query):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT "idIngredient", nom, category
                FROM catalog
                WHERE nom ILIKE %s AND is_validated = TRUE
                ORDER BY nom ASC
                LIMIT 8
            """, (f'%{query}%',))
            return curs.fetchall()
    finally:
        releaseConn(conn)

def getIngredientDiscounts(idRecette):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT DISTINCT ON (ri."idCatalog")
                    ri."idCatalog",
                    d.discount_pct,
                    d.original_price,
                    d.discounted_price,
                    s.nom AS store
                FROM recipe_ingredient ri
                JOIN catalog_discount cd ON cd."idCatalog" = ri."idCatalog"
                JOIN discount d ON d.id = cd."idDiscount"
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE ri."idRecette" = %s
                ORDER BY ri."idCatalog", d.discount_pct DESC NULLS LAST
            """, (idRecette,))
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getIngredientDiscounts): {e}")
        return []
    finally:
        releaseConn(conn)

# ====================================
# ====================================
#              DISCOUNT
# ====================================
# ====================================

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
    with conn.cursor() as curs:
        cursor.execute("TRUNCATE discount CASCADE")
    conn.commit()
    cursor.close()
    releaseConn(conn)

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

@cache.memoize(timeout=3600)  # 1 hour
def getWeeklyDiscounts(limit=5):
    conn = connectToDB()
    with conn.cursor() as curs:
        if limit == 0:
            curs.execute("""
                        SELECT s.nom, d.product_name, d.quantity, d.unit_of_measure,
                               d.original_price, d.discounted_price, d.discount_pct
                        FROM discount d
                        JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                        WHERE d.week_start = %s AND d.discount_pct IS NOT NULL AND d.discounted_price IS NOT NULL
                        ORDER BY d.discount_pct DESC
                    """, (getFlyerStartWeekStr(),))
            rows = curs.fetchall()
        else:
            curs.execute("""
                SELECT s.nom, d.product_name, d.quantity, d.unit_of_measure,
                    d.original_price, d.discounted_price, d.discount_pct
                FROM discount d
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE d.week_start = %s AND d.discount_pct IS NOT NULL AND d.discounted_price IS NOT NULL
                ORDER BY d.discount_pct DESC
                LIMIT %s
            """, (getFlyerStartWeekStr(), limit))
            rows = curs.fetchall()
    releaseConn(conn)
    return rows

@cache.cached(timeout=5)
def checkIfFlyersAlreadyDownloaded():
    epiceries = getAllEpiceries()
    weekStr = getFlyerStartWeekStr()

    for epicerie in epiceries:
        folder_prefix = f"circulaires/{epicerie}_{weekStr}/"
        if not any(
            imageExists(f"{folder_prefix}{epicerie}{suffix}.png")
            for suffix in ("0", "2", "4", "6")
        ):
            return False
    return True

def getDiscountsAdmin(page=1, limit=20, search=''):
    conn = connectToDB()
    offset = (page - 1) * limit
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT d.id, s.nom, d.product_name, d.quantity, d.unit_of_measure,
                       d.original_price, d.discounted_price, d.discount_pct, d.week_start
                FROM discount d
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE d.product_name ILIKE %s 
                   OR s.nom ILIKE %s 
                   OR CAST(d.id AS TEXT) = %s
                ORDER BY d.week_start DESC, d.id DESC
                LIMIT %s OFFSET %s
            """, (f'%{search}%', f'%{search}%', search, limit, offset))
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getDiscountsAdmin): {e}")
        return []
    finally:
        releaseConn(conn)

def countDiscountsAdmin(search=''):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT COUNT(*)
                FROM discount d
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE d.product_name ILIKE %s 
                   OR s.nom ILIKE %s 
                   OR CAST(d.id AS TEXT) = %s
            """, (f'%{search}%', f'%{search}%', search))
            return curs.fetchone()[0]
    except Exception as e:
        print(f"SQL ERROR (countDiscountsAdmin): {e}")
        return 0
    finally:
        releaseConn(conn)

def updateDiscount(idDiscount, product_name, quantity, unit_of_measure, original_price, discounted_price, discount_pct):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                UPDATE discount
                SET product_name = %s, quantity = %s, unit_of_measure = %s,
                    original_price = %s, discounted_price = %s, discount_pct = %s
                WHERE id = %s
            """, (product_name, quantity, unit_of_measure, original_price, discounted_price, discount_pct, idDiscount))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"SQL ERROR (updateDiscount): {e}")
    finally:
        releaseConn(conn)

def getDiscountsAdmin(page=1, limit=20, search='', invalid_units_only=False):
    conn = connectToDB()
    offset = (page - 1) * limit
    try:
        with conn.cursor() as curs:
            query = """
                SELECT d.id, s.nom, d.product_name, d.quantity, d.unit_of_measure,
                       d.original_price, d.discounted_price, d.discount_pct, d.week_start
                FROM discount d
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE (d.product_name ILIKE %s OR s.nom ILIKE %s OR CAST(d.id AS TEXT) = %s)
            """
            params = [f'%{search}%', f'%{search}%', search]

            if invalid_units_only:
                query += " AND d.unit_of_measure IS NOT NULL AND NOT (d.unit_of_measure = ANY(%s))"
                params.append(VALID_UNITS)

            query += " ORDER BY d.week_start DESC, d.id DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            curs.execute(query, params)
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getDiscountsAdmin): {e}")
        return []
    finally:
        releaseConn(conn)

def countDiscountsAdmin(search='', invalid_units_only=False):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            query = """
                SELECT COUNT(*)
                FROM discount d
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE (d.product_name ILIKE %s OR s.nom ILIKE %s OR CAST(d.id AS TEXT) = %s)
            """
            params = [f'%{search}%', f'%{search}%', search]

            if invalid_units_only:
                query += " AND d.unit_of_measure IS NOT NULL AND NOT (d.unit_of_measure = ANY(%s))"
                params.append(VALID_UNITS)

            curs.execute(query, params)
            return curs.fetchone()[0]
    except Exception as e:
        print(f"SQL ERROR (countDiscountsAdmin): {e}")
        return 0
    finally:
        releaseConn(conn)

def getCatalogDiscountMatchSample(week_start, limit=30):
    conn = connectToDB()
    try:
        with conn.cursor() as curs:
            curs.execute("""
                SELECT cat.nom AS catalog_nom, d.product_name AS discount_nom,
                       s.nom AS store, d.discount_pct, d.original_price, d.discounted_price
                FROM catalog_discount cd
                JOIN catalog cat ON cat."idIngredient" = cd."idCatalog"
                JOIN discount d ON d.id = cd."idDiscount"
                JOIN stores s ON s."idEpicerie" = d."idEpicerie"
                WHERE cd.week_start = %s
                ORDER BY RANDOM()
                LIMIT %s
            """, (week_start, limit))
            return curs.fetchall()
    except Exception as e:
        print(f"SQL ERROR (getCatalogDiscountMatchSample): {e}")
        return []
    finally:
        releaseConn(conn)


print("database.py done.")