from database import *
from scrapping import *
import os
import psycopg2
import google.generativeai

message = """
Give me only an SQL statement as an answer to add 3 example values to the given table.
My table 'client' has the following columns:
1. name
2. age
3. email
"""

conn = connectToDB()
with conn.cursor() as curs:
    curs.execute("SELECT * FROM client")
    print(curs.fetchall())

    chat = model.start_chat()
    ans = chat.send_message(message).text

    parsed = parseSQL(ans)

    curs.execute(parsed)
    curs.execute("SELECT * FROM client")
    print(curs.fetchall())

a = input("commit to db? (y/n): ")
if a == "y":
    conn.commit()



    