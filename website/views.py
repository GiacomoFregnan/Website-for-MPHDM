

from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from . import db
from .models import User, Match  # Importa i modelli
import json

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():

    # Se lo stato NON è NULL (quindi è 0, 1, 2, 3, o 5), vai a 'state'
    if current_user.matching_status is not None:
        return redirect(url_for('views.state'))


    # Altrimenti (se è NULL), mostra il form
    if request.method == 'POST':
        university = request.form['university']
        current_status = request.form['current_status']
        field_of_study = request.form['field_of_study']
        participation_role = request.form['participation_role']
        time_commitment = request.form['time_commitment']
        communication = request.form['communication']

        improve_communication = request.form['Improve_communication_with_advisor_PI']
        help_writing_paper = request.form['Help_in_writing_a_paper_projects_preparing_presentations']
        maximize_conference_experience = request.form['Maximize_the_learning_experience_at_a_conference']
        help_choice_time_abroad = request.form['Help_with_the_choice_of_the_time_abroad']
        phd_work_balance = request.form['PhD_work_balance']
        phd_family_balance = request.form['PhD_family_balance']
        improve_soft_skills = request.form['Improve_your_soft_skills']
        help_academic_career = request.form['Help_with_academic_career']
        help_industrial_career = request.form['Help_with_industrial_career']
        talk_mental_wellbeing = request.form['Talk_about_mental_well_being']

        discovery = request.form['discovery']
        advice = request.form['advice']
        promotion_help = request.form['promotion_help']
        gdpr_consent = request.form['gdpr_consent']

        if len(university) < 5:
            flash("Please enter your university", "error")

        elif not gdpr_consent:
            flash("Please select your gdpr consent", "error")
        else:
            current_user.university = university
            current_user.current_status = current_status
            current_user.field_of_study = field_of_study
            current_user.participation_role = participation_role
            current_user.time_commitment = time_commitment
            current_user.communication = communication

            current_user.improve_communication = improve_communication
            current_user.help_writing_paper = help_writing_paper
            current_user.maximize_conference_experience = maximize_conference_experience
            current_user.help_choice_time_abroad = help_choice_time_abroad
            current_user.phd_work_balance = phd_work_balance
            current_user.phd_family_balance = phd_family_balance
            current_user.improve_soft_skills = improve_soft_skills
            current_user.talk_mental_wellbeing = talk_mental_wellbeing
            current_user.help_academic_career = help_academic_career
            current_user.help_industrial_career = help_industrial_career

            current_user.discovery = discovery
            current_user.advice = advice
            current_user.promotion_help = promotion_help

            # Imposta lo stato in base al ruolo
            if participation_role == "Mentor (only PhDs and PhD graduates)":
                current_user.matching_status = 1
            elif participation_role == "Mentee (only master students and PhDs)":
                current_user.matching_status = 2
            elif participation_role == "Mentor and Mentee (Only for PhDs)":
                current_user.matching_status = 3

            db.session.commit()
            flash('Informations updated!', category='success')
            return redirect(url_for('views.state'))

    return render_template("home.html", user=current_user)


@views.route('/state', methods=['GET', 'POST'])
@login_required
def state():
    # LOGICA DI VISUALIZZAZIONE UTENTE "SBLOCCATA"
    partner = None

    # L'utente vede il match SOLO se il suo stato è 0 (Approvato)
    if current_user.matching_status == 0:
        # Cerca se è un mentee in un match approvato
        match_come_mentee = Match.query.filter_by(
            mentee_id=current_user.id,
            status='Approved'
        ).first()

        # Cerca se è un mentore in un match approvato
        match_come_mentor = Match.query.filter_by(
            mentor_id=current_user.id,
            status='Approved'
        ).first()

        if match_come_mentee:
            partner = match_come_mentee.mentor
        elif match_come_mentor:
            partner = match_come_mentor.mentee

    # Se lo stato non è 0 (es. è 1, 2, 3, 5, o NULL),
    # 'partner' rimarrà None, e il template mostrerà "in attesa".
    return render_template("state.html", user=current_user, partner=partner)




@views.route('/profile')
@login_required
def profile():
    return render_template("profile.html", user=current_user)
