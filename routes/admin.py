from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import User, Resume, Job
from extensions import db
from werkzeug.security import generate_password_hash

admin = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(func):
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("У вас немає прав доступу до цієї сторінки.")
            return redirect(url_for("main.index"))
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


# Маршрут для керування користувачами
@admin.route("/users")
@admin_required
def manage_users():
    users = User.query.all()
    return render_template("admin/manage_users.html", users=users)


# Маршрут для створення нового користувача (адміністратора або звичайного)
@admin.route("/create_user", methods=["GET", "POST"])
@admin_required
def create_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        is_admin = "is_admin" in request.form

        # Перевірка чи існує користувач
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Користувач з таким ім'ям вже існує.")
            return redirect(url_for("admin.create_user"))

        # Створення нового користувача
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()

        flash("Новий користувач створений успішно.")
        return redirect(url_for("admin.manage_users"))
    return render_template("admin/create_user.html")


# Видалення користувача
@admin.route("/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Ви не можете видалити свій власний обліковий запис.")
        return redirect(url_for("admin.manage_users"))

    # Видаляємо пов'язані резюме та вакансії
    Resume.query.filter_by(user_id=user.id).delete()
    Job.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("Користувача видалено успішно.")
    return redirect(url_for("admin.manage_users"))


# Зміна паролю користувача
@admin.route("/reset_password/<int:user_id>", methods=["GET", "POST"])
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        new_password = request.form["new_password"]
        user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
        db.session.commit()
        flash("Пароль користувача успішно змінено.")
        return redirect(url_for("admin.manage_users"))
    return render_template("admin/reset_password.html", user=user)


# Перегляд резюме користувача
@admin.route("/user_resumes/<int:user_id>")
@admin_required
def user_resumes(user_id):
    user = User.query.get_or_404(user_id)
    resumes = Resume.query.filter_by(user_id=user.id).all()
    return render_template("admin/user_resumes.html", user=user, resumes=resumes)


# Перегляд вакансій користувача
@admin.route("/user_jobs/<int:user_id>")
@admin_required
def user_jobs(user_id):
    user = User.query.get_or_404(user_id)
    jobs = Job.query.filter_by(user_id=user.id).all()
    return render_template("admin/user_jobs.html", user=user, jobs=jobs)
