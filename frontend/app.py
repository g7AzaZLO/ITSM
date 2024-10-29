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
        print(f"API response status: {response.status_code}")  # Проверяем статус ответа
        if response.status_code == 200:
            user_data = response.json()
            print(f"User data retrieved: {user_data}")  # Проверяем, что данные получены

            # Проверяем пароль
            if user_data['password'] == password:
                session['username'] = username
                session['role'] = user_data.get('role')  # Сохраняем роль пользователя в сессии
                print(f"User logged in: {session['username']}, role: {session['role']}")

                # Проверяем уровень доступа
                if session['role'] == 0:
                    print("Redirecting to order_services")
                    return redirect(url_for("order_services"))
                elif session['role'] in [1, 2, 3]:
                    print("Redirecting to manage_services")
                    return redirect(url_for("manage_services"))

                return redirect(url_for("index"))  # Перенаправление на домашнюю страницу
            else:
                flash("Неверный пароль.", "error")
        else:
            flash("Пользователь не найден.", "error")

    return render_template("login.html")


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    """Страница входа в систему."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Запрашиваем данные пользователя из FastAPI
        response = requests.get(f"{API_URL}/users/{username}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"User data retrieved: {user_data}")  # Для отладки

            # Проверяем пароль
            if user_data['password'] == password:
                # Сохраняем данные пользователя в сессии
                session['username'] = username
                session['role'] = user_data.get('role')
                flash("Вы успешно вошли в систему!", "success")

                # Проверяем уровень доступа
                if session['role'] == 0:
                    return redirect(url_for("order_services"))
                elif session['role'] in [1, 2, 3]:
                    return redirect(url_for("manage_services"))

                return redirect(url_for("index"))
            else:
                flash("Неверный пароль.", "error")
        else:
            flash("Пользователь не найден.", "error")

    return render_template("login.html")



@app.route('/order_services', methods=['GET', 'POST'])
def order_services():
    """Страница для заказа нескольких услуг одновременно."""
    if 'username' not in session or session.get('role') != 0:
        flash("Доступ запрещен.", "error")
        return redirect(url_for("login"))

    # Получаем список услуг из FastAPI
    response = requests.get(f"{API_URL}/catalog/services/")
    services = response.json() if response.status_code == 200 else []

    confirmation_message = ""

    if request.method == 'POST':
        # Получаем список выбранных услуг и их количество
        selected_services = request.form.getlist("service_ids")
        items = []
        total_price = 0  # Инициализируем общую стоимость

        for service_id in selected_services:
            quantity = int(request.form.get(f"quantities_{service_id}", 1))
            # Запрос на получение данных о конкретной услуге для расчета цены
            service_response = requests.get(f"{API_URL}/catalog/services/{service_id}")
            if service_response.status_code == 200:
                service_data = service_response.json()
                item_total = service_data['price'] * quantity
                total_price += item_total  # Добавляем к общей стоимости

                items.append({
                    "service_id": service_id,
                    "quantity": quantity
                })

        # Формируем данные для отправки с нужной структурой

        order_data = {
            "user_id": session['username'],
            "items": items,
            "total_price": total_price  # Передаем общую стоимость в запросе
        }
        print("Отправляемые данные:", order_data)
        # Отправляем запрос на FastAPI
        order_response = requests.post(f"{API_URL}/catalog/services/order", json=order_data)
        if order_response.status_code == 201:
            confirmation_message = "Заказ успешно оформлен!"
        else:
            confirmation_message = "Ошибка при оформлении заказа."

    return render_template("order_services.html", services=services, confirmation_message=confirmation_message)






@app.route('/logout')
def logout():
    """Выход из системы."""
    session.pop('username', None)
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(debug=True)
