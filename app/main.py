from database import *
import datetime

def clearConsole():
    os.system('cls')

conn = connectToDB()

def showClients():
    with conn.cursor() as curs:
        try:
            curs.execute(f"SELECT * FROM client")
            rows = curs.fetchall()
        except Exception as e:
            print(f"SQL ERROR: {e}")
            conn.rollback()
    
    return rows

def getNameFromId(idClient):
    with conn.cursor() as curs:
        try:
            curs.execute("SELECT name FROM client WHERE \"idClient\" = %s", (idClient,))
            name = curs.fetchone()[0]
        except Exception as e:
            print(f"SQL ERROR: {e}")
            conn.rollback()
    return name

def getUserRecipes(idClient: int):
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM recette WHERE \"idClient\" = %s ORDER BY \"idRecette\"", (idClient,))
        rows = curs.fetchall()
        return rows

def addRecipe(idClient, desc):
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

def delRecipe(idClient, idRecette):
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

def modifyRecipe(idClient, idRecette, newDesc):
    print(f"Modifying recipe {idRecette} from User {idClient}... to: {newDesc}")
    with conn.cursor() as curs:
        curs.execute("SELECT description FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
        row = curs.fetchone()
        curs.execute("UPDATE recette SET description = %s WHERE \"idClient\" = %s AND \"idRecette\" = %s", (newDesc, idClient, idRecette))
    conn.commit()
    print(f"Recipe {idRecette} from User {idClient} has been modified")

def getRecipe(idClient, idRecette):
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM recette WHERE \"idClient\" = %s AND \"idRecette\" = %s", (idClient, idRecette))
        row = curs.fetchall()
    return row

def getAllEpiceries():
    with conn.cursor() as curs:
        curs.execute("SELECT * FROM epicerie ORDER BY \"idEpicerie\"")
        rows = curs.fetchall()
    return rows

def getFlyerWeek():
    current_date = datetime.datetime.now().weekday()
    last_thursday = datetime.datetime.now() - datetime.timedelta(days=(current_date - 3) % 7)
    next_wednesday = last_thursday + datetime.timedelta(days=6)
    return last_thursday, next_wednesday

def getFlyerStartWeekStr():
    week = getFlyerWeek()
    return str(week[0].date())

def getNbPagesFlyer():
    nbPages = []
    dir_path = ["app/static/circulaires/maxi_" + getFlyerStartWeekStr(),
                "app/static/circulaires/metro_" + getFlyerStartWeekStr(),
                "app/static/circulaires/iga_" + getFlyerStartWeekStr(),
                "app/static/circulaires/superc_" + getFlyerStartWeekStr(),
                "app/static/circulaires/provigo_" + getFlyerStartWeekStr()]

    for path in dir_path:
        try:
            nbPages.append(len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))]))
        except Exception as e:
            print(f"Error accessing directory {path}: {e}")
            nbPages.append(0)  # Append 0 if there's an error accessing the directory

    return nbPages

def checkIfFlyersAlreadyDownloaded():
    epiceries = getAllEpiceries()
    weekStr = getFlyerStartWeekStr()
    dir_path = os.path.dirname(os.path.realpath(__file__))

    compteur = 0
    for epicerie in epiceries:
        nom = epicerie[1].lower()
        path = dir_path + SLASHS + "static" + SLASHS + "circulaires" + SLASHS + f"{nom}" + "_" + weekStr
        print(path)
        if not os.path.exists(path):
            return False
        compteur +=1
    return True
    
