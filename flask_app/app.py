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

@app.template_filter('from_json')
def from_json_filter(json_str):
    """Фильтр для парсинга JSON в шаблонах"""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except:
        return []
    
@app.context_processor
def inject_user():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
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
        if User.query.filter_by(username=form.username.data).first():
            flash("Пользователь уже существует", "danger")
        else:
            user = User(username=form.username.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Регистрация успешна!", "success")
            return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            session["user_id"] = user.id
            flash(f"Добро пожаловать, {user.username}!", "success")
            return redirect(url_for("index"))
        flash("Неверные данные", "danger")
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
            # Рекомендации по выбранным жанрам
            recs = recommender_client.get_recommendations_by_genres(selected_genres, 10)
        else:
            # Персональные рекомендации (по умолчанию)
            recs = recommender_client.get_recommendations(session["user_id"], 10)
        
        if recs:
            recommendations = recs
            history = RecommendationHistory(
                user_id=session["user_id"],
                game_ids=json.dumps([r["game_id"] for r in recs])
            )
            db.session.add(history)
            db.session.commit()
            flash(f"Найдено {len(recs)} рекомендаций!", "success")
        else:
            flash("Сервис рекомендаций недоступен", "danger")
    
    return render_template("recommend.html", form=form, recommendations=recommendations)

@app.route("/history")
def history():
    if "user_id" not in session:
        flash("Пожалуйста, войдите в систему", "warning")
        return redirect(url_for("login"))
    
    try:
        # Используем правильный импорт модели
        from models import RecommendationHistory
        
        history_list = RecommendationHistory.query.filter_by(
            user_id=session["user_id"]
        ).order_by(RecommendationHistory.created_at.desc()).all()
        
        # Парсим данные
        history_data = []
        for item in history_list:
            try:
                game_ids = json.loads(item.game_ids) if item.game_ids else []
            except:
                game_ids = []
            
            history_data.append({
                'id': item.id,
                'game_ids': game_ids,
                'created_at': item.created_at
            })
        
        return render_template("history.html", history=history_data)
    except Exception as e:
        logger.error(f"Ошибка в history: {e}")
        flash("Ошибка загрузки истории", "danger")
        return render_template("history.html", history=[])

@app.route("/search-by-text", methods=["POST"])
def search_by_text():
    """Поиск игр по текстовому описанию"""
    if "user_id" not in session:
        flash("Пожалуйста, войдите в систему", "warning")
        return redirect(url_for("login"))
    
    query = request.form.get("query", "").strip()
    genres_filter = request.form.getlist("genres_filter")
    
    if not query:
        flash("Введите поисковый запрос", "warning")
        return redirect(url_for("recommend"))
    
    # Если есть фильтр по жанрам, добавляем его к запросу
    if genres_filter:
        query = f"{query} {' '.join(genres_filter)}"
        flash(f"Поиск: {query}", "info")
    
    try:
        response = requests.post(
            f"{app.config['RECOMMENDER_API_URL']}/search-by-text",
            json={"query": query, "n_results": 30},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        recommendations = data.get("recommendations", [])
        
        # Сохраняем в историю
        game_ids = [r["game_id"] for r in recommendations]
        history = RecommendationHistory(
            user_id=session["user_id"],
            game_ids=json.dumps(game_ids)
        )
        db.session.add(history)
        db.session.commit()
        
        flash(f"Найдено {len(recommendations)} игр по запросу '{query}'", "success")
        return render_template("recommend.html", 
                             recommendations=recommendations, 
                             search_query=query,
                             form=RecommendForm())
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        flash(f"Ошибка: {str(e)}", "danger")
        return redirect(url_for("recommend"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)