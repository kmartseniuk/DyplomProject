from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
)
from flask_login import login_required, current_user
from models import Job, Resume, RankingResult
from extensions import db
import threading
import uuid
from rank_bm25 import BM25Okapi

from utils import (
    extract_skills_and_knowledge,
    calculate_similarity_sbert,
    calculate_similarity_tfidf,
    calculate_similarity_glove,
    calculate_similarity_bm25,
)

job = Blueprint("job", __name__)


ranking_tasks = {}

# Маршрут для додавання нової вакансії
@job.route("/add_job_ajax", methods=["POST"])
@login_required
def add_job_ajax():
    title = request.form.get("title")
    description = request.form.get("description")
    # Завантаження моделей
    models = current_app.config["MODELS"]
    token_skill_classifier = models["token_skill_classifier"]
    token_knowledge_classifier = models["token_knowledge_classifier"]
    # Витягання навичок та знань
    job_skills, job_knowledge = extract_skills_and_knowledge(
        description, token_skill_classifier, token_knowledge_classifier
    )

    last_job = (
        Job.query.filter_by(user_id=current_user.id).order_by(Job.number.desc()).first()
    )
    number = last_job.number + 1 if last_job else 1

    new_job = Job(
        user_id=current_user.id,
        title=title,
        description=description,
        skills=", ".join(job_skills),
        knowledge=", ".join(job_knowledge),
        number=number,
    )
    db.session.add(new_job)
    db.session.commit()
    return jsonify({"status": "success"})


# Маршрут для отримання даних про вакансію
@job.route("/get_job_info/<int:job_id>", methods=["GET"])
@login_required
def get_job_info(job_id):
    job_obj = db.session.get(Job, job_id)
    if job_obj is None:
        abort(404)
    if job_obj.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    return jsonify(
        {
            "title": job_obj.title,
            "description": job_obj.description,
            "skills": job_obj.skills,
            "knowledge": job_obj.knowledge,
        }
    )


# Маршрут для оновлення вакансії
@job.route("/update_job/<int:job_id>", methods=["POST"])
@login_required
def update_job(job_id):
    job_obj = db.session.get(Job, job_id)
    if job_obj is None:
        abort(404)
    if job_obj.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.form
    job_obj.title = data.get("title", job_obj.title)
    job_obj.description = data.get("description", job_obj.description)

    skills = data.get("skills", job_obj.skills)
    skills_list = [skill.strip() for skill in skills.split(",")]
    job_obj.skills = ", ".join(skills_list)

    knowledge = data.get("knowledge", job_obj.knowledge)
    knowledge_list = [item.strip() for item in knowledge.split(",")]
    job_obj.knowledge = ", ".join(knowledge_list)

    db.session.commit()
    return jsonify({"status": "success"})


# Маршрут для видалення вакансії
@job.route("/delete_job/<int:job_id>", methods=["POST"])
@login_required
def delete_job(job_id):
    job_obj = db.session.get(Job, job_id)
    if job_obj is None:
        abort(404)
    if job_obj.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    RankingResult.query.filter_by(job_id=job_id).delete()
    db.session.commit()
    db.session.delete(job_obj)
    db.session.commit()
    return jsonify({"status": "success"})


# Маршрут для автопошуку навичок
@job.route("/autocomplete_job_skills")
@login_required
def autocomplete_job_skills():
    term = request.args.get("term")
    jobs = Job.query.filter(
        Job.user_id == current_user.id, Job.skills.ilike(f"%{term}%")
    ).all()
    skills_set = set()
    for job_item in jobs:
        skills_set.update(job_item.skills.split(", "))
    filtered_skills = [skill for skill in skills_set if term.lower() in skill.lower()]
    return jsonify(filtered_skills[:5])


# Маршрут для автопошуку знань
@job.route("/autocomplete_job_knowledge")
@login_required
def autocomplete_job_knowledge():
    term = request.args.get("term")
    jobs = Job.query.filter(
        Job.user_id == current_user.id, Job.knowledge.ilike(f"%{term}%")
    ).all()
    knowledge_set = set()
    for job_item in jobs:
        knowledge_set.update(job_item.knowledge.split(", "))
    filtered_knowledge = [
        item for item in knowledge_set if term.lower() in item.lower()
    ]
    return jsonify(filtered_knowledge[:5])


