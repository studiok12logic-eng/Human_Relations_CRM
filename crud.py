from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import Person, Interaction, ProfilingData, Relationship, ProfilingQuestion, InteractionAnswer
from datetime import datetime, date
from typing import List, Optional, Dict
import random

# --- Person CRUD ---
def create_person(db: Session, last_name: str, first_name: str, yomigana_last: Optional[str], yomigana_first: Optional[str],
                  nickname: Optional[str], birth_date: Optional[date], gender: Optional[str], blood_type: Optional[str],
                  status: str, first_met_date: Optional[date], notes: Optional[str], tags: Optional[str]=None,
                  avatar_path: Optional[str]=None, is_self: bool=False, prediction_notes: Optional[str]=None) -> Person:
    new_person = Person(
        last_name=last_name,
        first_name=first_name,
        yomigana_last=yomigana_last,
        yomigana_first=yomigana_first,
        nickname=nickname,
        birth_date=birth_date,
        gender=gender,
        blood_type=blood_type,
        status=status,
        first_met_date=first_met_date,
        notes=notes,
        tags=tags,
        avatar_path=avatar_path,
        is_self=is_self,
        prediction_notes=prediction_notes
    )
    db.add(new_person)
    db.commit()
    db.refresh(new_person)
    return new_person

def get_people(db: Session) -> List[Person]:
    # Sort by yomigana if available, else kanji
    return db.query(Person).order_by(
        Person.yomigana_last, Person.yomigana_first, Person.last_name, Person.first_name
    ).all()

def get_person(db: Session, person_id: int) -> Optional[Person]:
    return db.query(Person).filter(Person.id == person_id).first()

def delete_person(db: Session, person_id: int):
    person = get_person(db, person_id)
    if person:
        # Manually delete relationships where this person is involved
        db.query(Relationship).filter(
            or_(Relationship.person_a_id == person_id, Relationship.person_b_id == person_id)
        ).delete(synchronize_session=False)

        db.delete(person)
        db.commit()

def update_person(db: Session, person_id: int, **kwargs) -> Optional[Person]:
    person = get_person(db, person_id)
    if person:
        for key, value in kwargs.items():
            setattr(person, key, value)
        db.commit()
        db.refresh(person)
    return person

# --- Interaction CRUD ---
def create_interaction(db: Session, person_id: int, category: str, content: str, tags: str, user_feeling: str,
                       entry_date: date, start_date_str: Optional[str]=None, end_date_str: Optional[str]=None,
                       answers: Optional[List[Dict]]=None, channel: Optional[str]=None) -> Interaction:
    new_int = Interaction(
        person_id=person_id,
        category=category,
        content=content,
        tags=tags,
        user_feeling=user_feeling,
        entry_date=entry_date,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        channel=channel
    )
    db.add(new_int)
    db.commit()
    db.refresh(new_int)

    if answers:
        for ans in answers:
            new_ans = InteractionAnswer(
                interaction_id=new_int.id,
                question_id=ans['question_id'],
                answer_value=ans['answer_value']
            )
            db.add(new_ans)
        db.commit()

    return new_int

def get_interactions_by_person(db: Session, person_id: int) -> List[Interaction]:
    return db.query(Interaction).filter(Interaction.person_id == person_id).order_by(Interaction.entry_date.desc()).all()

# --- Profiling CRUD (Legacy/Additional) ---
def create_profiling_data(db: Session, person_id: int, framework: str, result: str, confidence: str, evidence: str) -> ProfilingData:
    new_data = ProfilingData(
        person_id=person_id,
        framework=framework,
        result=result,
        confidence_level=confidence,
        evidence=evidence
    )
    db.add(new_data)
    db.commit()
    db.refresh(new_data)
    return new_data

def get_profiling_data_by_person(db: Session, person_id: int) -> List[ProfilingData]:
    return db.query(ProfilingData).filter(ProfilingData.person_id == person_id).all()

