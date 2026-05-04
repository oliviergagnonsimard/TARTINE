from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import getURI
from download import DownloadAllCirculaires
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import os
from main import *
from r2 import imageExists, getImageUrl

STORES = ['maxi', 'metro', 'iga', 'superc', 'provigo']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_URL = getURI()

app = Flask(__name__, template_folder='templates')
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.secret_key = "secret"
db = SQLAlchemy(app)


class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = getNameFromId(id)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

headings = ("idClient", "idRecette", "Description")

def resetSessionData(userID):
    session["userID"] = userID
    session["data"] = getUserRecipes(userID)
    session["name"] = getNameFromId(userID)

def triggerDownloadFlyers():
    if checkIfFlyersAlreadyDownloaded():
        print("Flyers already downloaded.")
        return
    DownloadAllCirculaires()
    print("Flyers downloaded.")


@app.route('/refreshFlyers')
def refreshFlyers():
     print()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == 'POST':
        userID = request.form['userID']

        login_user(User(userID))        

        session["userID"] = userID
        session["data"] = getUserRecipes(userID)
        session["name"] = getNameFromId(userID)
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))
    
@app.route('/addRecipee', methods=['POST', 'GET'])
def addRecipee():
    userID = session.get("userID")
    if request.method == 'POST':
        addRecipe(session["userID"], request.form["desc"])
        session["userID"] = userID
        session["data"] = getUserRecipes(userID)
        session["name"] = getNameFromId(userID)
        return redirect(url_for('dashboard'))
    else:
        return render_template('addRecipee.html')
    
@app.route('/delRecipee', methods=['POST', 'GET'])
def delRecipee():
    userID = session.get("userID")
    if request.method == 'POST':
        delRecipe(session["userID"], request.form["idRecette"])
        session["userID"] = userID
        session["data"] = getUserRecipes(userID)
        session["name"] = getNameFromId(userID)
        return redirect(url_for('dashboard'))
    else:
        userID = session.get("userID")
        data = session.get("data")
        name = session.get("name")
        return render_template('delRecipee.html', userID=userID, headings=headings, data=data, name=name)
    
@app.route('/modRecipee', methods=['POST', 'GET'])
def modRecipee():
    userID = session.get("userID")
    session["userID"] = userID
    session["name"] = getNameFromId(userID)

    if request.method == "POST":
        desc = request.form.get("desc")
        idRecette = request.form.get("idRecette")
        modifyRecipe(userID, idRecette, desc)
        session["data"] = getUserRecipes(userID)  # actualise la liste complète
        return redirect(url_for("dashboard"))

    idRecetteArg = request.args.get("idRecette")
    recipe = getRecipe(userID, idRecetteArg)
    print(recipe)
    return render_template('modifyRecipee.html', userID=userID, headings=headings, data=recipe,
                                name=session["name"],
                                showDesc=True,
                                idRecette=idRecetteArg
                               )
    
    
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    userID = session.get("userID")
    
    if request.method == 'POST':
        email = request.form['email']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        birthday = request.form['birthday']
        participe = request.form.get('participe') == 'on'

        setUserInfo(userID, email, firstname, lastname, birthday, participe)
        return redirect(url_for('dashboard'))
    
    data = getUserRecipes(userID)
    name = session.get("name")
    clientInfo = getUserInfo(userID)
    return render_template('dashboard.html', userID=userID, headings=headings, data=data, name=name, clientInfo=clientInfo)

@app.route('/flyers')
def flyers():
    areFlyersDownloaded = checkIfFlyersAlreadyDownloaded()
    if not areFlyersDownloaded:
        threading.Thread(target=triggerDownloadFlyers).start()
    epiceries = getAllEpiceries()
    week = getFlyerWeek()
    return render_template('flyers.html', epiceries=epiceries, week=week, downloading=not areFlyersDownloaded)

@app.route('/flyers/status')
def flyers_status():
    downloading = checkIfFlyersAlreadyDownloaded()
    return {"downloading": not downloading}

from r2 import imageExists, getImageUrl

@app.route('/flyers/<store>')
def flyer(store):
    if store not in STORES:
        return 404
    
    week_start = getFlyerStartWeekStr()
    
    # Compte les pages disponibles dans R2
    nbPages = 0
    while imageExists(f"circulaires/{store}_{week_start}/{store}{nbPages}.png"):
        nbPages += 1
    
    # Génère les URLs R2 pour chaque page
    image_urls = [
        getImageUrl(f"circulaires/{store}_{week_start}/{store}{i}.png")
        for i in range(0, nbPages, 2)  # ton compteur va de 2 en 2
    ]
    
    return render_template('flyer.html', store=store, image_urls=image_urls, week_start=week_start)

@app.route('/recipes')
def recipes():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    userID = session.get("userID")
    data = getUserRecipes(userID)
    name = session.get("name")
    return render_template('recipes.html', userID=userID, headings=headings, data=data, name=name)

@app.route('/leaderboard')
@app.route('/leaderboard/<int:page>')
def leaderboard(page=1):
    leaderboard = getLeaderboard(page=page)
    headings = ( "Classement", "Nom", "ID", "Score")
    userId = session.get("userID")

    return render_template('leaderboard.html', leaderboard=leaderboard, headings=headings, page=page, current_Id=userId)

def downloadFlyersJob():
    print("⏰ Téléchargement automatique des circulaires...")
    if not checkIfFlyersAlreadyDownloaded():
        DownloadAllCirculaires()
        print("✅ Circulaires téléchargées et uploadées sur R2 !")
    else:
        print("✅ Circulaires déjà à jour !")

scheduler = BackgroundScheduler()
scheduler.add_job(
    downloadFlyersJob,
    'cron',
    day_of_week='thu',  # jeudi
    hour=3,
    minute=0,
    timezone='America/Montreal'  # ← important !
)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host='0.0.0.0', port=port, debug=debug)