# Маршрут для переходу на сторінку ранжування
@job.route("/rank_resumes/<int:job_id>", methods=["GET"])
@login_required
def rank_resumes(job_id):
    job_obj = db.session.get(Job, job_id)
    if job_obj is None:
        abort(404)
    if job_obj.user_id != current_user.id:
        flash("У вас немає доступу до цієї вакансії.")
        return redirect(url_for("main.dashboard"))

    ranking_results = RankingResult.query.filter_by(job_id=job_id).all()

    if ranking_results:
        resume_scores = {}
        for ranking in ranking_results:
            resume_id = ranking.resume_id
            model_used = ranking.model_used
            if resume_id not in resume_scores:
                resume_scores[resume_id] = {
                    "resume": ranking.resume,
                    "scores_skills": {},
                    "scores_knowledge": {},
                    "scores_combined": {},
                    "matching_keywords_set": set(),
                    "rating": ranking.resume.rating,
                    "is_favorite": ranking.resume.is_favorite,
                    "has_phone": bool(ranking.resume.phone),
                    "has_email": bool(ranking.resume.email),
                }
            resume_scores[resume_id]["scores_skills"][model_used] = ranking.score_skills
            resume_scores[resume_id]["scores_knowledge"][
                model_used
            ] = ranking.score_knowledge
            resume_scores[resume_id]["scores_combined"][
                model_used
            ] = ranking.score_combined
            matching_keywords = (
                set(ranking.matching_keywords.split(", "))
                if ranking.matching_keywords
                else set()
            )
            resume_scores[resume_id]["matching_keywords_set"].update(matching_keywords)

        combined_results = []
        for data in resume_scores.values():
            avg_score_skills = (
                sum(data["scores_skills"].values()) / len(data["scores_skills"])
                if data["scores_skills"]
                else 0
            )
            avg_score_knowledge = (
                sum(data["scores_knowledge"].values()) / len(data["scores_knowledge"])
                if data["scores_knowledge"]
                else 0
            )
            avg_score_combined = (
                sum(data["scores_combined"].values()) / len(data["scores_combined"])
                if data["scores_combined"]
                else 0
            )
            matching_keywords = ", ".join(sorted(data["matching_keywords_set"]))
            scores = {
                model: round(score * 100, 2)
                for model, score in data["scores_combined"].items()
            }
            result = {
                "resume": data["resume"],
                "score_skills": round(avg_score_skills * 100, 2)
                if avg_score_skills
                else None,
                "score_knowledge": round(avg_score_knowledge * 100, 2)
                if avg_score_knowledge
                else None,
                "score_combined": round(avg_score_combined * 100, 2)
                if avg_score_combined
                else None,
                "matching_keywords": matching_keywords,
                "scores": scores,
                "rating": data["rating"],
                "is_favorite": data["is_favorite"],
                "has_phone": data["has_phone"],
                "has_email": data["has_email"],
            }
            combined_results.append(result)
        combined_results.sort(
            key=lambda x: x["score_combined"] if x["score_combined"] is not None else 0,
            reverse=True,
        )
    else:
        combined_results = []

    return render_template(
        "rank_resumes.html", job=job_obj, combined_results=combined_results
    )


# Маршрут для старту процесу ранжування
@job.route("/process_ranking/<int:job_id>", methods=["POST"])
@login_required
def process_ranking(job_id):
    job_obj = db.session.get(Job, job_id)
    if job_obj is None:
        abort(404)
    if job_obj.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json()
    selected_model = data.get("model", "all")

    task_id = str(uuid.uuid4())

    ranking_tasks[task_id] = {
        "current": 0,
        "total": 0,
        "progress": 0,
        "status": "in_progress",
    }

    app = current_app._get_current_object()

    # Фоновий процес для ранжування резюме
    threading.Thread(
        target=rank_resumes_background, args=(app, job_obj.id, task_id, selected_model)
    ).start()

    return jsonify({"status": "success", "task_id": task_id})


