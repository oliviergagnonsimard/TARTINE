from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from main import getNameFromId, getUserRecipes, addRecipe, delRecipe

DB_URL = "postgresql://postgres:2nvvhejBwQF62eroQzA9@tartinedb.cdwy0g0205gp.us-east-2.rds.amazonaws.com/postgres"

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

data = (
    ("1", "2", "3"),
    ("4", "5", "6")
)

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
    
@app.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    userID = session.get("userID")
    data = session.get("data")
    name = session.get("name")
    return render_template('dashboard.html', userID=userID, headings=headings, data=data, name=name)

if __name__ == "__main__":
    app.run(debug=True)