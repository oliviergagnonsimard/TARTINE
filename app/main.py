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

        
# if __name__ == "__main__":
#     if len(sys.argv) > 0:
#         data = getUserRecipes(sys.argv[1])
#         with open("output.json", 'w', encoding='utf-8') as f:
#             json.dump(data, f, indent=4)
#         exit()


# while True:
#     print(helpChat)
#     ask = input("Choice: ")

#     if ask == "1":
#         addRecipe()
#         continue

#     if ask == "2":
#         modifyRecipe()
#         continue

#     if ask == "3":
#         deleteRecipe()
#         continue

#     if ask == "4":
#         SeeRecipes()
#         continue

#     if ask == "0":
#         exit()