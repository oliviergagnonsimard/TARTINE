from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from main import getNameFromId, getUserRecipes, addRecipe, delRecipe, modifyRecipe, getRecipe,getAllEpiceries, getFlyerWeek, getNbPagesFlyer, checkIfFlyersAlreadyDownloaded, getFlyerStartWeekStr, getUserInfo
from main import getURI
import threading

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

@app.route('/downloadFlyers')
def downloadFlyers():
        if checkIfFlyersAlreadyDownloaded():
            print("Flyers are already downloaded for this week.")
            return "Flyers are already downloaded for this week."
        print("Downloading new flyers...")
        from download import DownloadAllCirculaires
        DownloadAllCirculaires()
        print("Flyers have been downloaded.")


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
    
    
@app.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    userID = session.get("userID")
    data = getUserRecipes(userID)
    name = session.get("name")
    clientInfo = getUserInfo(userID)
    return render_template('dashboard.html', userID=userID, headings=headings, data=data, name=name, clientInfo=clientInfo)

@app.route('/flyers')
def flyers():
    areFlyersDownloaded = checkIfFlyersAlreadyDownloaded()
    if not areFlyersDownloaded:
        threading.Thread(target=downloadFlyers).start()
    epiceries = getAllEpiceries()
    week = getFlyerWeek()
    if request.args.get("ready") == "1":
        areFlyersDownloaded = True
    return render_template('flyers.html', epiceries=epiceries, week=week, downloading=not areFlyersDownloaded)

@app.route('/flyers/status')
def flyers_status():
    downloading = checkIfFlyersAlreadyDownloaded()
    return {"downloading": not downloading}

@app.route('/flyers/maxi')
def maxi():
    nbPages = getNbPagesFlyer()[0]
    week_start = getFlyerStartWeekStr()
    return render_template('flyers/maxi.html', nbPages=nbPages, week_start=week_start)

@app.route('/flyers/metro')
def metro():
    nbPages = getNbPagesFlyer()[1]
    week_start = getFlyerStartWeekStr()
    return render_template('flyers/metro.html', nbPages=nbPages, week_start=week_start)

@app.route('/flyers/iga')
def iga():
    nbPages = getNbPagesFlyer()[2]
    week_start = getFlyerStartWeekStr()
    return render_template('flyers/iga.html', nbPages=nbPages, week_start=week_start)

@app.route('/flyers/superc')
def superc():
    nbPages = getNbPagesFlyer()[3]
    week_start = getFlyerStartWeekStr()
    return render_template('flyers/superc.html', nbPages=nbPages, week_start=week_start)

@app.route('/flyers/provigo')
def provigo():
    nbPages = getNbPagesFlyer()[4]
    week_start = getFlyerStartWeekStr()
    return render_template('flyers/provigo.html', nbPages=nbPages, week_start=week_start)

@app.route('/recipes')
def recipes():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    userID = session.get("userID")
    data = getUserRecipes(userID)
    name = session.get("name")
    return render_template('recipes.html', userID=userID, headings=headings, data=data, name=name)


if __name__ == "__main__":
    app.run(debug=True)