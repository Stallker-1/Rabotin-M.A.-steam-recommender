from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    predictions = db.relationship("RecommendationHistory", backref="user", lazy=True)
    
    def set_password(self, password: str) -> None:
        self.hashed_password = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)

class RecommendationHistory(db.Model):
    __tablename__ = "recommendations"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game_ids = db.Column(db.Text, nullable=False)  # JSON список
    created_at = db.Column(db.DateTime, default=datetime.utcnow)