def rank_resumes_background(app, job_id, task_id, selected_model):
    with app.app_context():
        job_obj = db.session.get(Job, job_id)
        models = current_app.config["MODELS"]
        sbert_model = models["sbert_model"]
        glove_model = models["glove_model"]
        tfidf_vectorizer = models["tfidf_vectorizer"]

        resumes = Resume.query.filter_by(user_id=job_obj.user_id).all()
        total_resumes = len(resumes)
        ranking_tasks[task_id]["total"] = total_resumes

        job_skills = set(job_obj.skills.split(", ")) if job_obj.skills else set()
        job_knowledge = (
            set(job_obj.knowledge.split(", ")) if job_obj.knowledge else set()
        )
        job_attributes = job_skills.union(job_knowledge)

        model_list = (
            ["sbert", "tfidf", "glove", "bm25"]
            if selected_model == "all"
            else [selected_model]
        )

        for model_name in model_list:
            idx = 0
            RankingResult.query.filter_by(job_id=job_id, model_used=model_name).delete()
            db.session.commit()

            if model_name == "bm25":
                corpus = []
                for resume in resumes:
                    resume_attributes = (
                        set(resume.skills.split(", ")) if resume.skills else set()
                    )
                    resume_attributes.update(
                        set(resume.knowledge.split(", ")) if resume.knowledge else set()
                    )
                    corpus.append(" ".join(resume_attributes))
                bm25_model = BM25Okapi([doc.split() for doc in corpus])

            for resume in resumes:
                idx += 1
                resume_skills = (
                    set(resume.skills.split(", ")) if resume.skills else set()
                )
                resume_knowledge = (
                    set(resume.knowledge.split(", ")) if resume.knowledge else set()
                )
                resume_attributes = resume_skills.union(resume_knowledge)

                # Обчислення подібності в моделі
                skill_similarity = knowledge_similarity = combined_similarity = 0.0

                if model_name == "sbert":
                    skill_similarity = calculate_similarity_sbert(
                        resume_skills, job_skills, sbert_model
                    )
                    knowledge_similarity = calculate_similarity_sbert(
                        resume_knowledge, job_knowledge, sbert_model
                    )
                    combined_similarity = calculate_similarity_sbert(
                        resume_attributes, job_attributes, sbert_model
                    )
                elif model_name == "tfidf":
                    skill_similarity = calculate_similarity_tfidf(
                        resume_skills, job_skills
                    )
                    knowledge_similarity = calculate_similarity_tfidf(
                        resume_knowledge, job_knowledge
                    )
                    combined_similarity = calculate_similarity_tfidf(
                        resume_attributes, job_attributes
                    )

                elif model_name == "glove":
                    skill_similarity = calculate_similarity_glove(
                        resume_skills, job_skills, tfidf_vectorizer, glove_model
                    )
                    knowledge_similarity = calculate_similarity_glove(
                        resume_knowledge, job_knowledge, tfidf_vectorizer, glove_model
                    )
                    combined_similarity = calculate_similarity_glove(
                        resume_attributes, job_attributes, tfidf_vectorizer, glove_model
                    )
                elif model_name == "bm25":
                    query_skills = list(job_skills)
                    query_knowledge = list(job_knowledge)
                    query_combined = list(job_attributes)

                    if query_skills:
                        scores_skills = bm25_model.get_scores(query_skills)
                        max_score_skills = max(scores_skills)
                        if max_score_skills != 0:
                            skill_similarity = scores_skills[idx - 1] / max_score_skills
                        else:
                            skill_similarity = 0.0

                    if query_knowledge:
                        scores_knowledge = bm25_model.get_scores(query_knowledge)
                        max_score_knowledge = max(scores_knowledge)
                        if max_score_knowledge != 0:
                            knowledge_similarity = (
                                scores_knowledge[idx - 1] / max_score_knowledge
                            )
                        else:
                            knowledge_similarity = 0.0

                    if query_combined:
                        scores_combined = bm25_model.get_scores(query_combined)
                        max_score_combined = max(scores_combined)
                        if max_score_combined != 0:
                            combined_similarity = (
                                scores_combined[idx - 1] / max_score_combined
                            )
                        else:
                            combined_similarity = 0.0

                matching_keywords_set = job_attributes & resume_attributes
                matching_keywords = ", ".join(sorted(matching_keywords_set))

                ranking_result = RankingResult(
                    job_id=job_id,
                    resume_id=resume.id,
                    score_skills=skill_similarity,
                    score_knowledge=knowledge_similarity,
                    score_combined=combined_similarity,
                    model_used=model_name,
                    matching_keywords=matching_keywords,
                )
                db.session.add(ranking_result)
                db.session.commit()

                progress = int((idx / total_resumes) * 100)
                ranking_tasks[task_id]["current"] = idx
                ranking_tasks[task_id]["progress"] = progress

        ranking_tasks[task_id]["status"] = "complete"


