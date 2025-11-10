from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func








class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    surname = db.Column(db.String(150))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    university = db.Column(db.String(150))
    current_status = db.Column(db.String(150))
    field_of_study = db.Column(db.String(150))
    participation_role =db.Column(db.String(150))
    time_commitment =db.Column(db.String(150))
    communication =db.Column(db.String(150))

    improve_communication = db.Column(db.String(150))
    help_writing_paper = db.Column(db.String(150))
    maximize_conference_experience = db.Column(db.String(150))
    help_choice_time_abroad = db.Column(db.String(150))
    phd_work_balance = db.Column(db.String(150))
    phd_family_balance = db.Column(db.String(150))
    improve_soft_skills = db.Column(db.String(150))
    help_academic_career = db.Column(db.String(150))
    help_industrial_career = db.Column(db.String(150))
    talk_mental_wellbeing = db.Column(db.String(150))

    discovery = db.Column(db.String(150))
    advice = db.Column(db.String(150))
    promotion_help = db.Column(db.String(150))




