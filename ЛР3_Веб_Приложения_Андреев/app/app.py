from flask import Flask, render_template, session, redirect, url_for, request, flash
from faker import Faker
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

fake = Faker()

app = Flask(__name__)
application = app

# Секретный ключ для работы сессий и Flask-Login
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# Задаём функцию для перенаправления неавторизованных пользователей
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо пройти аутентификацию.'
login_manager.login_message_category = 'warning'


# Модель пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


# Предопределённый пользователь
users = {
    'user': User(id=1, username='user', password='qwerty')
}


# Функция загрузки пользователя по ID
@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if str(user.id) == str(user_id):
            return user
    return None


# Счётчик посещений
@app.route('/counter')
def counter():
    visit_count = session.get('visit_count', 0)
    visit_count += 1
    session['visit_count'] = visit_count

    return render_template(
        'counter.html',
        title='Счётчик посещений',
        visit_count=visit_count
    )


# Аутентификация
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        flash('Вы уже авторизованы.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'  # Чекбокс "Запомнить меня"

        # Проверяем, существует ли пользователь и правильный ли пароль
        user = users.get(username)
        if user and user.password == password:
            login_user(user, remember=remember_me)
            flash(f'Добро пожаловать, {username}! Вы успешно вошли в систему.', 'success')

            # Перенаправляем на секретную страницу
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль.', 'danger')

    return render_template('login.html', title='Вход')


# Выход из системы
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


# Секретная страница
@app.route('/secret')
@login_required
def secret():
    return render_template(
        'secret.html',
        title='Секретная страница',
        username=current_user.username
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title='Страница не найдена'), 404
