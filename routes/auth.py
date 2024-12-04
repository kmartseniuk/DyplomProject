from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User

auth = Blueprint("auth", __name__)

# Маршрут для регістрації
@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        is_admin = True
        # Перевірка чи існує користувач з таким username
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Користувач з таким ім'ям вже існує.")
            return redirect(url_for("auth.register"))

        # Створення нового користувача
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()

        flash("Реєстрація успішна. Тепер ви можете увійти.")
        return redirect(url_for("auth.login"))
    return render_template("register.html")


# Маршрут для вхожу
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Авторизація користувача
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("main.index"))
        else:
            flash("Невірне ім'я користувача або пароль.")
            return redirect(url_for("auth.login"))
    return render_template("login.html")


# Маршрут для виходу із системи
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Ви вийшли з системи.")
    return redirect(url_for("auth.login"))
