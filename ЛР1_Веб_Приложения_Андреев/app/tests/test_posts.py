import pytest
from datetime import datetime
from app import app as flask_app


@pytest.fixture
def client():
    return flask_app.test_client()


@pytest.fixture
def posts_list():
    return [
        {
            'title': 'Заголовок поста',
            'text': 'Текст поста для тестирования',
            'author': 'Иванов Иван Иванович',
            'date': datetime(2025, 3, 10),
            'image_id': '123.jpg',
            'comments': [
                {
                    'author': 'Петров Петр',
                    'text': 'Отличный пост!',
                    'replies': [
                        {
                            'author': 'Сидоров Сидор',
                            'text': 'Согласен!'
                        }
                    ]
                }
            ]
        }
    ]


def test_posts_index(client):
    """тест - страница постов недоступна"""
    response = client.get("/posts")
    assert response.status_code == 200
    assert "Последние посты" in response.text


def test_posts_index_template(client, mocker, posts_list):
    """тест - при рендеринге страницы постов используется правильный шаблон"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts')
    assert response.status_code == 200
    assert "Последние посты" in response.text
    assert posts_list[0]['title'] in response.text


def test_post_page_uses_correct_template(client, mocker, posts_list):
    """тест - страница отдельного поста использует шаблон post.html"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    assert "Оставьте комментарий" in response.text
    assert posts_list[0]['title'] in response.text


def test_post_page_passes_all_data(client, mocker, posts_list):
    """тест - на страницу передаются все данные поста"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    post = posts_list[0]
    assert post['title'] in response.text
    assert post['author'] in response.text
    assert post['text'] in response.text
    assert post['image_id'] in response.text


def test_post_page_displays_title(client, mocker, posts_list):
    """тест - на странице поста отображается заголовок"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    assert posts_list[0]['title'] in response.text


def test_post_page_displays_author(client, mocker, posts_list):
    """тест - на странице поста отображается имя автора"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    assert posts_list[0]['author'] in response.text


def test_post_page_displays_text(client, mocker, posts_list):
    """тест - на странице поста отображается текст"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    assert posts_list[0]['text'] in response.text


def test_post_page_displays_image(client, mocker, posts_list):
    """тест - на странице поста отображается изображение"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    assert posts_list[0]['image_id'] in response.text


def test_post_page_date_format(client, mocker, posts_list):
    """тест - дата публикации отображается в правильном формате"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    date = posts_list[0]['date']
    expected_date_format = date.strftime('%d.%m.%Y')
    assert expected_date_format in response.text


def test_post_page_displays_comment_form(client, mocker, posts_list):
    """тест - на странице поста присутствует форма для комментария"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    assert "Оставьте комментарий" in response.text
    assert '<form' in response.text
    assert 'textarea' in response.text
    assert 'Отправить' in response.text
    assert 'btn btn-primary' in response.text


def test_post_page_displays_comments(client, mocker, posts_list):
    """тест - на странице поста отображаются комментарии"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    if posts_list[0]['comments']:
        assert "Комментарии" in response.text
        for comment in posts_list[0]['comments']:
            assert comment['author'] in response.text
            assert comment['text'] in response.text


def test_post_page_displays_replies(client, mocker, posts_list):
    """тест - на странице поста отображаются ответы на комментарии"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/0')
    assert response.status_code == 200
    for comment in posts_list[0]['comments']:
        if 'replies' in comment and comment['replies']:
            for reply in comment['replies']:
                assert reply['author'] in response.text
                assert reply['text'] in response.text


def test_nonexistent_post_returns_404(client, mocker, posts_list):
    """тест - при попытке получить доступ по несуществующему индексу возвращается 404"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/100')
    assert response.status_code == 404


def test_nonexistent_post_negative_index_returns_404(client, mocker, posts_list):
    """тест - отрицательный индекс поста возвращает 404"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts/-1')
    assert response.status_code == 404


def test_base_template_has_footer(client):
    """тест - базовый шаблон содержит подвал с ФИО и группой"""
    response = client.get('/')
    assert response.status_code == 200
    assert '<footer' in response.text
    assert 'Андреев Никита Денисович' in response.text
    assert '241-372' in response.text


def test_about_page_uses_correct_template(client):
    """тест - страница 'Об авторе' содержит ожидаемый контент"""
    response = client.get('/about')
    assert response.status_code == 200
    assert "Об авторе" in response.text
    assert "Дата рождения: 19.07.2006" in response.text


def test_index_page_uses_correct_template(client):
    """тест - главная страница содержит задание"""
    response = client.get('/')
    assert response.status_code == 200
    assert "Задание к лабораторной работе" in response.text
    assert "Доработайте прилагаемое к заданию веб-приложение" in response.text


def test_all_posts_have_unique_ids(client, mocker, posts_list):
    """тест - все посты имеют корректные индексы"""
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )

    response = client.get('/posts')
    assert response.status_code == 200
    assert len(posts_list) == 1
    for i in range(len(posts_list)):
        post_response = client.get(f'/posts/{i}')
        assert post_response.status_code == 200