# Маршрут для перевірки статусу ранжування
@job.route("/ranking_status/<task_id>")
@login_required
def ranking_status(task_id):
    task = ranking_tasks.get(task_id)
    if task:
        return jsonify(task)
    else:
        return jsonify({"status": "not_found"}), 404


# Маршрут для відображення результату ранжування
@job.route("/ranking_results/<int:job_id>", methods=["GET"])
@login_required
def ranking_results(job_id):
    job_obj = db.session.get(Job, job_id)
    if job_obj is None:
        abort(404)
    if job_obj.user_id != current_user.id:
        flash("У вас немає доступу до цієї вакансії.")
        return redirect(url_for("main.dashboard"))

    ranking_results = RankingResult.query.filter_by(job_id=job_id).all()

    if ranking_results:
        resume_scores = {}
        for ranking in ranking_results:
            resume_id = ranking.resume_id
            model_used = ranking.model_used
            if resume_id not in resume_scores:
                resume_scores[resume_id] = {
                    "resume": ranking.resume,
                    "scores_skills": {},
                    "scores_knowledge": {},
                    "scores_combined": {},
                    "matching_keywords_set": set(),
                    "rating": ranking.resume.rating,
                    "is_favorite": ranking.resume.is_favorite,
                    "has_phone": bool(ranking.resume.phone),
                    "has_email": bool(ranking.resume.email),
                }
            resume_scores[resume_id]["scores_skills"][model_used] = ranking.score_skills
            resume_scores[resume_id]["scores_knowledge"][
                model_used
            ] = ranking.score_knowledge
            resume_scores[resume_id]["scores_combined"][
                model_used
            ] = ranking.score_combined
            matching_keywords = (
                set(ranking.matching_keywords.split(", "))
                if ranking.matching_keywords
                else set()
            )
            resume_scores[resume_id]["matching_keywords_set"].update(matching_keywords)

        combined_results = []
        for data in resume_scores.values():
            avg_score_skills = (
                sum(data["scores_skills"].values()) / len(data["scores_skills"])
                if data["scores_skills"]
                else 0
            )
            avg_score_knowledge = (
                sum(data["scores_knowledge"].values()) / len(data["scores_knowledge"])
                if data["scores_knowledge"]
                else 0
            )
            avg_score_combined = (
                sum(data["scores_combined"].values()) / len(data["scores_combined"])
                if data["scores_combined"]
                else 0
            )
            matching_keywords = ", ".join(sorted(data["matching_keywords_set"]))
            scores = {
                model: round(score * 100, 2)
                for model, score in data["scores_combined"].items()
            }
            result = {
                "resume": data["resume"],
                "score_skills": round(avg_score_skills * 100, 2)
                if avg_score_skills
                else None,
                "score_knowledge": round(avg_score_knowledge * 100, 2)
                if avg_score_knowledge
                else None,
                "score_combined": round(avg_score_combined * 100, 2)
                if avg_score_combined
                else None,
                "matching_keywords": matching_keywords,
                "scores": scores,
                "rating": data["rating"],
                "is_favorite": data["is_favorite"],
                "has_phone": data["has_phone"],
                "has_email": data["has_email"],
            }
            combined_results.append(result)
        combined_results.sort(
            key=lambda x: x["score_combined"] if x["score_combined"] is not None else 0,
            reverse=True,
        )
    else:
        combined_results = []

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "ranking_results_content.html",
            job=job_obj,
            combined_results=combined_results,
        )
    else:
        return render_template(
            "rank_resumes.html", job=job_obj, combined_results=combined_results
        )
