# Application Flask avec dates converties en datetime

# 1. Imports Flask
from flask import Flask, render_template, request, redirect, abort

# 2. Imports MongoDB
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, timedelta

# 3. Imports pour le nuage de mots et le sitemap
from collections import Counter
import random
import re
import requests
import xml.etree.ElementTree as ET

# 4. Imports pour le scheduler
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# 5. Import des collections
from BdMongo import articles, consultations, subscriptions

# 6. Création de l'application Flask
app = Flask(__name__)

# 7. Filtre pour afficher publication_date quel que soit son type
#    - datetime → "dd/mm/yyyy à HH:MM"
#    - chaîne   → affichée telle quelle
#    - None     → "Date inconnue"
@app.template_filter("format_date")
def format_date(valeur):
    if valeur is None or valeur == "":
        return "Date inconnue"
    if isinstance(valeur, datetime):
        return valeur.strftime("%d/%m/%Y à %H:%M")
    return str(valeur)  # chaîne texte brute


# 8. Stopwords français de base
STOPWORDS_FR = {
    "le", "la", "les", "de", "du", "des", "un", "une", "en", "et", "est",
    "au", "aux", "ce", "se", "sa", "son", "ses", "sur", "par", "pour",
    "que", "qui", "dans", "avec", "plus", "pas", "il", "elle", "ils",
    "elles", "on", "nous", "vous", "je", "tu", "l", "d", "à", "a",
    "ou", "si", "ne", "y", "c", "n", "s", "j", "m", "qu",
    "tout", "mais", "sans", "deux", "comme", "faire", "moins", "après",
    "être", "face", "ans"
}

# 8. Namespaces XML pour les sitemaps
NAMESPACES = {
    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news":    "http://www.google.com/schemas/sitemap-news/0.9",
}

# 9. Instance globale du scheduler
scheduler = BackgroundScheduler(timezone="UTC")


# Conversion de date

def convertir_date(date_str):
    """
    Convertit une chaîne de date ISO du sitemap en objet datetime UTC.
    Essaie plusieurs formats courants.
    Retourne None si la conversion échoue, sans planter.
    """
    if not date_str:
        return None

    # Formats courants rencontrés dans les sitemaps
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",   # 2026-03-10T14:32:00+02:00
        "%Y-%m-%dT%H:%M:%SZ",    # 2026-03-10T14:32:00Z
        "%Y-%m-%dT%H:%M:%S",     # 2026-03-10T14:32:00
        "%Y-%m-%d",              # 2026-03-10
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            # Si pas de timezone, on suppose UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Convertit tout en UTC pour la cohérence
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue

    # Aucun format n'a fonctionné
    return None


# ── Fonctions métier ──────────────────────────────────────────

