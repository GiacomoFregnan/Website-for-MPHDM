

import numpy as np
import json
import os
from scipy.spatial.distance import cosine
from scipy.optimize import linear_sum_assignment
from itertools import product
import unicodedata


# Funzione di pulizia
def clean_string(s):
    if not s:
        return ""
    s = s.replace(u'\xa0', u' ')
    s = unicodedata.normalize('NFKC', s)
    return s.strip()


# Costanti
FIELDS = [
    "Physical Sciences and Engineering (Physics, Mathematics, Chemistry etc)",
    "Life Sciences (Biochemistry, Biology, Pharmaceutical Sciences, Medicine etc)",
    "Social Sciences (Law, Economics, Psychology etc)",
    "Humanities (Literature, History, Philosophy etc)",
    "Design and architecture"
]
LEVELS = {
    'Master student': "m", 'A PhD Student in the first year': "p1",
    'A PhD Student in the second year': "p2", 'A PhD student at least in the third year': "p3",
    'A master student': "m", 'A PhD Student': "p",
    'A PhD graduate (Post-doc or working in the private sector)': "d",
    'A PhD graduate (Post-doc or working in the private sector), with 3+ years of expertise': "d",
    'A PhD graduate (Post-doc or working in the private sector) (Post-doc or working in the private sector)': "d",
    'A PhD graduate (Post-doc or working in the private sector), with less than three years of expertise': "d"
}
PAIRS = [
    ("m", "p"), ("m", "p1"), ("m", "p2"), ("m", "p3"), ("m", "d"),
    ("p", "p"), ("p", "p2"), ("p", "p3"), ("p", "d"),
    ("p1", "p"), ("p1", "p3"), ("p1", "d"),
    ("p2", "d"), ("p3", "d")
]


# Funzioni Helper
def onehot(valuestring, values):
    vector = [0] * len(values)
    valuestring_clean = clean_string(valuestring)
    if valuestring_clean:
        for item in valuestring_clean.split(", "):
            if item in values:
                vector[values.index(item)] = 1
    return vector


def scalar(valuestring, values):
    valuestring_clean = clean_string(valuestring)
    if valuestring_clean in values:
        return values.index(valuestring_clean)
    return 0


def similarity(mentor, mentee, weightvector):
    if mentor["email"] == mentee["email"]: return -1.0
    mentee_level_clean = clean_string(mentee['level'])
    mentor_level_clean = clean_string(mentor['level'])
    mentee_level_code = LEVELS.get(mentee_level_clean)
    mentor_level_code = LEVELS.get(mentor_level_clean)
    if not mentee_level_code or not mentor_level_code: return -1.0
    if not (mentee_level_code, mentor_level_code) in PAIRS: return -1.0
    return 1 - cosine(mentor["features"], mentee["features"], weightvector)


def readWeightVector(weights_path):
    with open(weights_path) as f:
        weights = json.load(f)
    weightlist = [weights["availability_time"]]
    weightlist.extend([weights["availability_medium"] for i in range(5)])
    weightlist.extend(weights["questions"])
    return np.array(weightlist)


# Funzione Principale (CON IL CEROTTO)
def esegui_matching_da_db(utenti_da_matchare, weights_path):
    print("\n--- AVVIO LOGICA DI MATCHING (CON CONVERSIONE INT FORZATA) ---")

    people = {"mentor": [], "mentee": []}

    for user in utenti_da_matchare:

        # CEROTTO
        try:
            # Forza la conversione in Intero
            # Gestisce sia '1' (stringa) che NULL (None)
            status = int(user.matching_status)
        except (ValueError, TypeError):
            print(f"User {user.id} SKIPPATO (matching_status non valido: {user.matching_status})")
            continue


        level = clean_string(user.current_status)
        field = clean_string(user.field_of_study)
        time_comm = clean_string(user.time_commitment)
        comm_pref = clean_string(user.communication)

        if not all([level, field, time_comm, comm_pref]):
            print(f"User {user.id} SKIPPATO (dati form incompleti)")
            continue

        is_mentee = False
        if status in [2, 3]:  # 2=Mentee, 3=Entrambi
            is_mentee = True

        is_mentor = False
        if status in [1, 3]:  # 1=Mentor, 3=Entrambi
            is_mentor = True



        if is_mentor or is_mentee:
            # Codice per creare 'person'
            availability_time = scalar(time_comm, ["1 to 3 hours", "3 to 5 hours", "more than 5 hours"])
            availability_medium = onehot(comm_pref, ["Through phone calls", "Through face to face meetings",
                                                     "Through social media", "Through video calls", "Through emails"])
            interests = [
                int(user.improve_communication or 1),
                int(user.help_writing_paper or 1),
                int(user.maximize_conference_experience or 1),
                int(user.help_choice_time_abroad or 1),
                int(user.phd_work_balance or 1),
                int(user.phd_family_balance or 1),
                int(user.improve_soft_skills or 1),
                int(user.help_academic_career or 1),
                int(user.help_industrial_career or 1),
                int(user.talk_mental_wellbeing or 1)
            ]
            try:
                interests.append(FIELDS.index(field))
            except ValueError:
                interests.append(len(FIELDS))
            features = [availability_time];
            features.extend(availability_medium);
            features.extend(interests)
            features = np.array(features)
            if np.linalg.norm(features) > 0: features = features / np.linalg.norm(features)
            person = {"id": user.id, "name": f"{user.first_name} {user.surname}", "email": user.email, "level": level,
                      "features": features}

            if is_mentee: people["mentee"].append(person)
            if is_mentor: people["mentor"].append(person)

    print("\n--- FINE ELABORAZIONE UTENTI ---")
    print(f"Totale Mentee nella lista: {len(people['mentee'])}")
    print(f"Totale Mentor nella lista: {len(people['mentor'])}")

    if not people["mentee"] or not people["mentor"]:
        print("ERRORE: Una delle due liste è vuota. Impossibile procedere.")
        return None, None, None, None

    weightvector = readWeightVector(weights_path)

    test_features_len = len(people['mentor'][0]['features']) if people['mentor'] else len(
       people['mentee'][0]['features'])
    if test_features_len != len(weightvector):
       weightvector = np.append(weightvector, 1.0)

    M = np.zeros((len(people["mentee"]), len(people["mentor"])))
    for (e, mentee), (o, mentor) in product(enumerate(people["mentee"]), enumerate(people["mentor"])):
        M[e][o] = similarity(mentor, mentee, weightvector)

    row_ind, col_ind = linear_sum_assignment(M, maximize=True)
    return row_ind, col_ind, people, M