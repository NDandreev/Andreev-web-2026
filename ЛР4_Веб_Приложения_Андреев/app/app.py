from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
application = app

# Конфигурация
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация БД
db = SQLAlchemy(app)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо пройти аутентификацию.'
login_manager.login_message_category = 'warning'


# Модели БД
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    patronymic = db.Column(db.String(100), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    role = db.relationship('Role', back_populates='users', lazy='select')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join([p for p in parts if p])

    @property
    def short_name(self):
        result = self.last_name if self.last_name else ''
        if self.first_name:
            result += f' {self.first_name[0]}.' if result else f'{self.first_name[0]}.'
        if self.patronymic:
            result += f'{self.patronymic[0]}.' if result else f'{self.patronymic[0]}.'
        return result if result else self.login

    def has_permission(self, action, target_user=None):
        # Проверка прав доступа
        role_name = self.role.name if self.role else 'guest'

        # Admin - все права
        if role_name == 'admin':
            return True

        # Moderator - может удалять всех, кроме админов
        if role_name == 'moderator':
            if action == 'delete':
                if target_user and target_user.role and target_user.role.name == 'admin':
                    return False  # Нельзя удалять админа
                return True
            elif action == 'edit':
                return False  # Модератор не может редактировать
            elif action == 'create':
                return False  # Модератор не может создавать

        # User - может редактировать ТОЛЬКО свой профиль
        if role_name == 'user':
            if action == 'edit':
                return target_user and target_user.id == self.id
            elif action == 'delete':
                return False
            elif action == 'create':
                return False

        # Guest - ничего не может
        return False


# Добавляем обратную связь в Role
Role.users = db.relationship('User', back_populates='role', lazy='select')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Функции валидации
def validate_login(login):
    if not login or len(login) < 5:
        return False, "Логин должен содержать не менее 5 символов"
    if not re.match(r'^[a-zA-Z0-9]+$', login):
        return False, "Логин может содержать только латинские буквы и цифры"
    return True, ""


def validate_password(password):
    if not password:
        return False, "Пароль не может быть пустым"
    if len(password) < 8:
        return False, "Пароль должен содержать не менее 8 символов"
    if len(password) > 128:
        return False, "Пароль не должен превышать 128 символов"
    if ' ' in password:
        return False, "Пароль не должен содержать пробелов"
    if not re.search(r'[A-ZА-Я]', password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[a-zа-я]', password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[0-9]', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    allowed_pattern = r'^[a-zA-Zа-яА-Я0-9~!?@#$%^&*_\-+()\[\]{}><\/\\|"\'.,:;]+$'
    if not re.match(allowed_pattern, password):
        return False, "Пароль содержит недопустимые символы"
    return True, ""


# Декоратор для проверки прав
def permission_required(action):
    """Декоратор для проверки прав доступа"""

    def decorator(f):
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Для доступа необходимо авторизоваться', 'warning')
                return redirect(url_for('login'))

            target_user = None
            if 'user_id' in kwargs:
                target_user = User.query.get(kwargs['user_id'])

            if not current_user.has_permission(action, target_user):
                flash('У вас недостаточно прав для выполнения этого действия', 'danger')
                return redirect(url_for('user_list'))

            return f(*args, **kwargs)

        wrapper.__name__ = f.__name__
        return wrapper

    return decorator


# Маршруты
@app.route('/')
def index():
    return render_template('index.html', title='Задание')


@app.route('/users')
def user_list():
    users = User.query.order_by(User.id).all()
    return render_template('user_list.html', title='Список пользователей', users=users)


@app.route('/user/<int:user_id>')
def view_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))
    return render_template('view_user.html', title='Просмотр пользователя', user=user)