# --- Relationship CRUD ---
def create_relationship(db: Session, person_a: int, person_b: int, rel_type: str, quality: str,
                        position_a_to_b: Optional[str]=None, position_b_to_a: Optional[str]=None,
                        caution_flag: bool=False) -> Relationship:
    # Check if exists
    existing = db.query(Relationship).filter(
        or_(
            (Relationship.person_a_id == person_a) & (Relationship.person_b_id == person_b),
            (Relationship.person_a_id == person_b) & (Relationship.person_b_id == person_a)
        )
    ).first()

    if existing:
        # Update existing
        if existing.person_a_id == person_a:
            existing.relation_type = rel_type
            existing.quality = quality
            existing.position_a_to_b = position_a_to_b
            existing.position_b_to_a = position_b_to_a
            existing.caution_flag = caution_flag
        else:
            # Found as A=b, B=a
            existing.relation_type = rel_type
            existing.quality = quality
            existing.position_a_to_b = position_b_to_a # Flip
            existing.position_b_to_a = position_a_to_b # Flip
            existing.caution_flag = caution_flag

        db.commit()
        db.refresh(existing)
        return existing

    new_rel = Relationship(
        person_a_id=person_a,
        person_b_id=person_b,
        relation_type=rel_type,
        quality=quality,
        position_a_to_b=position_a_to_b,
        position_b_to_a=position_b_to_a,
        caution_flag=caution_flag
    )
    db.add(new_rel)
    db.commit()
    db.refresh(new_rel)
    return new_rel

def get_relationships_for_person(db: Session, person_id: int) -> List[Relationship]:
    return db.query(Relationship).filter(
        or_(Relationship.person_a_id == person_id, Relationship.person_b_id == person_id)
    ).all()

def get_all_relationships(db: Session) -> List[Relationship]:
    return db.query(Relationship).all()

# --- Question CRUD ---
def create_question(db: Session, category: str, question_text: str, judgment_criteria: str, answer_type: str, target_trait: Optional[str]=None, options: Optional[str]=None) -> ProfilingQuestion:
    new_q = ProfilingQuestion(
        category=category,
        question_text=question_text,
        judgment_criteria=judgment_criteria,
        answer_type=answer_type,
        target_trait=target_trait,
        options=options
    )
    db.add(new_q)
    db.commit()
    db.refresh(new_q)
    return new_q

def update_question(db: Session, question_id: int, **kwargs) -> Optional[ProfilingQuestion]:
    q = db.query(ProfilingQuestion).filter(ProfilingQuestion.id == question_id).first()
    if q:
        for key, value in kwargs.items():
            setattr(q, key, value)
        db.commit()
        db.refresh(q)
    return q

def delete_question(db: Session, question_id: int):
    q = db.query(ProfilingQuestion).filter(ProfilingQuestion.id == question_id).first()
    if q:
        db.delete(q)
        db.commit()

def seed_questions(db: Session):
    if db.query(ProfilingQuestion).count() == 0:
        # Initial questions
        questions = [
            {"category": "Big5", "text": "新しい経験やアイデアに対してどれくらいオープンですか？", "criteria": "High: 常に新しいことを探している. Low: 習慣を好む.", "type": "numeric", "trait": "Openness", "options": None},
            {"category": "Big5", "text": "約束や期限を守ることはどれくらい重要ですか？", "criteria": "High: 非常に几帳面. Low: 即興的.", "type": "numeric", "trait": "Conscientiousness", "options": None},
            {"category": "MBTI", "text": "休日は一人でゆっくり過ごしたいですか？それとも誰かと出かけたいですか？", "criteria": "E (外向) vs I (内向)", "type": "numeric", "trait": "E/I", "options": None},
            {"category": "個人情報", "text": "電話番号", "criteria": "", "type": "text", "trait": "Contact", "options": None},
        ]
        for q in questions:
            db.add(ProfilingQuestion(
                category=q["category"],
                question_text=q["text"],
                judgment_criteria=q["criteria"],
                answer_type=q["type"],
                target_trait=q["trait"],
                options=q["options"]
            ))
        db.commit()

def get_random_question(db: Session) -> Optional[ProfilingQuestion]:
    count = db.query(ProfilingQuestion).count()
    if count == 0:
        return None
    offset = random.randint(0, count - 1)
    return db.query(ProfilingQuestion).offset(offset).first()

def get_all_questions(db: Session) -> List[ProfilingQuestion]:
    return db.query(ProfilingQuestion).all()

def get_interaction_answers(db: Session, person_id: int) -> List[InteractionAnswer]:
    # Join InteractionAnswer with Interaction to filter by person
    return db.query(InteractionAnswer).join(Interaction).filter(Interaction.person_id == person_id).all()

def get_question_answer_counts(db: Session, person_id: int) -> Dict[int, int]:
    # Returns {question_id: count}
    answers = get_interaction_answers(db, person_id)
    counts = {}
    for a in answers:
        counts[a.question_id] = counts.get(a.question_id, 0) + 1
    return counts
