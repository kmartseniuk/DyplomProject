# routes/main.py

from flask import Blueprint, render_template, flash, request
from flask_login import login_required, current_user
from sqlalchemy import desc
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import Resume, Job

main = Blueprint("main", __name__)

# Домашня сторінка
@main.route("/")
@login_required
def index():
    return render_template("index.html")


# Налаштування
@main.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        # Зміна паролю
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        if check_password_hash(current_user.password, current_password):
            current_user.password = generate_password_hash(
                new_password, method="pbkdf2:sha256"
            )
            db.session.commit()
            flash("Пароль успішно змінено.")
        else:
            flash("Невірний поточний пароль.")
    return render_template("settings.html")


# Панель управління
@main.route("/dashboard", methods=["GET"])
@login_required
def dashboard():

    name_query = request.args.get("name_search", "")
    skill_query = request.args.get("skill_search", "")
    knowledge_query = request.args.get("knowledge_search", "")
    has_phone = request.args.get("has_phone")
    has_email = request.args.get("has_email")
    has_rating = request.args.get("has_rating")

    resumes = Resume.query.filter_by(user_id=current_user.id)
    if name_query:
        resumes = resumes.filter(Resume.name.contains(name_query))
    if skill_query:
        resumes = resumes.filter(Resume.skills.contains(skill_query))
    if knowledge_query:
        resumes = resumes.filter(Resume.knowledge.contains(knowledge_query))
    if has_phone:
        resumes = resumes.filter(Resume.phone.isnot(None), Resume.phone != "")
    if has_email:
        resumes = resumes.filter(Resume.email.isnot(None), Resume.email != "")
    if has_rating:
        resumes = resumes.filter(Resume.rating.isnot(None))

    resumes = resumes.order_by(
        desc((Resume.is_favorite.is_(True) & Resume.rating.isnot(None))),
        desc(Resume.is_favorite),
        Resume.rating.desc().nullslast(),
        Resume.number.desc(),
    )

    # Пагінація для списку резюме
    resume_page = request.args.get("resume_page", 1, type=int)
    resume_per_page = int(request.args.get("resume_per_page", 10))
    resumes_paginated = resumes.paginate(
        page=resume_page, per_page=resume_per_page, error_out=False
    )

    job_name_query = request.args.get("job_name_search", "")
    job_skill_query = request.args.get("job_skill_search", "")
    job_knowledge_query = request.args.get("job_knowledge_search", "")

    # Фільтрація резюме
    if knowledge_query:
        resumes = resumes.filter(Resume.knowledge.contains(knowledge_query))

    jobs = Job.query.filter_by(user_id=current_user.id)
    if job_name_query:
        jobs = jobs.filter(Job.title.contains(job_name_query))
    if job_skill_query:
        jobs = jobs.filter(Job.skills.contains(job_skill_query))
    if job_knowledge_query:
        jobs = jobs.filter(Job.knowledge.contains(job_knowledge_query))

    jobs = jobs.order_by(Job.number.desc())

    # Пагіная для списку вакансій
    job_page = request.args.get("job_page", 1, type=int)
    job_per_page = int(request.args.get("job_per_page", 5))
    jobs_paginated = jobs.paginate(
        page=job_page, per_page=job_per_page, error_out=False
    )

    return render_template(
        "dashboard.html",
        resumes_paginated=resumes_paginated,
        jobs_paginated=jobs_paginated,
        resume_per_page=resume_per_page,
        job_per_page=job_per_page,
    )