@app.route('/user/create', methods=['GET', 'POST'])
@login_required
@permission_required('create')
def create_user():
    """Создание пользователя (только для admin)"""
    roles = Role.query.order_by(Role.name).all()

    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        last_name = request.form.get('last_name', '').strip() or None
        first_name = request.form.get('first_name', '').strip()
        patronymic = request.form.get('patronymic', '').strip() or None
        role_id = request.form.get('role_id')
        role_id = int(role_id) if role_id and role_id != '' else None

        errors = {}

        is_valid, msg = validate_login(login)
        if not is_valid:
            errors['login'] = msg
        else:
            existing = User.query.filter_by(login=login).first()
            if existing:
                errors['login'] = 'Пользователь с таким логином уже существует'

        is_valid, msg = validate_password(password)
        if not is_valid:
            errors['password'] = msg

        if not first_name:
            errors['first_name'] = 'Имя не может быть пустым'

        if errors:
            return render_template('user_form.html', title='Создание пользователя',
                                   user=None, roles=roles, errors=errors,
                                   form_data=request.form), 400

        try:
            new_user = User(
                login=login,
                password_hash=generate_password_hash(password),
                last_name=last_name,
                first_name=first_name,
                patronymic=patronymic,
                role_id=role_id
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Пользователь {new_user.full_name or new_user.login} успешно создан', 'success')
            return redirect(url_for('user_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании пользователя: {str(e)}', 'danger')
            return render_template('user_form.html', title='Создание пользователя',
                                   user=None, roles=roles, errors=errors,
                                   form_data=request.form), 500

    return render_template('user_form.html', title='Создание пользователя',
                           user=None, roles=roles, errors={}, form_data={})


@app.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('edit')
def edit_user(user_id):
    """Редактирование пользователя (user - только свой профиль, admin - все)"""
    user = User.query.get(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))

    # Проверка прав уже в декораторе, но добавим дополнительную проверку
    if not current_user.has_permission('edit', user):
        flash('Вы можете редактировать только свой профиль', 'danger')
        return redirect(url_for('user_list'))

    roles = Role.query.order_by(Role.name).all()

    if request.method == 'POST':
        last_name = request.form.get('last_name', '').strip() or None
        first_name = request.form.get('first_name', '').strip()
        patronymic = request.form.get('patronymic', '').strip() or None
        role_id = request.form.get('role_id')
        role_id = int(role_id) if role_id and role_id != '' else None

        # Только admin может менять роль
        if current_user.role.name != 'admin':
            role_id = user.role_id  # Оставляем старую роль

        errors = {}

        if not first_name:
            errors['first_name'] = 'Имя не может быть пустым'

        if errors:
            return render_template('user_form.html', title='Редактирование пользователя',
                                   user=user, roles=roles, errors=errors,
                                   form_data=request.form), 400

        try:
            user.last_name = last_name
            user.first_name = first_name
            user.patronymic = patronymic
            user.role_id = role_id
            db.session.commit()
            flash(f'Данные пользователя {user.full_name or user.login} успешно обновлены', 'success')
            return redirect(url_for('user_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении данных: {str(e)}', 'danger')
            return render_template('user_form.html', title='Редактирование пользователя',
                                   user=user, roles=roles, errors=errors,
                                   form_data=request.form), 500

    form_data = {
        'last_name': user.last_name or '',
        'first_name': user.first_name or '',
        'patronymic': user.patronymic or '',
        'role_id': str(user.role_id) if user.role_id else ''
    }
    return render_template('user_form.html', title='Редактирование пользователя',
                           user=user, roles=roles, errors={}, form_data=form_data)


@app.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@permission_required('delete')
def delete_user(user_id):
    """Удаление пользователя (admin и moderator, moderator не может удалить admin)"""
    user = User.query.get(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))

    # Проверка: moderator не может удалить admin
    if current_user.role.name == 'moderator' and user.role and user.role.name == 'admin':
        flash('Модератор не может удалить администратора', 'danger')
        return redirect(url_for('user_list'))

    # Нельзя удалить самого себя
    if user.id == current_user.id:
        flash('Вы не можете удалить свой собственный аккаунт', 'danger')
        return redirect(url_for('user_list'))

    user_name = user.full_name or user.login

    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь {user_name} успешно удалён', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')

    return redirect(url_for('user_list'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Смена пароля (доступно всем авторизованным)"""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = {}

        if not current_user.check_password(old_password):
            errors['old_password'] = 'Неверный текущий пароль'

        is_valid, msg = validate_password(new_password)
        if not is_valid:
            errors['new_password'] = msg

        if new_password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают'

        if current_user.check_password(new_password):
            errors['new_password'] = 'Новый пароль должен отличаться от текущего'

        if errors:
            return render_template('change_password.html', title='Изменение пароля', errors=errors), 400

        try:
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Пароль успешно изменён', 'success')
            return redirect(url_for('user_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при смене пароля: {str(e)}', 'danger')
            return render_template('change_password.html', title='Изменение пароля', errors=errors), 500

    return render_template('change_password.html', title='Изменение пароля', errors={})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Вы уже авторизованы.', 'info')
        return redirect(url_for('user_list'))

    if request.method == 'POST':
        login = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'

        user = User.query.filter_by(login=login).first()

        # Любой пользователь может войти, независимо от роли
        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            flash(f'Добро пожаловать, {user.full_name or user.login}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('user_list'))
        else:
            flash('Неверный логин или пароль.', 'danger')

    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title='Страница не найдена'), 404


# Инициализация БД
def init_db():
    with app.app_context():
        db.create_all()

        # Добавляем роли
        if Role.query.first() is None:
            roles = [
                Role(name='admin', description='Полный доступ: создание, редактирование, удаление'),
                Role(name='moderator', description='Может удалять пользователей (кроме админов)'),
                Role(name='user', description='Может редактировать только свой профиль'),
                Role(name='guest', description='Только просмотр'),
            ]
            db.session.add_all(roles)
            db.session.commit()


init_db()

if __name__ == '__main__':
    app.run(debug=True)