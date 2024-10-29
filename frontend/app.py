# frontend/app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests

app = Flask(__name__)
app.secret_key = "your_secret_key"

# URL API FastAPI
API_URL = "http://127.0.0.1:8006"


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = {
            "username": username,
            "password": password,
            "role": 0
        }

        response = requests.post(f"{API_URL}/users/users/", json=user_data)

        if response.status_code == 201:
            flash("Регистрация прошла успешно! Войдите в систему.", "success")
            return redirect(url_for("login"))
        else:
            flash("Ошибка регистрации. Попробуйте другое имя пользователя.", "error")

    return render_template("register.html")



@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Запрашиваем данные пользователя из FastAPI
        response = requests.get(f"{API_URL}/users/users/{username}")
        if response.status_code == 200:
            user_data = response.json()

            # Проверяем пароль (на основе простого сравнения, можно заменить на хэш)
            if user_data['password'] == password:
                session['username'] = username
                flash("Вы успешно вошли в систему!", "success")
                return redirect(url_for("index"))
            else:
                flash("Неверный пароль.", "error")
        else:
            flash("Пользователь не найден.", "error")

    return render_template("hello.html")


@app.route('/logout')
def logout():
    """Выход из системы."""
    session.pop('username', None)
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(debug=True)
