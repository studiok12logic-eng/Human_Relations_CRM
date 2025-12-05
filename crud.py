from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import Person, Interaction, ProfilingData, Relationship, ProfilingQuestion
from datetime import datetime, date
from typing import List, Optional
import random

# --- Person CRUD ---
def create_person(db: Session, name: str, nickname: Optional[str], birth_date: Optional[date], gender: Optional[str], blood_type: Optional[str], status: str, first_met_date: Optional[date], notes: Optional[str], tags: Optional[str]=None, mbti_result: Optional[str]=None) -> Person:
    new_person = Person(
        name=name,
        nickname=nickname,
        birth_date=birth_date,
        gender=gender,
        blood_type=blood_type,
        status=status,
        first_met_date=first_met_date,
        notes=notes,
        tags=tags,
        mbti_result=mbti_result
    )
    db.add(new_person)
    db.commit()
    db.refresh(new_person)
    return new_person

def get_people(db: Session) -> List[Person]:
    return db.query(Person).all()

def get_person(db: Session, person_id: int) -> Optional[Person]:
    return db.query(Person).filter(Person.id == person_id).first()

def update_person(db: Session, person_id: int, **kwargs) -> Optional[Person]:
    person = get_person(db, person_id)
    if person:
        for key, value in kwargs.items():
            setattr(person, key, value)
        db.commit()
        db.refresh(person)
    return person

# --- Interaction CRUD ---
def create_interaction(db: Session, person_id: int, category: str, content: str, tags: str, user_feeling: str, date_time: datetime) -> Interaction:
    new_int = Interaction(
        person_id=person_id,
        category=category,
        content=content,
        tags=tags,
        user_feeling=user_feeling,
        date=date_time
    )
    db.add(new_int)
    db.commit()
    db.refresh(new_int)
    return new_int

def get_interactions_by_person(db: Session, person_id: int) -> List[Interaction]:
    return db.query(Interaction).filter(Interaction.person_id == person_id).order_by(Interaction.date.desc()).all()

# --- Profiling CRUD ---
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
def create_relationship(db: Session, person_a: int, person_b: int, rel_type: str, quality: str) -> Relationship:
    # Check if exists
    existing = db.query(Relationship).filter(
        or_(
            (Relationship.person_a_id == person_a) & (Relationship.person_b_id == person_b),
            (Relationship.person_a_id == person_b) & (Relationship.person_b_id == person_a)
        )
    ).first()

    if existing:
        existing.relation_type = rel_type
        existing.quality = quality
        db.commit()
        db.refresh(existing)
        return existing

    new_rel = Relationship(
        person_a_id=person_a,
        person_b_id=person_b,
        relation_type=rel_type,
        quality=quality
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
def seed_questions(db: Session):
    if db.query(ProfilingQuestion).count() == 0:
        questions = [
            {"trait": "Openness", "text": "新しい経験やアイデアに対してどれくらいオープンですか？", "criteria": "High: 常に新しいことを探している. Low: 習慣を好む."},
            {"trait": "Conscientiousness", "text": "約束や期限を守ることはどれくらい重要ですか？", "criteria": "High: 非常に几帳面. Low: 即興的."},
            {"trait": "Extraversion", "text": "大勢の人の中にいるとエネルギーを得ますか、それとも消耗しますか？", "criteria": "High: 外向的. Low: 内向的."},
            {"trait": "Agreeableness", "text": "他人の感情やニーズにどれくらい敏感ですか？", "criteria": "High: 協調的. Low: 競争的."},
            {"trait": "Neuroticism", "text": "ストレスを感じたとき、どれくらい感情的になりますか？", "criteria": "High: 不安になりやすい. Low: 落ち着いている."},
        ]
        for q in questions:
            db.add(ProfilingQuestion(target_trait=q["trait"], question_text=q["text"], judgment_criteria=q["criteria"]))
        db.commit()

def seed_mbti_questions(db: Session):
    # Check if MBTI questions exist (simple check)
    if db.query(ProfilingQuestion).filter(ProfilingQuestion.target_trait == "MBTI").count() == 0:
        # Example MBTI questions adapted for casual observation/asking
        mbti_qs = [
            {"text": "休日は一人でゆっくり過ごしたいですか？それとも誰かと出かけたいですか？", "criteria": "E (外向) vs I (内向)"},
            {"text": "物事を判断するとき、事実やデータを重視しますか？それとも感情や調和を重視しますか？", "criteria": "T (思考) vs F (感情)"},
            {"text": "旅行の計画はきっちり立てますか？それともその場の流れに任せますか？", "criteria": "J (判断) vs P (知覚)"},
            {"text": "物事の細部に目が行きますか？それとも全体的な可能性や意味に目が行きますか？", "criteria": "S (感覚) vs N (直観)"},
            {"text": "新しい環境に飛び込むとき、ワクワクしますか？それとも不安になりますか？", "criteria": "E/I or Openness"},
        ]
        for q in mbti_qs:
            db.add(ProfilingQuestion(target_trait="MBTI", question_text=q["text"], judgment_criteria=q["criteria"]))
        db.commit()

def get_random_question(db: Session) -> Optional[ProfilingQuestion]:
    count = db.query(ProfilingQuestion).count()
    if count == 0:
        return None
    offset = random.randint(0, count - 1)
    return db.query(ProfilingQuestion).offset(offset).first()

def get_all_questions(db: Session) -> List[ProfilingQuestion]:
    return db.query(ProfilingQuestion).all()
