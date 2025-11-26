# In website/auth.py

from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Match  # <-- Importa Match
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  ##means from __init__.py import db
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        # Applica .capitalize() prima di salvarli
        first_name = request.form.get('firstName').capitalize()
        surname = request.form.get('surname').capitalize()


        password1 = request.form.get('password1')
        password2 = request.form.get('password2')


        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif len(surname) < 2:
            flash('Surname must be greater than 1 character.', category='error')


        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:  # <-- L'errore era qui
            flash('Password must be at least 7 characters.', category='error')


        else:
            new_user = User(email=email, first_name=first_name, surname=surname, password=generate_password_hash(
                password1, method="pbkdf2:sha256"))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)


# ROTTA PER ELIMINARE L'ACCOUNT
@auth.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        #Trova e cancella tutti i match in cui l'utente è mentee
        matches_as_mentee = Match.query.filter_by(mentee_id=current_user.id).all()
        for match in matches_as_mentee:
            # Resetta il partner se il match era 'Approved' O 'Pending'
            if (match.status == 'Approved' or match.status == 'Pending') and match.mentor:
                reset_user_status(match.mentor)
            db.session.delete(match)

        #Trova e cancella tutti i match in cui l'utente è mentor
        matches_as_mentor = Match.query.filter_by(mentor_id=current_user.id).all()
        for match in matches_as_mentor:
            # Resetta il partner se il match era 'Approved' O 'Pending'
            if (match.status == 'Approved' or match.status == 'Pending') and match.mentee:
                reset_user_status(match.mentee)
            db.session.delete(match)

        #Ora che i match sono stati rimossi, cancella l'utente
        user_to_delete = User.query.get(current_user.id)
        db.session.delete(user_to_delete)

        #Fai il logout e salva le modifiche
        logout_user()
        db.session.commit()

        flash('Il tuo account è stato eliminato con successo.', category='success')
        return redirect(url_for('auth.login'))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione dell\'account: {e}', category='error')
        return redirect(url_for('views.home'))


# Funzione helper per rimettere in gioco un utente
def reset_user_status(user):
    if not user:
        return

    role = user.participation_role.strip() if user.participation_role else ""

    if role == "Mentor (only PhDs and PhD graduates)":
        user.matching_status = 1
    elif role == "Mentee (only master students and PhDs)":
        user.matching_status = 2
    elif role == "Mentor and Mentee (Only for PhDs)":
        user.matching_status = 3
    else:
        user.matching_status = None  # Default (form non compilato)

    db.session.add(user)
