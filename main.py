from database import *

helpChat = """
================
1) Create recipe
2) Modify recipe
3) Delete recipe
4) See recipes
0) Quit
================
"""

def clearConsole():
    os.system('cls')

conn = connectToDB()

def showClients():
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM client")
        rows = curs.fetchall()
        clearConsole()
        print("===================================")
        for row in rows:
            print(row)
        print("===================================")

def showRecipes(idClient: int):
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {idClient}")
        rows = curs.fetchall()
        print("===================================")
        for row in rows:
            print(row)
        print("===================================")

def SeeRecipes():
    with conn.cursor() as curs:
        showClients()
        id = input("idClient: ")
        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id}")
        rows = curs.fetchall()
        curs.execute(f"SELECT name FROM client WHERE \"idClient\" = {id}")
        name = curs.fetchone()[0]
        clearConsole()
        print("===================================")
        print(f"Voici les recettes enregistrées de {name}:")
        print()
        for row in rows:
            print(row)


def addRecipe():
    with conn.cursor() as curs:
        showClients()
        id = input("idClient: ")
        desc = input("Description de la recette: ")

        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id}")

        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id} ORDER BY \"idRecette\" DESC")
        newRecipeId = curs.fetchone()[1]
        newRecipeId += 1

        curs.execute(f"INSERT INTO recette VALUES({id}, {newRecipeId}, \'{desc}\')")
        clearConsole()
        showRecipes(id)
        print(f"New recipe ({newRecipeId}) added to UserID: {id}")
        confirmCommitToDB(conn)
        clearConsole()

def modifyRecipe():
    showClients()
    idC = input("idClient: ")
    clearConsole()
    showRecipes(idC)
    idR = input("idRecette: ")
    with conn.cursor() as curs:
        curs.execute(f"SELECT description FROM recette WHERE \"idClient\" = {idC} AND \"idRecette\" = {idR}")
        row = curs.fetchone()[0]
        print("Old description:")
        print(f"\"{row}\"")
        newDesc = input("New description: ")
        curs.execute(f"UPDATE recette SET description = \'{newDesc}\' WHERE \"idClient\" = {idC} AND \"idRecette\" = {idR}")
    clearConsole()
    showRecipes(idC)
    print(f"Recipe {idR} from User {idC} has been modified")
    confirmCommitToDB(conn)

def deleteRecipe():
    showClients()
    idC = input("idClient: ")
    clearConsole()
    showRecipes(idC)
    idR = input("idRecette: ")
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {idC} AND \"idRecette\" = {idR}")
        row = curs.fetchone()
        print(row)
        ask = input("Are you sure you want to delete this recipe? (y/n) ")
        if ask == "y":
            curs.execute(f"DELETE FROM recette WHERE \"idClient\" = {idC} AND \"idRecette\" = {idR}")
            clearConsole()
            showRecipes(idC)
            print(f"Recipe {idR} from User {idC} has been deleted")
            confirmCommitToDB(conn)
        clearConsole()
    
clearConsole()
while True:
    print(helpChat)
    ask = input("Choice: ")

    if ask == "1":
        addRecipe()
        continue

    if ask == "2":
        modifyRecipe()
        continue

    if ask == "3":
        deleteRecipe()
        continue

    if ask == "4":
        SeeRecipes()
        continue

    if ask == "0":
        exit()