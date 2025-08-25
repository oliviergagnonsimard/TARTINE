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


downloaded_pngs_path = DIR_PATH + SLASHS + "circulaires"
if not os.path.exists(downloaded_pngs_path):
    os.makedirs(downloaded_pngs_path)

def DownloadIMGFromWeb(url, filter, compteur, epicerie):
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch the following URL: {url}")

    parsedHTML = BeautifulSoup(response.text, "html.parser")

    img_tags = parsedHTML.find_all("img")
    image_urls = []


    for tag in img_tags:
        img_src = tag.get("src")

        # On join l'URL de base du site + le src de l'image
        full_url = urljoin(url, img_src)

        if full_url.lower().__contains__(filter):
            print(full_url)
            image_urls.append(full_url)


    # MAINTENANT QU'ON A LES URLS, ON LES TÉLÉCHARGES
    for url in image_urls:

        ans = requests.get(url)

        downloadedFileDIR = downloaded_pngs_path + SLASHS + epicerie
        if not os.path.exists(downloadedFileDIR):
            os.makedirs(downloadedFileDIR)
        downloadedFile = downloadedFileDIR + SLASHS + epicerie + str(compteur) + ".png"

        with open(downloadedFile, "wb") as f:
            f.write(ans.content)

        compteur += 1

def DownloadAllIMGFromCirculaire(url, filter, epicerie):
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch the following URL: {url}")

    parsedHTML = BeautifulSoup(response.text, "html.parser")

    url_tags = parsedHTML.find_all("a")
    all_IMGurls = []

    for tag in url_tags:
        tag_href = tag.get("href")
        full_url = urljoin(url, tag_href)

        if full_url.lower().__contains__(filter) and not full_url in all_IMGurls:
            all_IMGurls.append(full_url)

    compteur = 0
    for this_url in all_IMGurls:
        DownloadIMGFromWeb(this_url, filter, compteur, epicerie)
        compteur +=2
        print("======================================================================") 

def getAllNewUrls():
    urlsDebase = ["https://www.circulaires.com/maxi/",
                  "https://www.circulaires.com/supermarche-iga/",
                  "https://www.circulaires.com/metro/",
                  "https://www.circulaires.com/superc/",
                  "https://www.circulaires.com/provigo/"]

    all_urls = []
    for url in urlsDebase:
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch the following URL: {url}")

        parsedHTML = BeautifulSoup(response.text, "html.parser")

        url_tags = parsedHTML.find_all("a")

        for tag in url_tags:
            tag_href = tag.get("href")
            full_url = urljoin(url, tag_href)

            if full_url.__contains__("/circulaire/") and not full_url in all_urls:
                all_urls.append(full_url)
        
    return all_urls

def DownloadAllCirculaires():
    urls = getAllNewUrls()
    for this_url in urls:
        lastSlash = this_url.rfind("/")
        filtre = this_url[28:lastSlash]
        name = filtre[0:filtre.rfind("/")]
        DownloadAllIMGFromCirculaire(url=this_url,
                               filter=filtre,
                               epicerie=name)


DownloadAllCirculaires()