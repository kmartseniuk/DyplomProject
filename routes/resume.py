from flask import (
    Blueprint,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    session,
    send_file,
    current_app,
    abort,
)
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename
import os
import threading
import uuid
from extensions import db
from models import Resume, RankingResult
from utils import parse_resume

resume = Blueprint("resume", __name__)

upload_tasks = {}

# Проес Завантаження резюме
@resume.route("/upload_resume", methods=["GET", "POST"])
@login_required
def upload_resume():
    user_id = current_user.id
    if request.method == "POST":
        files = request.files.getlist("resumes")
        total_files = len(files)

        if not files or files[0].filename == "":
            flash("Будь ласка, виберіть файли.")
            return jsonify({"status": "error", "message": "No files selected"}), 400

        task_id = str(uuid.uuid4())

        upload_tasks[task_id] = {
            "current": 0,
            "total": total_files,
            "progress": 0,
            "status": "in_progress",
            "user_id": user_id,
        }

        session["upload_task_id"] = task_id

        app = current_app._get_current_object()

        saved_file_paths = []
        for file in files:
            if file and file.filename.endswith(".pdf"):
                original_filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                user_folder = os.path.join("resumes", str(user_id))
                os.makedirs(user_folder, exist_ok=True)
                file_path = os.path.join(user_folder, unique_filename)
                file.save(file_path)
                saved_file_paths.append((file_path, unique_filename))

        def process_files(app, user_id, saved_files, total_files, task_id):
            with app.app_context():
                # Iніцілізаця моделей
                models = current_app.config["MODELS"]
                token_skill_classifier = models["token_skill_classifier"]
                token_knowledge_classifier = models["token_knowledge_classifier"]
                max_number = (
                    db.session.query(func.max(Resume.number))
                    .filter_by(user_id=user_id)
                    .scalar()
                    or 0
                )
                idx = 0
                for file_path, unique_filename in saved_files:
                    # Парсинг резюме
                    resume_data = parse_resume(
                        file_path, token_skill_classifier, token_knowledge_classifier
                    )
                    resume_skills = resume_data["skills"]
                    resume_knowledge = resume_data["knowledge"]
                    resume_name = resume_data["name"] or "Невідомо"
                    resume_email = resume_data["email"] or ""
                    resume_phone = resume_data["phone"] or ""

                    # Перевірка на дублікати
                    existing_resume = Resume.query.filter_by(
                        name=resume_name, email=resume_email, user_id=user_id
                    ).first()
                    if existing_resume:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        idx += 1
                        upload_task = upload_tasks.get(task_id)
                        if upload_task:
                            upload_task["current"] = idx
                            upload_task["progress"] = int((idx / total_files) * 100)
                        continue

                    max_number += 1

                    new_resume = Resume(
                        filename=unique_filename,
                        name=resume_name,
                        email=resume_email,
                        phone=resume_phone,
                        skills=", ".join(resume_skills),
                        knowledge=", ".join(resume_knowledge),
                        user_id=user_id,
                        number=max_number,
                    )
                    db.session.add(new_resume)
                    db.session.commit()
                    idx += 1
                    upload_task = upload_tasks.get(task_id)
                    if upload_task:
                        upload_task["current"] = idx
                        upload_task["progress"] = int((idx / total_files) * 100)
                upload_task = upload_tasks.get(task_id)
                if upload_task:
                    upload_task["status"] = "complete"
                    upload_task["progress"] = 100

        # Початок фонового процесу завантаження резюме
        threading.Thread(
            target=process_files,
            args=(app, user_id, saved_file_paths, total_files, task_id),
        ).start()
        return jsonify({"status": "success", "task_id": task_id})

    return redirect(url_for("main.dashboard"))


# Маршрут для перевірки прогресу завантаження
@resume.route("/upload_status/<task_id>")
@login_required
def upload_status(task_id):
    task = upload_tasks.get(task_id)
    if task and task["user_id"] == current_user.id:
        return jsonify(
            {
                "status": task["status"],
                "current": task["current"],
                "total": task["total"],
                "progress": task["progress"],
            }
        )
    else:
        return jsonify({"status": "not_found"}), 404


# Маршрут для перегляду резюме
@resume.route("/resume_pdf/<int:resume_id>")
@login_required
def resume_pdf(resume_id):
    resume_obj = db.session.get(Resume, resume_id)
    if resume_obj is None:
        abort(404)
    if resume_obj.user_id != current_user.id:
        flash("Ви не маєте права переглядати це резюме.")
        return redirect(url_for("main.dashboard"))
    user_folder = os.path.join("resumes", str(current_user.id))
    file_path = os.path.join(user_folder, resume_obj.filename)
    if not os.path.exists(file_path):
        flash("Файл резюме не знайдено.")
        return redirect(url_for("main.dashboard"))
    return send_file(file_path)


