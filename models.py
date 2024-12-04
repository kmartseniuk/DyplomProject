# models.py

from datetime import datetime
from extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 

    # Relationships
    resumes = db.relationship('Resume', back_populates='user', lazy=True)
    jobs = db.relationship('Job', back_populates='user', lazy=True)

class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(150),nullable=True)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    skills = db.Column(db.Text)
    knowledge = db.Column(db.Text)
    rating = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='resumes')
    ranking_results = db.relationship('RankingResult', back_populates='resume', lazy=True)

class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    skills = db.Column(db.Text)
    knowledge = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='jobs')
    ranking_results = db.relationship('RankingResult', back_populates='job', lazy=True)

class RankingResult(db.Model):
    __tablename__ = 'ranking_results'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    score_skills = db.Column(db.Float, nullable=False)
    score_knowledge = db.Column(db.Float, nullable=False)
    score_combined = db.Column(db.Float, nullable=False)
    matching_keywords = db.Column(db.Text)
    model_used = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    job = db.relationship('Job', back_populates='ranking_results')
    resume = db.relationship('Resume', back_populates='ranking_results')
