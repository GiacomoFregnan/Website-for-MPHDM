# In website/__init__.py
# (Versione semplice, senza approvazione)

from flask import Flask, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
import os
from . import matching_logic

db = SQLAlchemy()
DB_NAME = "database.db"
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    db.init_app(app)
    migrate.init_app(app, db)

    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Match

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    class UserAdminView(ModelView):
        column_list = ('first_name', 'surname', 'email', 'is_admin', 'matching_status')
        form_excluded_columns = ('password',)
        column_searchable_list = ('first_name', 'surname', 'email')
        column_filters = ('is_admin', 'university', 'matching_status')

        def is_accessible(self): return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs): return redirect(url_for('auth.login', next=request.url))

    class MyAdminIndexView(AdminIndexView):
        @expose('/')
        def index(self):
            try:
                totale_utenti = User.query.filter_by(is_admin=False).count()
                mentors = User.query.filter(User.participation_role.ilike('%Mentor%')).count()
                mentees = User.query.filter(User.participation_role.ilike('%Mentee%')).count()
                utenti_da_matchare = User.query.filter(User.matching_status.in_([1, 2, 3])).count()
                utenti_matchati = User.query.filter_by(matching_status=0).count()

            except Exception as e:
                totale_utenti = mentors = mentees = utenti_da_matchare = utenti_matchati = 0
                flash(f"Errore nel caricamento statistiche: {e}", "error")

            return self.render(
                'admin/custom_index.html',
                totale_utenti=totale_utenti,
                mentors=mentors,
                mentees=mentees,
                utenti_da_matchare=utenti_da_matchare,
                utenti_matchati=utenti_matchati
            )

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    # --- VISTA PER IL MATCHING (Versione semplice) ---
    class MatchingView(BaseView):
        @expose('/')
        def index(self):
            # Carica tutti i match e li passa al template
            all_matches = Match.query.all()
            return self.render(
                'admin/matching.html',
                all_matches=all_matches
            )

        @expose('/run-matching', methods=['POST'])
        def run_matching(self):
            try:
                # 1. Trova utenti 1, 2, 3
                utenti_da_matchare = User.query.filter(
                    User.matching_status.in_([1, 2, 3]),
                    User.is_admin == False
                ).all()

                if not utenti_da_matchare:
                    flash("Nessun utente in attesa di matching (Stato 1, 2, o 3).", "warning")
                    return redirect(url_for('matching.index'))

                weights_path = os.path.join(app.root_path, '..', 'config', 'weights.json')

                if not os.path.exists(weights_path):
                    flash(f"Errore: file dei pesi non trovato in {weights_path}", "error")
                    return redirect(url_for('matching.index'))

                # 2. Esegui algoritmo
                row_ind, col_ind, people, M = matching_logic.esegui_matching_da_db(
                    utenti_da_matchare,
                    weights_path
                )

                if people is None:
                    flash("Algoritmo avviato, ma non ci sono abbastanza mentori o mentee per un matching.", "info")
                    return redirect(url_for('matching.index'))

                # 3. Aggiorna DB
                match_creati = 0
                id_utenti_matchati = set()

                for e, o in zip(row_ind, col_ind):
                    if M[e][o] > -1:
                        mentee = people["mentee"][e]
                        mentor = people["mentor"][o]

                        # Crea il Match
                        nuovo_match = Match(mentor_id=mentor['id'], mentee_id=mentee['id'])
                        db.session.add(nuovo_match)

                        id_utenti_matchati.add(mentor['id'])
                        id_utenti_matchati.add(mentee['id'])
                        match_creati += 1

                if match_creati == 0:
                    flash("Algoritmo eseguito, ma nessun match valido trovato (punteggio > -1).", "info")
                    return redirect(url_for('matching.index'))

                # Imposta lo stato degli utenti direttamente a 0
                User.query.filter(
                    User.id.in_(id_utenti_matchati)
                ).update(
                    {User.matching_status: 0},
                    synchronize_session=False
                )

                db.session.commit()
                flash(f'Matching completato! Creati {match_creati} nuovi match.', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Errore critico durante il matching: {e}', 'error')

            return redirect(url_for('matching.index'))

        # --- PULSANTE DI RESET (Opzionale ma utile per i test) ---
        @expose('/reset-matches', methods=['POST'])
        def reset_all_matches(self):
            try:
                # 1. Resetta gli utenti da 0 a 1, 2, 3
                users_to_reset = User.query.filter(User.matching_status == 0).all()
                for user in users_to_reset:
                    self.reset_user_status(user)

                # 2. Cancella tutti i match
                num_matches_deleted = db.session.query(Match).delete()
                db.session.commit()
                flash(
                    f"Reset completato! {len(users_to_reset)} utenti reimpostati, {num_matches_deleted} match cancellati.",
                    "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Errore reset: {e}", "error")
            return redirect(url_for('matching.index'))

        def reset_user_status(self, user):
            if not user: return
            role = user.participation_role.strip() if user.participation_role else ""
            if role == "Mentor (only PhDs and PhD graduates)":
                user.matching_status = 1
            elif role == "Mentee (only master students and PhDs)":
                user.matching_status = 2
            elif role == "Mentor and Mentee (Only for PhDs)":
                user.matching_status = 3
            else:
                user.matching_status = None  # Usa NULL
            db.session.add(user)  # Aggiungi alla sessione

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    # --- FINE VISTA MATCHING ---

    admin = Admin(
        app,
        name='Pannello Admin',
        template_mode='bootstrap4',
        index_view=MyAdminIndexView(name='Statistiche', url='/admin')
    )

    admin.add_view(UserAdminView(User, db.session, name="Users"))
    admin.add_view(MatchingView(name='Matching', endpoint='matching'))
    admin.add_link(MenuLink(name='Torna al Sito', category='', url='/'))

    return app