from database import *
from scrapping import *

conn = connectToDB()

def SendOneIMGDiscountsToDB(filename):
    with conn.cursor() as curs:
        ans = sendIMG(filename)

        curs.execute(ans)

    confirmCommitToDB(conn)

downloaded_pngs_path = DIR_PATH + SLASHS + "downloaded_pdfs"
downloadedFile = downloaded_pngs_path + SLASHS + "downloaded_pdf_0.png"

SendOneIMGDiscountsToDB(downloadedFile)