import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


#ТЕСТЫ ДЛЯ ПАРАМЕТРОВ URL

def test_request_params_page_displays_params(client):
    """тест - страница параметров URL отображает все переданные параметры"""
    response = client.get('/request-params?name=John&age=25&city=Moscow')
    assert response.status_code == 200
    assert 'name' in response.text
    assert 'John' in response.text
    assert 'age' in response.text
    assert '25' in response.text
    assert 'city' in response.text
    assert 'Moscow' in response.text


def test_request_params_page_empty(client):
    """тест - страница параметров URL без параметров показывает сообщение"""
    response = client.get('/request-params')
    assert response.status_code == 200
    assert 'Параметры не переданы' in response.text


#ТЕСТЫ ДЛЯ ЗАГОЛОВКОВ ЗАПРОСА

def test_request_headers_page_displays_headers(client):
    """тест - страница заголовков запроса отображает заголовки"""
    response = client.get('/request-headers')
    assert response.status_code == 200
    # Проверяем наличие основных заголовков
    assert 'User-Agent' in response.text
    assert 'Host' in response.text


def test_request_headers_page_displays_values(client):
    """тест - страница заголовков запроса отображает значения"""
    response = client.get('/request-headers')
    assert response.status_code == 200
    assert '127.0.0.1' in response.text or 'localhost' in response.text


#ТЕСТЫ ДЛЯ COOKIE

def test_cookies_page_initial_state(client):
    """тест - страница cookie показывает, что cookie не установлен"""
    response = client.get('/cookies')
    assert response.status_code == 200
    assert 'не установлен' in response.text


def test_cookies_set_cookie(client):
    """тест - установка cookie работает корректно"""
    response = client.post('/cookies', data={'action': 'set'})
    assert response.status_code == 200
    assert 'успешно установлен' in response.text
    # Проверяем, что cookie был установлен
    assert 'user_preference' in response.headers.get('Set-Cookie', '')


def test_cookies_delete_cookie(client):
    """тест - удаление cookie работает корректно"""
    # Сначала устанавливаем cookie
    client.post('/cookies', data={'action': 'set'})
    # Затем удаляем
    response = client.post('/cookies', data={'action': 'delete'})
    assert response.status_code == 200
    assert 'успешно удалён' in response.text


#ТЕСТЫ ДЛЯ ПАРАМЕТРОВ ФОРМЫ

def test_form_data_page_get(client):
    """тест - GET запрос к странице формы показывает пустое состояние"""
    response = client.get('/form-data')
    assert response.status_code == 200
    assert 'Данные не отправлены' in response.text


def test_form_data_page_post(client):
    """тест - POST запрос с данными формы отображает отправленные значения"""
    response = client.post('/form-data', data={
        'name': 'Тестовый Пользователь',
        'email': 'test@example.com',
        'message': 'Тестовое сообщение'
    })
    assert response.status_code == 200
    assert 'Тестовый Пользователь' in response.text
    assert 'test@example.com' in response.text
    assert 'Тестовое сообщение' in response.text


#ТЕСТЫ ДЛЯ ВАЛИДАЦИИ ТЕЛЕФОНА

def test_phone_validation_valid_plus7(client):
    """тест - валидный номер с +7 форматируется правильно"""
    response = client.post('/phone-validation', data={'phone': '+7 (123) 456-75-90'})
    assert response.status_code == 200
    assert '8-123-456-75-90' in response.text


def test_phone_validation_valid_8(client):
    """тест - валидный номер с 8 форматируется правильно"""
    response = client.post('/phone-validation', data={'phone': '8(123)4567590'})
    assert response.status_code == 200
    assert '8-123-456-75-90' in response.text


def test_phone_validation_valid_10_digits(client):
    """тест - валидный номер из 10 цифр форматируется правильно"""
    response = client.post('/phone-validation', data={'phone': '123.456.75.90'})
    assert response.status_code == 200
    assert '8-123-456-75-90' in response.text


def test_phone_validation_invalid_symbols(client):
    """тест - номер с недопустимыми символами вызывает ошибку"""
    response = client.post('/phone-validation', data={'phone': '123abc456'})
    assert response.status_code == 200
    assert 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.' in response.text
    assert 'is-invalid' in response.text


def test_phone_validation_wrong_digit_count_plus7(client):
    """тест - номер с +7 и неправильным количеством цифр вызывает ошибку"""
    response = client.post('/phone-validation', data={'phone': '+7 (123) 456'})
    assert response.status_code == 200
    assert 'Неверное количество цифр' in response.text


def test_phone_validation_wrong_digit_count_10_digits_format(client):
    """тест - номер без +7 с 11 цифрами вызывает ошибку"""
    response = client.post('/phone-validation', data={'phone': '12345678901'})
    assert response.status_code == 200
    assert 'Неверное количество цифр' in response.text


def test_phone_validation_bootstrap_error_classes(client):
    """тест - при ошибке используются Bootstrap классы is-invalid и invalid-feedback"""
    response = client.post('/phone-validation', data={'phone': 'invalid!!!'})
    assert response.status_code == 200
    assert 'is-invalid' in response.text
    assert 'invalid-feedback' in response.text


def test_phone_validation_empty_input(client):
    """тест - пустой ввод вызывает ошибку"""
    response = client.post('/phone-validation', data={'phone': ''})
    assert response.status_code == 200
    assert 'Неверное количество цифр' in response.text or 'Недопустимый' in response.text


def test_phone_validation_spaces_only(client):
    """тест - только пробелы вызывают ошибку"""
    response = client.post('/phone-validation', data={'phone': '     '})
    assert response.status_code == 200
    assert 'Неверное количество цифр' in response.text


def test_phone_validation_with_dots(client):
    """тест - номер с точками форматируется правильно"""
    response = client.post('/phone-validation', data={'phone': '8912.345.67.89'})
    assert response.status_code == 200
    assert '8-912-345-67-89' in response.text


def test_phone_validation_with_hyphens(client):
    """тест - номер с дефисами форматируется правильно"""
    response = client.post('/phone-validation', data={'phone': '8-912-345-67-89'})
    assert response.status_code == 200
    assert '8-912-345-67-89' in response.text


def test_phone_validation_with_parentheses(client):
    """тест - номер со скобками форматируется правильно"""
    response = client.post('/phone-validation', data={'phone': '8(912)3456789'})
    assert response.status_code == 200
    assert '8-912-345-67-89' in response.text