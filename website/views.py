from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from . import db
import json

views = Blueprint('views', __name__)




@views.route('/', methods=['GET', 'POST'])
@login_required
def home():

    if current_user.university:
        return redirect(url_for('views.state'))


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
        elif not current_status:
            flash("Please select your current status", "error")
        elif not field_of_study:
            flash("Please select your field of study", "error")
        elif not participation_role:
            flash("Please select your participation role", "error")
        elif not time_commitment:
            flash("Please select your time commitment", "error")
        elif not communication:
            flash("Please select your communication", "error")
        elif not improve_communication:
            flash("Please select your improve communication", "error")
        elif not help_writing_paper:
            flash("Please select your help writing paper", "error")
        elif not maximize_conference_experience:
            flash("Please select your maximize conference experience", "error")
        elif not help_choice_time_abroad:
            flash("Please select your help choice time abroad", "error")
        elif not phd_work_balance:
            flash("Please select your phd work balance", "error")
        elif not phd_family_balance:
            flash("Please select your phd family balance", "error")
        elif not improve_soft_skills:
            flash("Please select your improve soft skills", "error")
        elif not talk_mental_wellbeing:
            flash("Please select your talk about mental well-being", "error")
        elif not help_academic_career:
            flash("Please select your help academic career", "error")
        elif not help_industrial_career:
            flash("Please select your help industrial career", "error")
        elif not discovery:
            flash("Please select how dis you discovered us", "error")
        elif not promotion_help:
            flash("Please select if you want promotion", "error")
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



            db.session.commit()
            flash('Informations updated!', category='success')
            return redirect(url_for('views.state'))

    return render_template("home.html", user=current_user)


@views.route('/state', methods=['GET', 'POST'])
@login_required
def state():
    return render_template("state.html", user=current_user)
