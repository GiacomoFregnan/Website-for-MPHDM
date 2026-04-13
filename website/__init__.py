from flask import Flask, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
import os
from dotenv import load_dotenv
from . import matching_logic
from sqlalchemy import func, not_
from flask_mail import Mail, Message
import json

load_dotenv()
db = SQLAlchemy()
DB_NAME = "database.db"
migrate = Migrate()
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

    mail.init_app(app)

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


        # Impedisce all'admin di eliminare utenti per evitare record orfani nei Match
        can_delete = False

        # Impedisce la modifica manuale dei dati sensibili degli utenti dal pannello
        can_edit = False

        # Opzionale: impedisce la creazione manuale di utenti (devono passare per il Sign Up)
        can_create = False

        def is_accessible(self): return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs): return redirect(url_for('auth.login', next=request.url))

    # CLASSE PER LA TABELLA MATCH
    class MatchAdminView(ModelView):
        # Mostra i nomi leggibili usando le relazioni del modello
        column_list = ('mentee.first_name', 'mentee.surname', 'mentor.first_name', 'mentor.surname', 'status')

        # Permette di modificare lo stato direttamente dalla lista
        column_editable_list = ('status',)

        # Aggiunge un filtro per lo stato
        column_filters = ('status',)

        # Rendi le FK ricercabili (es. per email)
        column_searchable_list = ('mentee.email', 'mentor.email', 'mentee.first_name', 'mentor.first_name')


        can_delete = False  # Forza l'admin a usare la tua funzione "Rifiuta" in Gestione Matching
        can_edit = False    # Solo l'algoritmo dovrebbe modificare i Match
        can_create = False  # Solo l'algoritmo dovrebbe creare i Match


        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    # CLASSE PER I CONSIGLI
    class AdviceView(BaseView):
        @expose('/')
        def index(self):
            # Trova tutti gli utenti che hanno lasciato un consiglio
            all_advice = User.query.filter(
                not_(User.advice.is_(None)),  # Non è NULL
                User.advice != ''  # Non è una stringa vuota
            ).all()

            return self.render('admin/advice.html', all_advice=all_advice)

        # ELIMINAZIONE CONSIGLIO
        @expose('/delete/<int:user_id>')
        def delete_advice(self, user_id):
                user = User.query.get_or_404(user_id)
                user.advice = None  # Cancella il testo del consiglio
                db.session.commit()
                flash('Consiglio rimosso con successo!', category='success')
                return redirect(url_for('advice.index'))

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))



    class MyAdminIndexView(AdminIndexView):
        @expose('/')
        def index(self):
            try:
                totale_utenti = User.query.filter_by(is_admin=False).count()
                mentors = User.query.filter(User.participation_role.ilike('%Mentor%')).count()
                mentees = User.query.filter(User.participation_role.ilike('%Mentee%')).count()
                utenti_da_matchare = User.query.filter(User.matching_status.in_([1, 2, 3])).count()
                utenti_matchati = User.query.filter_by(matching_status=0).count()
                utenti_in_attesa_approvazione = User.query.filter_by(matching_status=5).count()

                discovery_stats = db.session.query(
                    User.discovery,
                    func.count(User.discovery)
                ).filter(User.is_admin == False).group_by(User.discovery).all()

            except Exception as e:
                totale_utenti = mentors = mentees = utenti_da_matchare = utenti_matchati = utenti_in_attesa_approvazione = 0
                discovery_stats = []
                flash(f"Errore nel caricamento statistiche: {e}", "error")

            return self.render(
                'admin/custom_index.html',
                totale_utenti=totale_utenti,
                mentors=mentors,
                mentees=mentees,
                utenti_da_matchare=utenti_da_matchare,
                utenti_matchati=utenti_matchati,
                utenti_in_attesa_approvazione=utenti_in_attesa_approvazione,
                discovery_stats=discovery_stats
            )

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))

    # VISTA PER IL MATCHING (CON FLUSSO APPROVAZIONE)
    class MatchingView(BaseView):
        @expose('/')
        def index(self):
            # Carica match in sospeso e approvati
            pending_matches = Match.query.filter_by(status='Pending').all()
            approved_matches = Match.query.filter_by(status='Approved').all()

            return self.render(
                'admin/matching.html',
                pending_matches=pending_matches,
                approved_matches=approved_matches
            )

        @expose('/run-matching', methods=['POST'])
        def run_matching(self):
            try:
                # 1. Trova utenti 1, 2, 3
                utenti_da_matchare = User.query.filter(
                    User.matching_status.in_([1, 2, 3])
                ).all()

                if not utenti_da_matchare:
                    flash("Nessun utente in attesa di matching (Stato 1, 2, o 3).", "warning")
                    return redirect(url_for('matching.index'))

                weights_path = os.path.join(app.root_path, '..', 'config', 'weights.json')

                if not os.path.exists(weights_path):
                    flash(f"Errore: file dei pesi non trovato in {weights_path}", "error")
                    return redirect(url_for('matching.index'))

                # esecuszione algoritmo versione col cerotto int()
                row_ind, col_ind, people, M = matching_logic.esegui_matching_da_db(
                    utenti_da_matchare,
                    weights_path
                )

                if people is None:
                    flash("Algoritmo avviato, ma non ci sono abbastanza mentori o mentee per un matching.", "info")
                    return redirect(url_for('matching.index'))

                # aggiorno DB
                match_creati = 0
                id_utenti_in_sospeso = set()

                for e, o in zip(row_ind, col_ind):
                    if M[e][o] > -1:
                        mentee = people["mentee"][e]
                        mentor = people["mentor"][o]

                        # Crea il Match come 'Pending'
                        nuovo_match = Match(mentor_id=mentor['id'], mentee_id=mentee['id'], status='Pending')
                        db.session.add(nuovo_match)

                        # Aggiunnta degli ID degli utenti da impostare a 5
                        id_utenti_in_sospeso.add(mentor['id'])
                        id_utenti_in_sospeso.add(mentee['id'])
                        match_creati += 1

                if match_creati == 0:
                    flash("Algoritmo eseguito, ma nessun match valido trovato (punteggio > -1).", "info")
                    return redirect(url_for('matching.index'))

                # Impostazione dello stato degli utenti a 5 (Pending Approval)
                User.query.filter(
                    User.id.in_(id_utenti_in_sospeso)
                ).update(
                    {User.matching_status: 5},
                    synchronize_session=False
                )

                db.session.commit()
                flash(f'Matching completato! Creati {match_creati} nuovi match. Sono in attesa di approvazione.',
                      'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Errore critico durante il matching: {e}', 'error')

            return redirect(url_for('matching.index'))

        # ROTTA PER APPROVARE
        @expose('/approve/<int:match_id>')
        def approve_match(self, match_id):
            match = Match.query.get_or_404(match_id)
            if match.status == 'Pending':
                match.status = 'Approved'

                # Imposta gli utenti a '0' (Completato)
                if match.mentor: match.mentor.matching_status = 0
                if match.mentee: match.mentee.matching_status = 0

                #RICHIAMO LA FUNZIONE DELLE EMAIL
                self.send_matching_emails(match)


                db.session.commit()
                flash(f"Match tra {match.mentor.first_name} e {match.mentee.first_name} approvato.", "success")
            else:
                flash("Match già processato.", "warning")
            return redirect(url_for('matching.index'))

        # ROTTA PER RIFIUTARE
        @expose('/reject/<int:match_id>')
        def reject_match(self, match_id):
            match = Match.query.get_or_404(match_id)
            if match.status == 'Pending':

                # Rimettiamo gli utenti "in gioco"
                self.reset_user_status(match.mentor)
                self.reset_user_status(match.mentee)

                db.session.delete(match)
                db.session.commit()
                flash(f"Match tra {match.mentor.first_name} e {match.mentee.first_name} rifiutato.", "danger")
            else:
                flash("Match già processato.", "warning")
            return redirect(url_for('matching.index'))

        # FUNZIONE PER COMPOSIZIONE E INVIO MAIL
        def send_matching_emails(self, match):
            # Email per il Mentee
            msg_mentee = Message(
                "Il tuo Match è stato approvato! - MyPhDMentor",
                recipients=[match.mentee.email]
            )
            msg_mentee.body = f"""Ciao {match.mentee.first_name.capitalize()},
abbiamo una splendida notizia! Il tuo match è stato approvato.
Il tuo Mentor è {match.mentor.first_name.capitalize()} {match.mentor.surname.capitalize()}.

Puoi contattare il tuo Mentor all'indirizzo email: {match.mentor.email}

Buon percorso di mentoring!
Il team di MyPhDMentor"""

            # Email per il Mentor
            msg_mentor = Message(
                "Nuovo Mentee assegnato! - MyPhDMentor",
                recipients=[match.mentor.email]
            )
            msg_mentor.body = f"""Ciao {match.mentor.first_name.capitalize()},
il sistema di matching ha confermato la tua assegnazione.
Il tuo Mentee è {match.mentee.first_name.capitalize()} {match.mentee.surname.capitalize()}.
            
Puoi contattare il tuo Mentee all'indirizzo email: {match.mentee.email}
            
Grazie per la tua disponibilità e buon lavoro!
Il team di MyPhDMentor"""

            try:
                mail.send(msg_mentee)
                mail.send(msg_mentor)
            except Exception as e:
                # Se l'invio fallisce, lo stampiamo nel terminale per fare debug
                print(f"Errore critico nell'invio delle email: {e}")


        # Funzione helper per resettare lo stato utente
        def reset_user_status(self, user):
            if not user:
                return

            # Pulisci il ruolo per sicurezza
            role = user.participation_role.strip() if user.participation_role else ""

            if role == "Mentor (only PhDs and PhD graduates)":
                user.matching_status = 1
            elif role == "Mentee (only master students and PhDs)":
                user.matching_status = 2
            elif role == "Mentor and Mentee (Only for PhDs)":
                user.matching_status = 3
            else:
                user.matching_status = None  # Default è NULL (form non compilato)

            db.session.add(user)  # Aggiungi alla sessione per il commit

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))


    # VISTA PER LA CONFIGURAZIONE DEI PESI (WEIGHTS.JSON)
    class AlgorithmConfigView(BaseView):
        @expose('/')
        def index(self):
            # Cerca il file weights.json nella cartella config
            weights_path = os.path.join(app.root_path, '..', 'config', 'weights.json')
            try:
                with open(weights_path, 'r') as f:
                    weights = json.load(f)
            except Exception as e:
                weights = {}
                flash(f"Errore nella lettura del file weights.json: {e}", "error")

            return self.render('admin/weights.html', weights=weights)

        @expose('/update', methods=['POST'])
        def update_weights(self):
            weights_path = os.path.join(app.root_path, '..', 'config', 'weights.json')
            try:
                # Recupera i dati dal form e convertili in float (numeri decimali)
                new_weights = {
                    "availability_time": float(request.form.get('availability_time', 1.0)),
                    "availability_medium": float(request.form.get('availability_medium', 0.5)),
                    "questions": [
                        float(request.form.get(f'q{i}', 1.0)) for i in range(10)
                    ]
                }

                # Sovrascrive il file JSON con i nuovi dati
                with open(weights_path, 'w') as f:
                    json.dump(new_weights, f, indent=4)

                flash("Pesi dell'algoritmo aggiornati con successo!", "success")
            except ValueError:
                flash("Errore: Inserisci solo valori numerici validi (usa il punto per i decimali).", "error")
            except Exception as e:
                flash(f"Errore critico durante il salvataggio: {e}", "error")

            return redirect(url_for('config.index'))

        def is_accessible(self):
            return current_user.is_authenticated and current_user.is_admin

        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login', next=request.url))




    admin = Admin(
        app,
        name='Pannello Admin',
        template_mode='bootstrap4',
        index_view=MyAdminIndexView(name='Statistiche', url='/admin')
    )

    # Aggiungi le viste al pannello admin
    admin.add_view(UserAdminView(User, db.session, name="Users"))
    admin.add_view(MatchAdminView(Match, db.session, name="Matches"))
    admin.add_view(MatchingView(name='Matching', endpoint='matching'))
    admin.add_view(AdviceView(name='Consigli Utenti', endpoint='advice'))
    admin.add_view(AlgorithmConfigView(name='Tuning Algoritmo', endpoint='config'))

    admin.add_link(MenuLink(name='Torna al Sito', category='', url='/'))

    return app