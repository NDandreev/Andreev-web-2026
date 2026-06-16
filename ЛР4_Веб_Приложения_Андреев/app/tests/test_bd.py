import pytest
from app import app as test_app, db, User, Role
from werkzeug.security import generate_password_hash


# Список для хранения созданных в тестах пользователей
created_test_users = []


@pytest.fixture
def client():
    """Фикстура для тестового клиента"""
    test_app.config['TESTING'] = True
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    # Используем реальную БД, а не временную
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    return test_app.test_client()


@pytest.fixture
def init_database():
    """Фикстура для инициализации тестовой БД"""
    with test_app.app_context():
        # Проверяем и создаём только отсутствующие роли
        admin_role = Role.query.filter_by(name='admin').first()
        user_role = Role.query.filter_by(name='user').first()

        if admin_role is None:
            admin_role = Role(name='admin', description='Администратор')
            db.session.add(admin_role)

        if user_role is None:
            user_role = Role(name='user', description='Пользователь')
            db.session.add(user_role)

        db.session.commit()

        # Обновляем ссылки на роли
        admin_role = Role.query.filter_by(name='admin').first()
        user_role = Role.query.filter_by(name='user').first()

        # Создаём тестового пользователя (если его нет)
        if User.query.filter_by(login='testuser').first() is None:
            test_user = User(
                login='testuser',
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Тест',
                last_name='Тестов',
                patronymic='Тестович',
                role_id=admin_role.id
            )
            db.session.add(test_user)

        # Создаём дополнительных пользователей для тестов (если их нет)
        if User.query.filter_by(login='ivanov').first() is None:
            user1 = User(
                login='ivanov',
                password_hash=generate_password_hash('Password123!'),
                first_name='Иван',
                last_name='Иванов',
                patronymic='Иванович',
                role_id=user_role.id
            )
            db.session.add(user1)

        if User.query.filter_by(login='petrov').first() is None:
            user2 = User(
                login='petrov',
                password_hash=generate_password_hash('Password123!'),
                first_name='Пётр',
                last_name='Петров',
                patronymic='Петрович',
                role_id=user_role.id
            )
            db.session.add(user2)

        db.session.commit()

        yield db


@pytest.fixture
def authenticated_client(client, init_database):
    """Фикстура для авторизованного клиента"""
    with client:
        # Выполняем вход пользователя testuser
        client.post('/login', data={
            'username': 'testuser',
            'password': 'TestPass123!'
        }, follow_redirects=True)
        return client


@pytest.fixture
def admin_client(client, init_database):
    """Фикстура для администратора"""
    with client:
        # Создаём админа если нет
        admin_role = Role.query.filter_by(name='admin').first()
        if User.query.filter_by(login='admin_test').first() is None:
            admin_user = User(
                login='admin_test',
                password_hash=generate_password_hash('AdminPass123!'),
                first_name='Админ',
                last_name='Тестов',
                role_id=admin_role.id
            )
            db.session.add(admin_user)
            db.session.commit()

        client.post('/login', data={
            'username': 'admin_test',
            'password': 'AdminPass123!'
        }, follow_redirects=True)
        return client


# Тест 1 - Страница со списком пользователей доступна
def test_user_list_page_accessible(client, init_database):
    response = client.get('/users')
    assert response.status_code == 200
    assert 'Список пользователей' in response.data.decode('utf-8')


# Тест 2 - В таблице отображаются пользователи
def test_user_list_shows_users_table(client, init_database):
    response = client.get('/users')
    response_text = response.data.decode('utf-8')
    assert 'Пользователи' in response_text or 'Список' in response_text
    assert 'Просмотр' in response_text


# Тест 3 - Кнопки 'Редактировать' и 'Удалить' НЕ видны для неавторизованных
def test_edit_and_delete_buttons_hidden_for_anonymous(client, init_database):
    response = client.get('/users')
    response_text = response.data.decode('utf-8')
    assert 'Просмотр' in response_text
    # Проверяем, что нет кнопок редактирования и удаления
    assert 'btn-warning' not in response_text or 'Редактировать' not in response_text
    assert 'btn-danger' not in response_text or 'Удалить' not in response_text


# Тест 4 - Кнопки 'Редактировать' и 'Удалить' видны для администратора
def test_edit_and_delete_buttons_visible_for_admin(admin_client, init_database):
    response = admin_client.get('/users')
    response_text = response.data.decode('utf-8')
    assert 'Редактировать' in response_text
    assert 'Удалить' in response_text
    assert 'Создание пользователя' in response_text


