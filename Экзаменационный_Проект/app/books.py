from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
import os
import hashlib
from app import db
from app.models import Book, Genre, Review, Cover, Status

books_bp = Blueprint('books', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_cover(file, book_id):
    if not file or not allowed_file(file.filename):
        return None

    file_data = file.read()
    md5_hash = hashlib.md5(file_data).hexdigest()

    existing = Cover.query.filter_by(md5_hash=md5_hash).first()
    if existing:
        existing.book_id = book_id
        db.session.commit()
        return existing.filename

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"cover_{book_id}_{md5_hash[:8]}.{ext}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    with open(filepath, 'wb') as f:
        f.write(file_data)

    cover = Cover(filename=filename, mime_type=file.mimetype, md5_hash=md5_hash, book_id=book_id)
    db.session.add(cover)
    db.session.commit()
    return filename


@books_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['BOOKS_PER_PAGE']
    books = Book.query.order_by(Book.year.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('books/index.html', books=books)


@books_bp.route('/book/<int:book_id>')
def detail(book_id):
    book = Book.query.get_or_404(book_id)

    # только одобренные рецензии
    approved_status = Status.query.filter_by(name='одобрена').first()
    approved_reviews = []
    if approved_status:
        approved_reviews = Review.query.filter_by(
            book_id=book_id, status_id=approved_status.id
        ).order_by(Review.created_at.desc()).all()

    # проверка, оставлял ли пользователь рецензию
    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()

    from app.utils import md_to_html
    book.description_html = md_to_html(book.description)

    return render_template(
        'books/detail.html',
        book=book,
        approved_reviews=approved_reviews,
        user_review=user_review
    )


@books_bp.route('/book/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав', 'danger')
        return redirect(url_for('books.index'))

    genres = Genre.query.order_by(Genre.name).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        year = request.form.get('year')
        publisher = request.form.get('publisher')
        author = request.form.get('author')
        pages = request.form.get('pages')
        genre_ids = request.form.getlist('genres')
        cover_file = request.files.get('cover')

        from app.utils import sanitize_html
        description = sanitize_html(description)

        book = Book(title=title, description=description, year=year, publisher=publisher, author=author, pages=pages)
        db.session.add(book)
        db.session.flush()

        for genre_id in genre_ids:
            genre = Genre.query.get(genre_id)
            if genre:
                book.genres.append(genre)

        db.session.commit()

        if cover_file and allowed_file(cover_file.filename):
            save_cover(cover_file, book.id)

        flash('Книга успешно добавлена', 'success')
        return redirect(url_for('books.detail', book_id=book.id))

    return render_template('books/form.html', book=None, genres=genres, is_edit=False)


@books_bp.route('/book/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав', 'danger')
        return redirect(url_for('books.index'))

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Книга успешно удалена', 'success')
    return redirect(url_for('books.index'))