def lire_sitemap(url):
    """Télécharge et parse un sitemap. Retourne une liste de dictionnaires."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    resultats = []
    for url_tag in root.findall("sitemap:url", NAMESPACES):
        loc              = url_tag.findtext("sitemap:loc",                     default="", namespaces=NAMESPACES)
        title            = url_tag.findtext("news:news/news:title",            default="", namespaces=NAMESPACES)
        publication_date = url_tag.findtext("news:news/news:publication_date", default="", namespaces=NAMESPACES)
        resultats.append({"loc": loc, "title": title, "publication_date": publication_date})
    return resultats


def inserer_articles(liste, subscription_id, source_name):
    """
    Insère les articles dans MongoDB.
    publication_date est converti en datetime avant insertion.
    Retourne (nb_insérés, nb_doublons).
    """
    nb_inseres  = 0
    nb_doublons = 0
    for item in liste:
        try:
            articles.insert_one({
                "subscription_id":     subscription_id,
                "source_name":         source_name,
                "url":                 item["loc"],
                "title":               item["title"],
                # Conversion de la chaîne ISO en vrai datetime UTC
                "publication_date":    convertir_date(item["publication_date"]),
                "fetched_at":          datetime.now(timezone.utc),
                "consultations_count": 0,
            })
            nb_inseres += 1
        except DuplicateKeyError:
            nb_doublons += 1
    return nb_inseres, nb_doublons


def mettre_a_jour_un_abonnement(subscription_id_str):
    """Met à jour un seul abonnement. Appelé par chaque job APScheduler."""
    try:
        oid = ObjectId(subscription_id_str)
        sub = subscriptions.find_one({"_id": oid, "active": True})
        if sub is None:
            return
        liste = lire_sitemap(sub["sitemap_url"])
        inseres, doublons = inserer_articles(liste, sub["_id"], sub["source_name"])
        subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"last_fetch_at": datetime.now(timezone.utc)}}
        )
        print(f"[Scheduler] {sub['source_name']} : {inseres} insérés, {doublons} doublons.")
    except Exception as e:
        print(f"[Scheduler] Erreur pour {subscription_id_str} : {e}")


def mettre_a_jour_tous_les_abonnements():
    """Utilisée par le bouton manuel. Met à jour tous les abonnements actifs."""
    abonnements_actifs = list(subscriptions.find({"active": True}))
    total_inseres  = 0
    total_doublons = 0
    total_traites  = 0
    erreurs        = []

    for sub in abonnements_actifs:
        total_traites += 1
        try:
            liste = lire_sitemap(sub["sitemap_url"])
            inseres, doublons = inserer_articles(liste, sub["_id"], sub["source_name"])
            total_inseres  += inseres
            total_doublons += doublons
            subscriptions.update_one(
                {"_id": sub["_id"]},
                {"$set": {"last_fetch_at": datetime.now(timezone.utc)}}
            )
        except Exception as e:
            erreurs.append(f"{sub['source_name']} : {str(e)}")

    return {"traites": total_traites, "inseres": total_inseres,
            "doublons": total_doublons, "erreurs": erreurs}


# Gestion des jobs APScheduler

def synchroniser_jobs():
    """Synchronise les jobs APScheduler avec la collection subscriptions."""
    abonnements_actifs = list(subscriptions.find({"active": True}))
    ids_attendus = {f"sub_{str(sub['_id'])}" for sub in abonnements_actifs}

    for job in scheduler.get_jobs():
        if job.id.startswith("sub_") and job.id not in ids_attendus:
            scheduler.remove_job(job.id)
            print(f"[Scheduler] Job supprimé : {job.id}")

    for sub in abonnements_actifs:
        job_id     = f"sub_{str(sub['_id'])}"
        minutes    = sub.get("refresh_interval_minutes", 60)
        sub_id_str = str(sub["_id"])
        existing   = scheduler.get_job(job_id)

        if existing is None:
            scheduler.add_job(
                func=mettre_a_jour_un_abonnement,
                trigger="interval",
                minutes=minutes,
                id=job_id,
                args=[sub_id_str],
                replace_existing=True,
            )
            print(f"[Scheduler] Job créé : {sub['source_name']} toutes les {minutes} min.")
        else:
            intervalle_actuel = int(existing.trigger.interval.total_seconds() // 60)
            if intervalle_actuel != minutes:
                scheduler.reschedule_job(job_id, trigger="interval", minutes=minutes)
                print(f"[Scheduler] Job mis à jour : {sub['source_name']} → {minutes} min.")


def demarrer_scheduler():
    """Démarre le scheduler et enregistre l'arrêt propre via atexit."""
    synchroniser_jobs()
    scheduler.start()
    print("Scheduler démarré.")
    atexit.register(lambda: scheduler.shutdown(wait=False))


# Routes

@app.route("/")
def index():
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return render_template("home.html", python_version=python_version)


# Articles

@app.route("/articles")
def liste_articles():
    source  = request.args.get("source_name", "").strip()
    keyword = request.args.get("keyword", "").strip()
    date    = request.args.get("publication_date", "").strip()

    filtre = {}

    if source:
        filtre["source_name"] = source

    if keyword:
        filtre["title"] = {"$regex": keyword, "$options": "i"}

    if date:
        # Convertit la date saisie en plage : du début au fin du jour
        # Exemple : "2026-03-10" → entre 2026-03-10T00:00:00Z et 2026-03-10T23:59:59Z
        debut_journee = convertir_date(date)
        if debut_journee:
            fin_journee = debut_journee + timedelta(days=1) - timedelta(seconds=1)
            filtre["publication_date"] = {
                "$gte": debut_journee,
                "$lte": fin_journee,
            }

    resultats = articles.find(filtre).sort("publication_date", -1).limit(20)
    return render_template(
        "articles.html",
        articles=list(resultats),
        source=source, keyword=keyword, date=date
    )


@app.route("/article/<id>/open")
def ouvrir_article(id):
    try:
        oid = ObjectId(id)
    except InvalidId:
        abort(404)
    article = articles.find_one({"_id": oid})
    if article is None:
        abort(404)
    consultations.insert_one({"article_id": oid, "consulted_at": datetime.now(timezone.utc)})
    articles.update_one({"_id": oid}, {"$inc": {"consultations_count": 1}})
    return redirect(article["url"])


# Nuage de mots

