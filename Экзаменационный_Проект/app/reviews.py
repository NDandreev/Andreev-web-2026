from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Review, Book, Status
from app.utils import sanitize_html

reviews_bp = Blueprint('reviews', __name__)


@reviews_bp.route('/add/<int:book_id>', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    book = Book.query.get_or_404(book_id)
    existing = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()
    if existing:
        flash('Вы уже оставили рецензию на эту книгу', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        text = request.form.get('text')
        if not rating or not text:
            flash('Заполните все поля', 'danger')
            return render_template('reviews/review_form.html', book=book)

        text = sanitize_html(text)
        status = Status.query.filter_by(name='на рассмотрении').first()
        if not status:
            flash('Статус "на рассмотрении" не найден', 'danger')
            return redirect(url_for('books.detail', book_id=book_id))

        review = Review(
            book_id=book_id,
            user_id=current_user.id,
            rating=rating,
            text=text,
            status_id=status.id
        )
        db.session.add(review)
        db.session.commit()
        flash('Рецензия отправлена на модерацию', 'success')
        return redirect(url_for('books.detail', book_id=book_id))

    return render_template('reviews/review_form.html', book=book)


@reviews_bp.route('/my')
@login_required
def my_reviews():
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('reviews/my_reviews.html', reviews=reviews)


@reviews_bp.route('/moderation')
@login_required
def moderation():
    if current_user.role.name not in ['moderator', 'admin']:
        flash('У вас нет прав доступа', 'danger')
        return redirect(url_for('books.index'))

    status_pending = Status.query.filter_by(name='на рассмотрении').first()
    if not status_pending:
        flash('Статус не найден', 'danger')
        return redirect(url_for('books.index'))

    page = request.args.get('page', 1, type=int)
    per_page = 10
    reviews = Review.query.filter_by(status_id=status_pending.id).order_by(
        Review.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('reviews/moderation.html', reviews=reviews)


@reviews_bp.route('/moderate/<int:review_id>')
@login_required
def moderate_review(review_id):
    if current_user.role.name not in ['moderator', 'admin']:
        flash('У вас нет прав', 'danger')
        return redirect(url_for('books.index'))

    review = Review.query.get_or_404(review_id)
    if review.status.name != 'на рассмотрении':
        flash('Эта рецензия уже была рассмотрена', 'warning')
        return redirect(url_for('reviews.moderation'))

    return render_template('reviews/review_moderate.html', review=review)


@reviews_bp.route('/approve/<int:review_id>', methods=['POST'])
@login_required
def approve_review(review_id):
    if current_user.role.name not in ['moderator', 'admin']:
        flash('Нет прав', 'danger')
        return redirect(url_for('books.index'))

    review = Review.query.get_or_404(review_id)
    if review.status.name != 'на рассмотрении':
        flash('Рецензия уже рассмотрена', 'warning')
        return redirect(url_for('reviews.moderation'))

    approved = Status.query.filter_by(name='одобрена').first()
    if not approved:
        flash('Статус "одобрена" не найден', 'danger')
        return redirect(url_for('reviews.moderation'))

    review.status_id = approved.id
    db.session.commit()
    flash('Рецензия одобрена', 'success')
    return redirect(url_for('reviews.moderation'))


@reviews_bp.route('/reject/<int:review_id>', methods=['POST'])
@login_required
def reject_review(review_id):
    if current_user.role.name not in ['moderator', 'admin']:
        flash('Нет прав', 'danger')
        return redirect(url_for('books.index'))

    review = Review.query.get_or_404(review_id)
    if review.status.name != 'на рассмотрении':
        flash('Рецензия уже рассмотрена', 'warning')
        return redirect(url_for('reviews.moderation'))

    rejected = Status.query.filter_by(name='отклонена').first()
    if not rejected:
        flash('Статус "отклонена" не найден', 'danger')
        return redirect(url_for('reviews.moderation'))

    review.status_id = rejected.id
    db.session.commit()
    flash('Рецензия отклонена', 'danger')
    return redirect(url_for('reviews.moderation'))