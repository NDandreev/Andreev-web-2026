import random
from functools import lru_cache
from flask import Flask, render_template, abort, request, make_response
from faker import Faker

fake = Faker()

app = Flask(__name__)
application = app

images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': 'Заголовок поста',
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list())

@app.route('/posts/<int:index>')
def post(index):
    posts = posts_list()
    if index < 0 or index >= len(posts):
        abort(404)
    p = posts[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')

@app.route('/request-params')
def request_params():
    params = request.args
    return render_template('request_params.html', title='Параметры URL', params=params)

@app.route('/request-headers')
def request_headers():
    headers = dict(request.headers)
    return render_template('request_headers.html', title='Заголовки запроса', headers=headers)


@app.route('/cookies', methods=['GET', 'POST'])
def cookies():
    cookie_value = request.cookies.get('user_preference')
    message = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'set':
            message = 'Cookie успешно установлен!'
            resp = make_response(
                render_template('cookies.html', title='Cookie', cookie_value='dark_mode', message=message))
            resp.set_cookie('user_preference', 'dark_mode', max_age=60 * 60 * 24 * 30)  # на 30 дней
            return resp

        elif action == 'delete':
            message = 'Cookie успешно удалён!'
            resp = make_response(render_template('cookies.html', title='Cookie', cookie_value=None, message=message))
            resp.delete_cookie('user_preference')
            return resp

    return render_template('cookies.html', title='Cookie', cookie_value=cookie_value, message=None)


@app.route('/form-data', methods=['GET', 'POST'])
def form_data():
    submitted_data = None

    if request.method == 'POST':
        submitted_data = dict(request.form)

    return render_template('form_data.html', title='Параметры формы', submitted_data=submitted_data)


@app.route('/phone-validation', methods=['GET', 'POST'])
def phone_validation():
    error = None
    formatted_phone = None
    phone_input = ''

    if request.method == 'POST':
        phone_input = request.form.get('phone', '')
        is_valid, error, formatted = validate_phone(phone_input)

        if is_valid:
            formatted_phone = formatted
        else:
            error = error

    return render_template('phone_validation.html', title='Валидация телефона',
                           phone_input=phone_input, error=error, formatted_phone=formatted_phone)


def validate_phone(phone):

    allowed_chars = set('0123456789+ ()-.')

    for char in phone:
        if char not in allowed_chars:
            return False, "Недопустимый ввод. В номере телефона встречаются недопустимые символы.", None

    digits = ''.join([char for char in phone if char.isdigit()])
    digit_count = len(digits)
    phone_stripped = phone.strip()

    if phone_stripped.startswith('+7') or phone_stripped.startswith('8'):
        if digit_count == 11:
            is_eleven_digit_format = True
        else:
            return False, f"Недопустимый ввод. Неверное количество цифр. Ожидается 11 цифр, получено {digit_count}.", None
    else:
        if digit_count == 10:
            is_eleven_digit_format = False
        else:
            return False, f"Недопустимый ввод. Неверное количество цифр. Ожидается 10 цифр, получено {digit_count}.", None

    formatted = format_phone_number(digits, is_eleven_digit_format)

    return True, None, formatted


def format_phone_number(digits, is_eleven_digit_format):

    if is_eleven_digit_format:

        if digits.startswith('7'):
            digits = '8' + digits[1:]
    else:
        digits = '8' + digits

    return f"{digits[0]}-{digits[1:4]}-{digits[4:7]}-{digits[7:9]}-{digits[9:11]}"

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title='Страница не найдена'), 404