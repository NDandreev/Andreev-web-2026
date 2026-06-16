import os
import hashlib
import shutil
from app import create_app, db
from app.models import Role, User, Genre, Status, Book, Cover
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # --- 1. Создаём роли ---
    roles = [
        Role(name='admin', description='Предоставлен полный доступ к системе'),
        Role(name='moderator', description='Предоставлена возможность редактировать книги и модерировать рецензии'),
        Role(name='user', description='Предоставлена возможность оставлять рецензии')
    ]
    for role in roles:
        if not Role.query.filter_by(name=role.name).first():
            db.session.add(role)
    db.session.commit()

    # --- 2. Создаём администратора ---
    if not User.query.filter_by(login='admin').first():
        admin = User(
            login='admin',
            last_name='Администратор',
            first_name='Системный',
            role_id=Role.query.filter_by(name='admin').first().id
        )
        admin.set_password('admin123')
        db.session.add(admin)

    # --- 3. Создаём жанры (расширенный список) ---
    genres_list = [
        'Фантастика', 'Детектив', 'Роман', 'Поэзия',
        'Научная литература', 'Приключения', 'Триллер', 'Исторический роман',
        'Фэнтези', 'Классика', 'Научная фантастика', 'Ужасы', 'Мистика', 'Антиутопия'
    ]
    for genre_name in genres_list:
        if not Genre.query.filter_by(name=genre_name).first():
            db.session.add(Genre(name=genre_name))
    db.session.commit()

    # --- 4. Создаём статусы рецензий ---
    statuses = ['на рассмотрении', 'одобрена', 'отклонена']
    for status_name in statuses:
        if not Status.query.filter_by(name=status_name).first():
            db.session.add(Status(name=status_name))
    db.session.commit()

    # --- 5. Получаем объекты жанров для привязки ---
    genre_horror = Genre.query.filter_by(name='Ужасы').first()
    genre_mystic = Genre.query.filter_by(name='Мистика').first()
    genre_roman = Genre.query.filter_by(name='Роман').first()
    genre_classic = Genre.query.filter_by(name='Классика').first()
    genre_fantasy = Genre.query.filter_by(name='Фэнтези').first()
    genre_sci_fi = Genre.query.filter_by(name='Научная фантастика').first()
    genre_dystopia = Genre.query.filter_by(name='Антиутопия').first()

    # --- 6. Данные о книгах ---
    books_data = [
        {
            'title': 'Сияние',
            'author': 'Стивен Кинг',
            'year': 1977,
            'publisher': 'АСТ',
            'pages': 512,
            'description': 'Семья становится смотрителями отеля "Оверлук" в горах, где пробуждаются злые силы.',
            'genres': [genre_horror, genre_mystic]
        },
        {
            'title': 'Кэрри',
            'author': 'Стивен Кинг',
            'year': 1974,
            'publisher': 'АСТ',
            'pages': 320,
            'description': 'Скромная старшеклассница с телекинетическими способностями мстит своим мучителям.',
            'genres': [genre_horror, genre_mystic]
        },
        {
            'title': 'Мартин Иден',
            'author': 'Джек Лондон',
            'year': 1909,
            'publisher': 'Эксмо',
            'pages': 480,
            'description': 'История молодого моряка, который через самообразование пытается стать писателем.',
            'genres': [genre_roman, genre_classic]
        },
        {
            'title': 'Мастер и Маргарита',
            'author': 'Михаил Булгаков',
            'year': 1966,
            'publisher': 'Художественная литература',
            'pages': 480,
            'description': 'Великий роман о любви, дьяволе и свободе творчества.',
            'genres': [genre_roman, genre_fantasy, genre_classic]
        },
        {
            'title': 'Великий Гэтсби',
            'author': 'Фрэнсис Скотт Фицджеральд',
            'year': 1925,
            'publisher': 'АСТ',
            'pages': 256,
            'description': 'История таинственного миллионера и его любви к прекрасной девушке.',
            'genres': [genre_roman, genre_classic]
        },
        {
            'title': 'Портрет Дориана Грея',
            'author': 'Оскар Уайльд',
            'year': 1890,
            'publisher': 'Эксмо',
            'pages': 304,
            'description': 'Молодой человек продаёт душу за вечную молодость и красоту.',
            'genres': [genre_roman, genre_classic]
        },
        {
            'title': '1984',
            'author': 'Джордж Оруэлл',
            'year': 1949,
            'publisher': 'АСТ',
            'pages': 320,
            'description': 'Антиутопия о тоталитарном обществе и уничтожении личности.',
            'genres': [genre_sci_fi, genre_dystopia]
        },
        {
            'title': 'Оно',
            'author': 'Стивен Кинг',
            'year': 1986,
            'publisher': 'АСТ',
            'pages': 1168,
            'description': 'Зловещее существо, принимающее облик клоуна Пеннивайза, терроризирует город Дерри.',
            'genres': [genre_horror, genre_mystic]
        }
    ]

    # --- 7. Добавляем книги (если их ещё нет) ---
    for data in books_data:
        existing = Book.query.filter_by(title=data['title'], author=data['author']).first()
        if not existing:
            book = Book(
                title=data['title'],
                author=data['author'],
                year=data['year'],
                publisher=data['publisher'],
                pages=data['pages'],
                description=data['description']
            )
            db.session.add(book)
            db.session.flush()
            for genre in data['genres']:
                if genre:
                    book.genres.append(genre)
    db.session.commit()

    # --- 8. АВТОМАТИЧЕСКАЯ ПРИВЯЗКА ОБЛОЖЕК ---
    cover_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
    # Убедимся, что папка существует
    os.makedirs(cover_folder, exist_ok=True)

    # Разрешённые расширения
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

    all_books = Book.query.all()
    for book in all_books:
        if book.cover:
            continue  # у книги уже есть обложка

        # Формируем базовое имя для поиска
        base_name_ru = book.title.lower().replace(' ', '_')
        found = None
        for filename in os.listdir(cover_folder):
            name, ext = os.path.splitext(filename)
            if ext.lower() not in allowed_extensions:
                continue
            # Сравниваем имя файла (без расширения) с базовым именем книги (игнорируя регистр)
            if name.lower() == base_name_ru:
                found = filename
                break

        if found:
            source_path = os.path.join(cover_folder, found)
            # Генерируем новое имя на основе MD5-хеша содержимого
            with open(source_path, 'rb') as f:
                file_data = f.read()
            md5_hash = hashlib.md5(file_data).hexdigest()
            ext = os.path.splitext(found)[1].lower()
            # Имя: cover_{book_id}_{md5[:8]}{ext}
            new_filename = f"cover_{book.id}_{md5_hash[:8]}{ext}"
            new_path = os.path.join(cover_folder, new_filename)

            # Копируем файл с новым именем (если ещё не существует)
            if not os.path.exists(new_path):
                shutil.copy2(source_path, new_path)
                print(f"📁 Скопирован файл: {found} -> {new_filename}")

            # Определяем mime_type
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_map.get(ext, 'application/octet-stream')

            # Создаём запись в Cover
            cover = Cover(
                filename=new_filename,
                mime_type=mime_type,
                md5_hash=md5_hash,
                book_id=book.id
            )
            db.session.add(cover)
            print(f"✅ Обложка привязана к книге «{book.title}»: {new_filename}")

    db.session.commit()

    print("\n" + "="*50)
    print("✅ База данных инициализирована!")
    print(f"📚 Добавлено книг: {len(books_data)}")
    print("👤 Админ: login='admin', password='admin123'")
    print("📁 Обложки сохранены в папке static/uploads/covers/")
    print("="*50)