def generer_svg(titres):
    texte = " ".join(titres).lower()
    mots  = re.findall(r"[a-zàâäéèêëîïôùûüç]{3,}", texte)
    mots_filtres = [m for m in mots if m not in STOPWORDS_FR]
    frequences   = Counter(mots_filtres).most_common(50)
    if not frequences:
        return None
    freq_max = frequences[0][1]
    freq_min = frequences[-1][1]
    def taille(freq):
        if freq_max == freq_min:
            return 32
        return int(14 + (freq - freq_min) / (freq_max - freq_min) * 46)
    couleurs = ["#58a6ff", "#3fb950", "#d29922", "#f78166", "#79b8ff", "#56d364", "#e3b341", "#ffa198"]
    LARGEUR, HAUTEUR, MARGE = 900, 520, 10
    random.seed(42)
    boites = []
    def chevauche(x, y, w, h):
        x1, y1, x2, y2 = x-w/2-6, y-h-6, x+w/2+6, y+6
        return any(x1 < bx2 and x2 > bx1 and y1 < by2 and y2 > by1 for bx1,by1,bx2,by2 in boites)
    def hors_cadre(x, y, w, h):
        return x-w/2 < MARGE or x+w/2 > LARGEUR-MARGE or y-h < MARGE or y > HAUTEUR-MARGE
    elements = []
    for mot, freq in frequences:
        px = taille(freq)
        w_mot, h_mot = len(mot)*px*0.6, px
        couleur = random.choice(couleurs)
        for _ in range(200):
            x = random.randint(int(w_mot/2)+MARGE, int(LARGEUR-w_mot/2)-MARGE)
            y = random.randint(h_mot+MARGE, HAUTEUR-MARGE)
            if not chevauche(x, y, w_mot, h_mot) and not hors_cadre(x, y, w_mot, h_mot):
                boites.append((x-w_mot/2, y-h_mot, x+w_mot/2, y))
                elements.append(f'<text x="{x}" y="{y}" font-size="{px}" fill="{couleur}" font-family="Arial, sans-serif" text-anchor="middle">{mot}</text>')
                break
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARGEUR}" height="{HAUTEUR}" style="background:#161b22;">'
            + "".join(elements) + "</svg>")


@app.route("/wordcloud")
def nuage_de_mots():
    titres = [a["title"] for a in articles.find({}, {"title": 1}) if a.get("title")]
    svg = generer_svg(titres) if titres else None
    return render_template("wordcloud.html", svg=svg)


# Abonnements

@app.route("/subscriptions")
def liste_subscriptions():
    liste = list(subscriptions.find().sort("source_name", 1))
    return render_template("subscriptions.html", subscriptions=liste, erreur=None, resume=None)


@app.route("/subscriptions/add", methods=["POST"])
def ajouter_subscription():
    source_name      = request.form.get("source_name", "").strip()
    sitemap_url      = request.form.get("sitemap_url", "").strip()
    refresh_interval = request.form.get("refresh_interval_minutes", "60").strip()

    if not source_name or not sitemap_url:
        liste = list(subscriptions.find().sort("source_name", 1))
        return render_template("subscriptions.html", subscriptions=liste,
                               erreur="Le nom de la source et l'URL du sitemap sont obligatoires.", resume=None)
    try:
        subscriptions.insert_one({
            "source_name":              source_name,
            "sitemap_url":              sitemap_url,
            "active":                   True,
            "refresh_interval_minutes": int(refresh_interval) if refresh_interval.isdigit() else 60,
            "last_fetch_at":            None,
        })
    except DuplicateKeyError:
        liste = list(subscriptions.find().sort("source_name", 1))
        return render_template("subscriptions.html", subscriptions=liste,
                               erreur=f"Cet abonnement existe déjà : {sitemap_url}", resume=None)
    synchroniser_jobs()
    return redirect("/subscriptions")


@app.route("/subscriptions/delete/<id>", methods=["POST"])
def supprimer_subscription(id):
    try:
        oid = ObjectId(id)
    except InvalidId:
        abort(404)
    subscriptions.delete_one({"_id": oid})
    synchroniser_jobs()
    return redirect("/subscriptions")


@app.route("/subscriptions/toggle/<id>", methods=["POST"])
def basculer_subscription(id):
    try:
        oid = ObjectId(id)
    except InvalidId:
        abort(404)
    sub = subscriptions.find_one({"_id": oid})
    if sub is None:
        abort(404)
    subscriptions.update_one({"_id": oid}, {"$set": {"active": not sub.get("active", True)}})
    synchroniser_jobs()
    return redirect("/subscriptions")


@app.route("/subscriptions/interval/<id>", methods=["POST"])
def modifier_intervalle(id):
    try:
        oid = ObjectId(id)
    except InvalidId:
        abort(404)
    nouvel_intervalle = request.form.get("refresh_interval_minutes", "").strip()
    if not nouvel_intervalle.isdigit() or int(nouvel_intervalle) < 1:
        liste = list(subscriptions.find().sort("source_name", 1))
        return render_template("subscriptions.html", subscriptions=liste,
                               erreur="L'intervalle doit être un entier positif (en minutes).", resume=None)
    subscriptions.update_one({"_id": oid}, {"$set": {"refresh_interval_minutes": int(nouvel_intervalle)}})
    synchroniser_jobs()
    return redirect("/subscriptions")


@app.route("/subscriptions/update", methods=["POST"])
def mettre_a_jour():
    resume = mettre_a_jour_tous_les_abonnements()
    liste  = list(subscriptions.find().sort("source_name", 1))
    return render_template("subscriptions.html", subscriptions=liste, erreur=None, resume=resume)


# Lancement

if __name__ == "__main__":
    demarrer_scheduler()
    app.run(debug=True, use_reloader=False)