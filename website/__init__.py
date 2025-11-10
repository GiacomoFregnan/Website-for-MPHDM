# In website/__init__.py

from flask import Flask, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView

# Definisci le estensioni qui, senza app
db = SQLAlchemy()
DB_NAME = "database.db"
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    # Collega le estensioni all'app
    db.init_app(app)
    migrate.init_app(app, db)

    # Importa i blueprint
    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # Importa i modelli DOPO db.init_app
    from .models import User

    # Configura Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # --- Definisci le classi Admin DENTRO la factory ---

    class AdminModelView(ModelView):
        # Colonne da mostrare nella lista
        column_list = ('first_name', 'surname', 'email', 'is_admin')
        # Campi da escludere nei form
        form_excluded_columns = ('password',)
        # Campi ricercabili
        column_searchable_list = ('first_name', 'surname', 'email')
        # Filtri
        column_filters = ('is_admin', 'university')

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    class MyAdminIndexView(AdminIndexView):
        @expose('/')
        def index(self):
            # Calcola le statistiche
            try:
                totale_utenti = User.query.filter_by(is_admin=False).count()
                mentors = User.query.filter(User.participation_role.ilike('%Mentor%')).count()
                mentees = User.query.filter(User.participation_role.ilike('%Mentee%')).count()
                utenti_stem = User.query.filter(
                    User.field_of_study.ilike('%Physical Sciences%') |
                    User.field_of_study.ilike('%Life Sciences%')
                ).count()
                utenti_ssh = User.query.filter(
                    User.field_of_study.ilike('%Social Sciences%') |
                    User.field_of_study.ilike('%Humanities%')
                ).count()
            except Exception as e:
                totale_utenti = mentors = mentees = utenti_stem = utenti_ssh = 0
                flash(f"Errore nel caricamento statistiche: {e}", "error")

            # Passa i dati al template
            return self.render(
                'admin/custom_index.html',
                totale_utenti=totale_utenti,
                mentors=mentors,
                mentees=mentees,
                utenti_stem=utenti_stem,
                utenti_ssh=utenti_ssh
            )

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    # --- Inizializza Admin ---
    admin = Admin(
        app,
        name='Pannello Admin',
        template_mode='bootstrap4',
        index_view=MyAdminIndexView(name='Statistiche', url='/admin')
    )

    # Aggiungi le viste al pannello admin
    admin.add_view(AdminModelView(User, db.session))

    return app