# Тест 5 - Страница просмотра пользователя доступна всем
def test_view_user_page_accessible(client, init_database):
    user = User.query.filter_by(login='testuser').first()
    if user:
        response = client.get(f'/user/{user.id}')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'Просмотр пользователя' in response_text


# Тест 6 - Просмотр несуществующего пользователя перенаправляет
def test_view_nonexistent_user_returns_404(client, init_database):
    response = client.get('/user/99999', follow_redirects=True)
    assert 'Пользователь не найден' in response.data.decode('utf-8')


# Тест 7 - Неавторизованный пользователь перенаправляется со страницы создания
def test_create_user_page_redirects_for_anonymous(client, init_database):
    response = client.get('/user/create', follow_redirects=True)
    response_text = response.data.decode('utf-8')
    assert 'Вход' in response_text or 'login' in response_text.lower()


# Тест 8 - Администратор имеет доступ к странице создания
def test_create_user_page_accessible_for_admin(admin_client, init_database):
    response = admin_client.get('/user/create')
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Создание пользователя' in response_text


# Тест 9 - Успешное создание нового пользователя
def test_create_user_success(admin_client, init_database):
    login = 'newcreatesuccess2'
    created_test_users.append(login)

    response = admin_client.post('/user/create', data={
        'login': login,
        'password': 'NewPass123!',
        'first_name': 'Новый',
        'last_name': 'Созданный',
        'patronymic': 'Новович',
        'role_id': '2'
    }, follow_redirects=True)

    response_text = response.data.decode('utf-8')
    assert ('успешно создан' in response_text or
            'Список пользователей' in response_text or
            'Пользователи' in response_text)


# Тест 10 - Валидация - логин слишком короткий (< 5 символов)
def test_create_user_validation_login_too_short(admin_client, init_database):
    response = admin_client.post('/user/create', data={
        'login': 'new',
        'password': 'NewPass123!',
        'first_name': 'Новый',
        'last_name': 'Тестовый'
    })

    response_text = response.data.decode('utf-8')
    assert 'Логин должен содержать не менее 5 символов' in response_text


# Тест 11 - Валидация - логин содержит недопустимые символы
def test_create_user_validation_login_invalid_chars(admin_client, init_database):
    response = admin_client.post('/user/create', data={
        'login': 'русскийлогин',
        'password': 'NewPass123!',
        'first_name': 'Новый',
        'last_name': 'Тестовый'
    })

    response_text = response.data.decode('utf-8')
    assert 'Логин может содержать только латинские буквы и цифры' in response_text


# Тест 12 - Валидация - логин уже существует
def test_create_user_validation_duplicate_login(admin_client, init_database):
    response = admin_client.post('/user/create', data={
        'login': 'testuser',
        'password': 'NewPass123!',
        'first_name': 'Новый',
        'last_name': 'Тестовый'
    })

    response_text = response.data.decode('utf-8')
    assert 'Пользователь с таким логином уже существует' in response_text


# Тест 13 - Валидация - пароль слишком короткий
def test_create_user_validation_password_too_short(admin_client, init_database):
    response = admin_client.post('/user/create', data={
        'login': 'newuser2',
        'password': 'Short1!',
        'first_name': 'Новый',
        'last_name': 'Тестовый'
    })

    response_text = response.data.decode('utf-8')
    assert 'Пароль должен содержать не менее 8 символов' in response_text


# Тест 14 - Валидация - пустое имя
def test_create_user_validation_empty_first_name(admin_client, init_database):
    response = admin_client.post('/user/create', data={
        'login': 'newuser3',
        'password': 'NewPass123!',
        'first_name': '',
        'last_name': 'Тестовый'
    })

    response_text = response.data.decode('utf-8')
    assert 'Имя не может быть пустым' in response_text


# Тест 15 - Страница редактирования доступна для администратора
def test_edit_user_page_accessible_for_admin(admin_client, init_database):
    user = User.query.filter_by(login='testuser').first()
    if user:
        response = admin_client.get(f'/user/{user.id}/edit')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'Редактирование' in response_text


