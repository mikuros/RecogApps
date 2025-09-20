from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Watermark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_name_db = db.Column(db.String(64), nullable=False)
    secret_key_db = db.Column(db.String(64), nullable=False)
    created_at_db = db.Column(db.DateTime, default=db.func.now())
