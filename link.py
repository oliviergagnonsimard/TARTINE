from database import *
from scrapping import *

conn = connectToDB()
with conn.cursor() as curs:
    curs.execute("SELECT * FROM discount")
    print(curs.fetchall())


    print("--------------------------")

    ans = sendPDF("MAXI")

    curs.execute(ans)
    curs.execute("SELECT * FROM discount")
    print(curs.fetchall())

a = input("commit to db? (y/n): ")
if a == "y":
    conn.commit()