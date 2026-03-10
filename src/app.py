# ============================================================
# app.py - Application Flask avec affichage des articles MongoDB
# ============================================================

# 1. Imports Flask
from flask import Flask, render_template

# 2. Import de la connexion MongoDB
from BdMongo import db, articles

# 3. Création de l'application Flask
app = Flask(__name__)


# 4. Route principale
@app.route("/")
def index():
    return "Application Flask + MongoDB opérationnelle"


# 5. Route /articles : affiche les 20 derniers articles
@app.route("/articles")
def liste_articles():
    # Récupère les 20 articles les plus récents, triés par date de publication
    resultats = articles.find().sort("publication_date", -1).limit(20)
    # Convertit le curseur MongoDB en liste Python
    liste = list(resultats)
    return render_template("articles.html", articles=liste)


# 6. Lancement du serveur
if __name__ == "__main__":
    app.run(debug=True)