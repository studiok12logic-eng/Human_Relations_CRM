from sqlalchemy.orm import Session
from database import Person, Interaction, ProfilingData, Relationship, ProfilingQuestion, engine, SessionLocal
from datetime import datetime, date
import random

# --- Person CRUD ---
def create_person(db: Session, name: str, nickname: str = None, birth_date: date = None,
                  gender: str = None, blood_type: str = None, status: str = None,
                  first_met_date: date = None, notes: str = None):
    db_person = Person(
        name=name, nickname=nickname, birth_date=birth_date, gender=gender,
        blood_type=blood_type, status=status, first_met_date=first_met_date, notes=notes
    )
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    return db_person

def get_people(db: Session):
    return db.query(Person).all()

def get_person(db: Session, person_id: int):
    return db.query(Person).filter(Person.id == person_id).first()

def update_person(db: Session, person_id: int, **kwargs):
    person = db.query(Person).filter(Person.id == person_id).first()
    if person:
        for key, value in kwargs.items():
            setattr(person, key, value)
        db.commit()
        db.refresh(person)
    return person

# --- Interaction CRUD ---
def create_interaction(db: Session, person_id: int, category: str, content: str,
                       tags: str = None, user_feeling: str = None, interaction_date: datetime = None):
    if interaction_date is None:
        interaction_date = datetime.now()

    db_interaction = Interaction(
        person_id=person_id, category=category, content=content,
        tags=tags, user_feeling=user_feeling, date=interaction_date
    )
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

def get_interactions_by_person(db: Session, person_id: int):
    return db.query(Interaction).filter(Interaction.person_id == person_id).order_by(Interaction.date.desc()).all()

# --- Profiling Data CRUD ---
def create_profiling_data(db: Session, person_id: int, framework: str, result: str,
                          confidence_level: str, evidence: str = None):
    db_profiling = ProfilingData(
        person_id=person_id, framework=framework, result=result,
        confidence_level=confidence_level, evidence=evidence
    )
    db.add(db_profiling)
    db.commit()
    db.refresh(db_profiling)
    return db_profiling

def get_profiling_data_by_person(db: Session, person_id: int):
    return db.query(ProfilingData).filter(ProfilingData.person_id == person_id).all()

# --- Relationship CRUD ---
def create_relationship(db: Session, person_a_id: int, person_b_id: int,
                        relation_type: str, quality: str = None):
    # Check if exists (undirected check is complex, here we just assume directed or user handles it)
    # Ideally we should check if (a,b) or (b,a) exists if relationships are symmetric.
    # For now, simplistic implementation.
    db_rel = Relationship(
        person_a_id=person_a_id, person_b_id=person_b_id,
        relation_type=relation_type, quality=quality
    )
    db.add(db_rel)
    db.commit()
    db.refresh(db_rel)
    return db_rel

def get_relationships_for_person(db: Session, person_id: int):
    # Get relationships where person is A or B
    as_a = db.query(Relationship).filter(Relationship.person_a_id == person_id).all()
    as_b = db.query(Relationship).filter(Relationship.person_b_id == person_id).all()
    return as_a + as_b

# --- Questions CRUD & Seed ---
def seed_questions(db: Session):
    if db.query(ProfilingQuestion).count() == 0:
        questions = [
            {"target_trait": "Openness (Big5)", "question_text": "新しいことを試すのが好きですか？", "judgment_criteria": "Yesなら開放性が高い傾向"},
            {"target_trait": "Extroversion (MBTI/Big5)", "question_text": "休日は一人で過ごすことが多いですか、誰かと会うことが多いですか？", "judgment_criteria": "誰かと会うなら外向型(E)"},
            {"target_trait": "Conscientiousness (Big5)", "question_text": "部屋は常に片付いていますか？", "judgment_criteria": "Yesなら誠実性が高い(J寄り)"},
            {"target_trait": "Agreeableness (Big5)", "question_text": "議論になったとき、相手に合わせることが多いですか？", "judgment_criteria": "Yesなら協調性が高い(F寄り)"},
            {"target_trait": "Values", "question_text": "人生で一番大切にしているものは何ですか？", "judgment_criteria": "価値観の特定"},
        ]
        for q in questions:
            db_q = ProfilingQuestion(
                target_trait=q["target_trait"],
                question_text=q["question_text"],
                judgment_criteria=q["judgment_criteria"]
            )
            db.add(db_q)
        db.commit()

def get_random_question(db: Session):
    count = db.query(ProfilingQuestion).count()
    if count == 0:
        return None
    random_offset = int(random.random() * count)
    return db.query(ProfilingQuestion).offset(random_offset).first()
