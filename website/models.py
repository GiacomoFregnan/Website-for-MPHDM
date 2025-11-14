

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
    participation_role = db.Column(db.String(150))
    time_commitment = db.Column(db.String(150))
    communication = db.Column(db.String(150))

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

    # COLONNA MATCHING_STATUS
    # 0 -> Correctly matched (e approvato dall'admin)
    # 1 -> Requires an assignment as Mentor
    # 2 -> Requires an assignment as Mentee
    # 3 -> Requires an assignment as both
    # 5 -> Matched, Pending Admin Approval
    # NULL (default) -> Form non compilato
    matching_status = db.Column(db.Integer, default=None, nullable=True)


#TABELLA MATC
class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # COLONNA PER L'APPROVAZIONE
    # Stati: 'Pending', 'Approved'
    status = db.Column(db.String(50), default='Pending', nullable=False)

    mentor = db.relationship('User', foreign_keys=[mentor_id], backref='mentoring_matches')
    mentee = db.relationship('User', foreign_keys=[mentee_id], backref='mentee_match')