# Маршрут для отримання даних з резюме
@resume.route("/get_resume_info/<int:resume_id>")
@login_required
def get_resume_info(resume_id):
    resume_obj = db.session.get(Resume, resume_id)
    if resume_obj is None:
        abort(404)
    if resume_obj.user_id != current_user.id:
        return jsonify({"status": "error"})
    return jsonify(
        {
            "name": resume_obj.name,
            "email": resume_obj.email,
            "phone": resume_obj.phone,
            "skills": resume_obj.skills,
            "knowledge": resume_obj.knowledge,
            "rating": resume_obj.rating,
            "feedback": resume_obj.feedback,
            "is_favorite": resume_obj.is_favorite,
        }
    )


# Маршрут для онолвення даних резюме
@resume.route("/update_resume/<int:resume_id>", methods=["POST"])
@login_required
def update_resume(resume_id):
    resume_obj = db.session.get(Resume, resume_id)
    if resume_obj is None:
        abort(404)
    if resume_obj.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.form
    resume_obj.name = data.get("name", resume_obj.name)
    resume_obj.email = data.get("email", resume_obj.email)
    resume_obj.phone = data.get("phone", resume_obj.phone)

    skills = data.get("skills", resume_obj.skills)
    skills_list = [skill.strip() for skill in skills.split(",")]
    resume_obj.skills = ", ".join(skills_list)

    knowledge = data.get("knowledge", resume_obj.knowledge)
    knowledge_list = [item.strip() for item in knowledge.split(",")]
    resume_obj.knowledge = ", ".join(knowledge_list)

    resume_obj.rating = data.get("rating", resume_obj.rating)
    resume_obj.feedback = data.get("feedback", resume_obj.feedback)

    db.session.commit()
    return jsonify({"status": "success"})


# Маршрут для видалення резюме
@resume.route("/delete_resume/<int:resume_id>", methods=["POST"])
@login_required
def delete_resume(resume_id):
    resume_obj = db.session.get(Resume, resume_id)
    if resume_obj is None:
        abort(404)
    if resume_obj.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Немає доступу"})
    RankingResult.query.filter_by(resume_id=resume_id).delete()
    db.session.commit()
    user_folder = os.path.join("resumes", str(current_user.id))
    file_path = os.path.join(user_folder, resume_obj.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(resume_obj)
    db.session.commit()
    resumes = (
        Resume.query.filter_by(user_id=current_user.id).order_by(Resume.number).all()
    )
    for idx, res in enumerate(resumes, start=1):
        res.number = idx
    db.session.commit()
    return jsonify({"status": "success"})


# Маршрут для додавання резюме в улюблене
@resume.route("/toggle_favorite_resume", methods=["POST"])
@login_required
def toggle_favorite_resume():
    resume_id = request.form.get("resume_id")
    resume_obj = db.session.get(Resume, resume_id)
    if resume_obj is None:
        abort(404)
    if resume_obj.user_id != current_user.id:
        return jsonify({"status": "error"})
    resume_obj.is_favorite = not resume_obj.is_favorite
    db.session.commit()
    return jsonify({"status": "success", "is_favorite": resume_obj.is_favorite})


# Автопошук по навичкам
@resume.route("/autocomplete_skills")
@login_required
def autocomplete_skills():
    term = request.args.get("term")
    skills = (
        db.session.query(Resume.skills)
        .filter(Resume.user_id == current_user.id, Resume.skills.ilike(f"%{term}%"))
        .all()
    )
    skills_list = set()
    for skill_str in skills:
        skills_list.update(skill_str[0].split(", "))
    filtered_skills = [skill for skill in skills_list if term.lower() in skill.lower()]
    return jsonify(filtered_skills[:5])


@resume.route("/autocomplete_knowledge")
@login_required
def autocomplete_knowledge():
    term = request.args.get("term")
    knowledge_entries = (
        db.session.query(Resume.knowledge)
        .filter(Resume.user_id == current_user.id, Resume.knowledge.ilike(f"%{term}%"))
        .all()
    )
    knowledge_list = set()
    for knowledge_str in knowledge_entries:
        knowledge_list.update(knowledge_str[0].split(", "))
    filtered_knowledge = [
        knowledge for knowledge in knowledge_list if term.lower() in knowledge.lower()
    ]
    return jsonify(filtered_knowledge[:5])


@resume.route("/get_upload_task_id")
@login_required
def get_upload_task_id():
    task_id = session.get("upload_task_id")
    return jsonify({"task_id": task_id})


@resume.route("/clear_upload_task_id", methods=["POST"])
@login_required
def clear_upload_task_id():
    session.pop("upload_task_id", None)
    return jsonify({"status": "success"})
