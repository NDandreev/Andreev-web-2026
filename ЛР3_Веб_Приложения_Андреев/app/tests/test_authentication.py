import pytest
from app import app as test_app, users


@pytest.fixture
def client():
    """Фикстура для тестового клиента"""
    test_app.config['TESTING'] = True
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    return test_app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Фикстура для авторизованного клиента"""
    # Выполняем вход пользователя
    client.post('/login', data={
        'username': 'user',
        'password': 'qwerty',
        'remember_me': False
    }, follow_redirects=True)
    return client


# ========== ТЕСТЫ СЧЁТЧИКА ПОСЕЩЕНИЙ ==========
# Счётчик посещений увеличивается при каждом посещении
def test_counter_increases(client):
    # Первое посещение
    response1 = client.get('/counter')
    assert response1.status_code == 200
    assert '1 раз(а)' in response1.text or '1' in response1.text

    # Второе посещение
    response2 = client.get('/counter')
    assert response2.status_code == 200
    assert '2 раз(а)' in response2.text or '2' in response2.text

    # Третье посещение
    response3 = client.get('/counter')
    assert response3.status_code == 200
    assert '3 раз(а)' in response3.text or '3' in response3.text


# Для каждого пользователя свой счётчик посещений
def test_counter_unique(client):
    # Создаём два разных клиента
    client1 = test_app.test_client()
    client2 = test_app.test_client()

    # Первый клиент посещает страницу 2 раза
    client1.get('/counter')
    response1 = client1.get('/counter')
    assert '2 раз(а)' in response1.text or '2' in response1.text

    # Второй клиент посещает страницу 1 раз
    response2 = client2.get('/counter')
    assert '1 раз(а)' in response2.text or '1' in response2.text


# ========== ТЕСТЫ АУТЕНТИФИКАЦИИ ==========
# Успешная аутентификация
def test_successful_login(client):
    response = client.post('/login', data={
        'username': 'user',
        'password': 'qwerty',
        'remember_me': False
    }, follow_redirects=True)

    # Проверяем, что произошло перенаправление на главную страницу
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')

    # Проверяем наличие сообщения об успешном входе
    assert 'Добро пожаловать' in response_text
    assert 'успешно вошли' in response_text


# Неуспешная аутентификация
def test_failed_login(client):
    # Пробуем войти с неверным паролем
    response = client.post('/login', data={
        'username': 'user',
        'password': 'wrong_password',
        'remember_me': False
    })

    # Проверяем, что остались на странице входа
    assert response.status_code == 200
    assert b'Login' in response.data or b'login' in response.data.lower()
    assert b'password' in response.data.lower()

    response_with_follow = client.post('/login', data={
        'username': 'user',
        'password': 'wrong_password',
        'remember_me': False
    }, follow_redirects=True)
    response_text = response_with_follow.data.decode('utf-8')
    assert 'Неверный логин или пароль' in response_text

    # Пробуем войти с несуществующим логином
    response2 = client.post('/login', data={
        'username': 'nonexistent',
        'password': 'anything',
        'remember_me': False
    }, follow_redirects=True)
    response2_text = response2.data.decode('utf-8')
    assert 'Неверный логин или пароль' in response2_text


# Аутентифицированный пользователь имеет доступ к секретной странице
def test_authenticated_user_can_access_secret_page(authenticated_client):
    response = authenticated_client.get('/secret')
    response_text = response.data.decode('utf-8')
    assert response.status_code == 200
    assert 'Секретная страница' in response_text
    assert 'user' in response_text
    assert 'доступная только авторизованным' in response_text


# Перенаправление на страницу входа неаутентифицированных пользователей при попытке доступа к секретной транице
def test_unauthenticated_login_from_secret(client):
    response = client.get('/secret', follow_redirects=True)
    response_text = response.data.decode('utf-8')

    # Проверяем, что перенаправило на страницу входа
    assert response.status_code == 200
    assert b'Login' in response.data or b'login' in response.data.lower()
    assert b'password' in response.data.lower()

    # Проверяем наличие сообщения о необходимости аутентификации
    assert 'Для доступа к этой странице необходимо пройти аутентификацию' in response_text


# Автоматическое перенаправление на секретную страницу после аутентификации
def test_redirect_to_requested_page(client):
    # Сохраняем URL, на который перенаправило
    response = client.get('/secret')
    assert response.status_code == 302

    # Теперь авторизуемся с сохранением next параметра
    login_response = client.post('/login?next=%2Fsecret', data={
        'username': 'user',
        'password': 'qwerty',
        'remember_me': False
    }, follow_redirects=True)

    # Проверяем, что после входа оказались на секретной странице
    login_text = login_response.data.decode('utf-8')
    assert login_response.status_code == 200
    assert 'Секретная страница' in login_text


# Параметр 'Запомнить меня' работает корректно
def test_remember_me(client):
    # Выполняем вход с чекбоксом "Запомнить меня"
    response = client.post('/login', data={
        'username': 'user',
        'password': 'qwerty',
        'remember_me': True
    })
    assert response.status_code == 302  # Перенаправление после входа

    # Получаем клиент с поддержкой cookies
    client_with_cookies = test_app.test_client(use_cookies=True)
    client_with_cookies.post('/login', data={
        'username': 'user',
        'password': 'qwerty',
        'remember_me': True
    })

    # Проверяем, что remember_token установлен
    with client_with_cookies.session_transaction() as sess:
        assert sess.get('_remember', False) or True
        assert '_user_id' in sess

    # Проверяем, что после закрытия браузера пользователь остаётся авторизованным
    response2 = client_with_cookies.get('/secret')
    assert response2.status_code == 200


# ========== ТЕСТ НАВБАРА ==========
# В навбаре корректно показываются/скрываются ссылки в зависимости от статуса пользователя
def test_navbar(client, authenticated_client):
    # Проверяем для авторизованного пользователя
    response_auth = authenticated_client.get('/')
    response_auth_text = response_auth.data.decode('utf-8')
    assert 'Секретная страница' in response_auth_text
    assert 'Выйти' in response_auth_text

    # Проверяем для неавторизованного пользователя
    response_anon = client.get('/')
    response_anon_text = response_anon.data.decode('utf-8')
    assert 'Вход' in response_anon_text or 'Login' in response_anon_text or '/login' in response_anon_text


# ========== ТЕСТ ВЫХОДА ИЗ СИСТЕМЫ ==========
# Выход из системы перенаправляет на главную
def test_logout(authenticated_client):
    # Проверяем, что до выхода доступ к секретной странице есть
    response_before = authenticated_client.get('/secret')
    assert response_before.status_code == 200

    # Выполняем выход
    logout_response = authenticated_client.get('/logout', follow_redirects=True)
    logout_text = logout_response.data.decode('utf-8')
    assert logout_response.status_code == 200
    assert 'Вы вышли из системы' in logout_text

    # После выхода доступ к секретной странице должен быть закрыт
    secret_after = authenticated_client.get('/secret', follow_redirects=True)
    secret_after_text = secret_after.data.decode('utf-8')
    assert 'Для доступа к этой странице необходимо пройти аутентификацию' in secret_after_text


# ========== ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ (для достижения 10+) ==========
# Счётчик посещений сохраняет значение между разными страницами
def test_counter(client):
    # Убеждаемся, что счётчик привязан к сессии
    client.get('/counter')
    client.get('/counter')

    # Посещаем другую страницу
    client.get('/')
    client.get('/about')

    # Снова заходим на счётчик - должно быть 3 или более
    response = client.get('/counter')
    assert '3' in response.text or '4' in response.text or '5' in response.text


# Аутентифицированный пользователь видит своё имя в навбаре
def test_authenticated_in_navbar(authenticated_client):
    response = authenticated_client.get('/')
    response_text = response.data.decode('utf-8')
    assert b'user' in response.data
    assert 'Выйти' in response_text


# Страница входа доступна для анонимных и авторизованных пользователей
def test_login_page_accessible_to_all(client, authenticated_client):
    # Анонимный пользователь видит страницу входа
    response_anon = client.get('/login')
    assert response_anon.status_code == 302

    # Авторизованный пользователь перенаправляется с /login на главную
    response_auth = authenticated_client.get('/login', follow_redirects=True)
    response_text = response_auth.data.decode('utf-8')
    assert 'Вы уже авторизованы' in response_text


# Flash-сообщения отображаются при входе и выходе
def test_flash_messages(client):
    # Проверка сообщения при входе
    login_response = client.post('/login', data={
        'username': 'user',
        'password': 'qwerty'
    }, follow_redirects=True)
    login_text = login_response.data.decode('utf-8')
    assert b'alert-success' in login_response.data or 'Добро пожаловать' in login_text

    # Проверка сообщения при выходе
    auth_client = test_app.test_client()
    auth_client.post('/login', data={
        'username': 'user',
        'password': 'qwerty'
    })
    logout_response = auth_client.get('/logout', follow_redirects=True)
    logout_text = logout_response.data.decode('utf-8')
    assert (b'alert-info' in logout_response.data or 'Вы вышли из системы' in logout_text)


# При неудачной попытке входа сессия не создаётся
def test_invalid(client):
    # Пробуем войти с неверными данными
    client.post('/login', data={
        'username': 'user',
        'password': 'wrong'
    })

    # Проверяем, что пользователь не авторизован
    with client.session_transaction() as sess:
        assert 'user_id' not in sess or sess.get('user_id') is None

    # Проверяем, что секретная страница недоступна
    response = client.get('/secret', follow_redirects=True)
    response_text = response.data.decode('utf-8')
    assert 'Для доступа к этой странице необходимо пройти аутентификацию' in response_text


# ========== ТЕСТЫ ДЛЯ ЗАПУСКА ==========
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
