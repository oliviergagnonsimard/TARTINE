import requests
import os
import platform
from bs4 import BeautifulSoup
from urllib.parse import urljoin
PLATFORM = platform.system()

SLASHS = "\\"

if PLATFORM == "Linux":
    SLASHS = "/"

DIR_PATH = os.path.dirname(os.path.realpath(__file__))


downloaded_pngs_path = DIR_PATH + SLASHS + "downloaded_pngs"
if not os.path.exists(downloaded_pngs_path):
    os.makedirs(downloaded_pngs_path)

def DownloadIMGFromWeb(url, differentiator):
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch the following URL: {url}")

    parsedHTML = BeautifulSoup(response.text, "html.parser")

    img_tags = parsedHTML.find_all("img")
    image_urls = []

    for tag in img_tags:
        print(tag)
        img_src = tag.get("src")

        # On join l'URL de base du site + le src de l'image
        full_url = urljoin(url, img_src)
        print(full_url)

        if full_url.lower().__contains__(differentiator):
            image_urls.append(full_url)

    Compteur = 0
    # MAINTENANT QU'ON A LES URLS ON LES TÉLÉCHARGES
    print("VOICI LES URLS =========================================================================")    
    for url in image_urls:

        ans = requests.get(url)

        downloadedFile = downloaded_pngs_path + SLASHS + "downloaded_pngs_" + Compteur.__str__() + ".png"

        with open(downloadedFile, "wb") as f:
            f.write(ans.content)

        Compteur += 1

def DownloadAllIMGFromCirculaire(url, differentiator):
    print("A FAIRE")


DownloadIMGFromWeb(url="https://www.circulaires.com/maxi/circulaire/?ref=circulaires.com&n=&p=&sname=maxi&region=&sttr=1747627200&str=4369068",
                   differentiator="/maxi/circulaire/")