# Тест 16 - На форме редактирования нет полей логин и пароль
def test_edit_user_no_login_password_fields(admin_client, init_database):
    user = User.query.filter_by(login='testuser').first()
    if user:
        response = admin_client.get(f'/user/{user.id}/edit')
        response_text = response.data.decode('utf-8')
        assert 'Логин' not in response_text
        assert 'Пароль' not in response_text


# Тест 17 - Успешное редактирование пользователя
def test_edit_user_success(admin_client, init_database):
    user = User.query.filter_by(login='ivanov').first()
    if user:
        response = admin_client.post(f'/user/{user.id}/edit', data={
            'first_name': 'ИзменённыйИван',
            'last_name': 'ИзменённыйИванов',
            'patronymic': 'ИзменённыйИванович',
            'role_id': '2'
        }, follow_redirects=True)

        response_text = response.data.decode('utf-8')
        assert 'успешно обновлены' in response_text


# Тест 18 - Неавторизованный пользователь перенаправляется при редактировании
def test_edit_user_redirects_for_anonymous(client, init_database):
    user = User.query.filter_by(login='testuser').first()
    if user:
        response = client.get(f'/user/{user.id}/edit', follow_redirects=True)
        response_text = response.data.decode('utf-8')
        assert 'Вход' in response_text or 'Для доступа' in response_text


# Тест 19 - Успешное удаление пользователя
def test_delete_user_success(admin_client, init_database):
    login = 'todeleteuser'
    created_test_users.append(login)

    # Создаём пользователя для удаления
    admin_client.post('/user/create', data={
        'login': login,
        'password': 'DeletePass123!',
        'first_name': 'НаУдаление',
        'last_name': 'Удаляемый'
    })

    user_to_delete = User.query.filter_by(login=login).first()
    if user_to_delete:
        response = admin_client.post(f'/user/{user_to_delete.id}/delete', follow_redirects=True)
        response_text = response.data.decode('utf-8')
        assert 'успешно удалён' in response_text
        # Удаляем из списка, так как пользователь уже удалён
        created_test_users.remove(login)


# Тест 20 - Удаление работает только через POST запрос
def test_delete_user_requires_post(admin_client, init_database):
    user = User.query.filter_by(login='petrov').first()
    if user:
        response = admin_client.get(f'/user/{user.id}/delete')
        assert response.status_code == 405


# Тест 21 - Страница смены пароля доступна авторизованным
def test_change_password_page_accessible(client, init_database):
    with client:
        # Создаём пользователя
        user = User.query.filter_by(login='pw_page_user').first()
        if user is None:
            user = User(
                login='pw_page_user',
                password_hash=generate_password_hash('PagePass123!'),
                first_name='Тест',
                last_name='Доступ'
            )
            db.session.add(user)
            db.session.commit()
            created_test_users.append('pw_page_user')

        # Авторизуемся
        client.post('/login', data={
            'username': 'pw_page_user',
            'password': 'PagePass123!'
        }, follow_redirects=True)

        # Проверяем доступ к странице смены пароля
        response = client.get('/change-password', follow_redirects=True)
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'Изменение пароля' in response_text or 'Текущий пароль' in response_text


# Тест 22 - Успешная смена пароля
def test_change_password_success(client, init_database):
    with client:
        # Создаём пользователя специально для теста смены пароля
        login = 'test_pw_change'
        created_test_users.append(login)

        user = User.query.filter_by(login=login).first()
        if user is None:
            user = User(
                login=login,
                password_hash=generate_password_hash('OldPass123!'),
                first_name='Тест',
                last_name='СменаПароля'
            )
            db.session.add(user)
            db.session.commit()

        # Авторизуемся
        client.post('/login', data={
            'username': login,
            'password': 'OldPass123!'
        }, follow_redirects=True)

        # Меняем пароль
        client.post('/change-password', data={
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!'
        }, follow_redirects=True)

        # Выходим
        client.get('/logout', follow_redirects=True)

        # Пробуем войти с новым паролем
        response = client.post('/login', data={
            'username': login,
            'password': 'NewPass456!'
        }, follow_redirects=True)

        response_text = response.data.decode('utf-8')
        assert 'Добро пожаловать' in response_text or 'Список пользователей' in response_text


