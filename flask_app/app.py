import logging
import json
import requests
from flask import Flask, flash, redirect, render_template, request, session, url_for
from config import Config
from models import User, RecommendationHistory, db
from forms import LoginForm, RegistrationForm, RecommendForm
from services.recommender_client import RecommenderAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
recommender_client = RecommenderAPIClient(app.config["RECOMMENDER_API_URL"])


@app.context_processor
def inject_user():
    user = None
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
    return {"current_user": user}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        if User.query.filter_by(username=username).first():
            flash("Пользователь уже существует", "danger")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Регистрация успешна! Войдите в систему", "success")
            return redirect(url_for("login"))
    
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Добро пожаловать, {username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Неверное имя пользователя или пароль", "danger")
    
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("index"))


@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    if "user_id" not in session:
        flash("Войдите в систему", "warning")
        return redirect(url_for("login"))
    
    form = RecommendForm()
    recommendations = None
    
    if form.validate_on_submit():
        selected_genres = form.genres.data
        
        if selected_genres:
            recs = recommender_client.get_recommendations_by_genres(selected_genres, 10)
        else:
            recs = recommender_client.get_recommendations(session["user_id"], 10)
        
        if recs:
            recommendations = recs
            games_data = [{"id": r["game_id"], "name": r["name"]} for r in recs]
            history = RecommendationHistory(
                user_id=session["user_id"],
                game_ids=json.dumps(games_data)
            )
            db.session.add(history)
            db.session.commit()
            flash(f"Найдено {len(recs)} рекомендаций!", "success")
        else:
            flash("Сервис рекомендаций недоступен", "danger")
    
    return render_template("recommend.html", form=form, recommendations=recommendations)


@app.route("/search-by-text", methods=["POST", "GET"])
def search_by_text():
    if "user_id" not in session:
        flash("Войдите в систему", "warning")
        return redirect(url_for("login"))
    
    # Поддержка GET для пагинации
    if request.method == "GET":
        query = request.args.get("query", "")
        page = int(request.args.get("page", 1))
        per_page = 30
    else:
        query = request.form.get("query", "").strip()
        page = 1
        per_page = 30
        genres_filter = request.form.getlist("genres_filter")
        if genres_filter:
            query = f"{query} {' '.join(genres_filter)}"
    
    if not query:
        flash("Введите поисковый запрос", "warning")
        return redirect(url_for("recommend"))
    
    try:
        response = requests.post(
            f"{app.config['RECOMMENDER_API_URL']}/search-by-text",
            json={"query": query, "n_results": per_page, "page": page},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        recommendations = data.get("recommendations", [])
        total = data.get("total", 0)
        
        # Сохраняем в историю только при первом поиске (не при пагинации)
        if request.method == "POST":
            games_data = [{"id": r["game_id"], "name": r["name"]} for r in recommendations]
            history = RecommendationHistory(
                user_id=session["user_id"],
                game_ids=json.dumps(games_data[:30])
            )
            db.session.add(history)
            db.session.commit()
        
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        
        flash(f"Найдено {total} игр по запросу '{query}'", "success")
        return render_template("recommend.html", 
                             recommendations=recommendations, 
                             search_query=query,
                             page=page,
                             total=total,
                             start=start,
                             end=min(start + per_page, total),
                             total_pages=total_pages,
                             form=RecommendForm())
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        flash("Ошибка поиска", "danger")
        return redirect(url_for("recommend"))


@app.route("/history")
def history():
    if "user_id" not in session:
        flash("Войдите в систему", "warning")
        return redirect(url_for("login"))
    
    try:
        history_list = RecommendationHistory.query.filter_by(
            user_id=session["user_id"]
        ).order_by(RecommendationHistory.created_at.desc()).all()
        
        history_data = []
        for item in history_list:
            try:
                games_data = json.loads(item.game_ids) if item.game_ids else []
                if games_data and isinstance(games_data[0], int):
                    games_data = [{"id": gid, "name": f"Game_{gid}"} for gid in games_data]
            except:
                games_data = []
            
            history_data.append({
                'id': item.id,
                'games': games_data,
                'created_at': item.created_at
            })
        
        return render_template("history.html", history=history_data)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        flash("Ошибка загрузки истории", "danger")
        return render_template("history.html", history=[])


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)