# Тест 23 - Неверный старый пароль
def test_change_password_wrong_old(client, init_database):
    with client:
        login = 'testuser_pass'
        created_test_users.append(login)

        user = User.query.filter_by(login=login).first()
        if user is None:
            user = User(
                login=login,
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Тест',
                last_name='Парольный'
            )
            db.session.add(user)
            db.session.commit()

        client.post('/login', data={
            'username': login,
            'password': 'TestPass123!'
        }, follow_redirects=True)

        response = client.post('/change-password', data={
            'old_password': 'WrongPassword!',
            'new_password': 'NewTestPass456!',
            'confirm_password': 'NewTestPass456!'
        }, follow_redirects=True)

        response_text = response.data.decode('utf-8')
        assert 'Неверный текущий пароль' in response_text


# Тест 24 - Пароли не совпадают
def test_change_password_mismatch(client, init_database):
    with client:
        login = 'testuser_mismatch'
        created_test_users.append(login)

        user = User.query.filter_by(login=login).first()
        if user is None:
            user = User(
                login=login,
                password_hash=generate_password_hash('TestPass123!'),
                first_name='Тест',
                last_name='Несовпадение'
            )
            db.session.add(user)
            db.session.commit()

        client.post('/login', data={
            'username': login,
            'password': 'TestPass123!'
        }, follow_redirects=True)

        response = client.post('/change-password', data={
            'old_password': 'TestPass123!',
            'new_password': 'NewTestPass456!',
            'confirm_password': 'DifferentPass789!'
        }, follow_redirects=True)

        response_text = response.data.decode('utf-8')
        assert 'Пароли не совпадают' in response_text


# Тест 25 - Успешная аутентификация
def test_successful_login(client, init_database):
    with client:
        login = 'logintestuser'
        created_test_users.append(login)

        user = User.query.filter_by(login=login).first()
        if user is None:
            user = User(
                login=login,
                password_hash=generate_password_hash('LoginPass123!'),
                first_name='Логин',
                last_name='Тестовый'
            )
            db.session.add(user)
            db.session.commit()

        response = client.post('/login', data={
            'username': login,
            'password': 'LoginPass123!'
        }, follow_redirects=True)

        response_text = response.data.decode('utf-8')
        assert 'Добро пожаловать' in response_text or 'Список пользователей' in response_text


# Тест 26 - Неуспешная аутентификация - неверный пароль
def test_failed_login_wrong_password(client, init_database):
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'WrongPassword!'
    }, follow_redirects=True)

    response_text = response.data.decode('utf-8')
    assert 'Неверный логин или пароль' in response_text


# Тест 27 - Выход из системы
def test_logout(client, init_database):
    with client:
        login = 'logoutuser'
        created_test_users.append(login)

        user = User.query.filter_by(login=login).first()
        if user is None:
            user = User(
                login=login,
                password_hash=generate_password_hash('LogoutPass123!'),
                first_name='Выход',
                last_name='Тестовый'
            )
            db.session.add(user)
            db.session.commit()

        client.post('/login', data={
            'username': login,
            'password': 'LogoutPass123!'
        }, follow_redirects=True)

        response = client.get('/logout', follow_redirects=True)
        response_text = response.data.decode('utf-8')
        assert 'Вы вышли из системы' in response_text


def cleanup_all_test_users():
    """Принудительное удаление всех тестовых пользователей"""
    with test_app.app_context():
        # Список всех тестовых логинов, которые могли быть созданы
        test_logins = [
            'newcreatesuccess2',
            'todeleteuser',
            'pw_page_user',
            'test_pw_change',
            'testuser_pass',
            'testuser_mismatch',
            'logintestuser',
            'logoutuser',
            'test_admin_creator',
            'admin_test',
        ]

        deleted = 0
        for login in test_logins:
            user = User.query.filter_by(login=login).first()
            if user:
                db.session.delete(user)
                deleted += 1
                print(f"  Удалён: {login}")

        # Удаляем пользователей с изменёнными именами
        users_with_changed_names = User.query.filter(
            (User.first_name == 'ИзменённыйИван') |
            (User.last_name == 'ИзменённыйИванов') |
            (User.first_name == 'ИзменённыйТест') |
            (User.last_name == 'ИзменённыйТестов')
        ).all()

        for user in users_with_changed_names:
            db.session.delete(user)
            deleted += 1

        # Удаляем пользователей, у которых логин содержит 'test' но не является основным
        all_users = User.query.all()
        for user in all_users:
            if 'test' in user.login and user.login not in ['testuser']:
                if user.login not in test_logins:
                    db.session.delete(user)
                    deleted += 1

        db.session.commit()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
    cleanup_all_test_users()
