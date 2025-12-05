from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, date

Base = declarative_base()

class Person(Base):
    __tablename__ = 'people'
    id = Column(Integer, primary_key=True)
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    yomigana_last = Column(String)
    yomigana_first = Column(String)

    nickname = Column(String)
    birth_date = Column(Date)
    gender = Column(String)
    blood_type = Column(String)
    status = Column(String)  # e.g., Friend, Acquaintance, VIP
    first_met_date = Column(Date)
    notes = Column(Text)
    strategy = Column(Text) # 攻略方法

    # New columns
    tags = Column(String) # Chunking/Group

    avatar_path = Column(String)
    is_self = Column(Boolean, default=False)
    prediction_notes = Column(Text) # Personality based prediction

    # Relationships
    interactions = relationship("Interaction", back_populates="person", cascade="all, delete-orphan")
    profiling_data = relationship("ProfilingData", back_populates="person", cascade="all, delete-orphan")
    history = relationship("PersonHistory", back_populates="person", cascade="all, delete-orphan")

    @property
    def name(self):
        return f"{self.last_name} {self.first_name}"

class PersonHistory(Base):
    __tablename__ = 'person_history'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'), nullable=False)
    date_str = Column(String) # e.g. 1999/04, 2020 Summer
    content = Column(Text)

    person = relationship("Person", back_populates="history")

class Interaction(Base):
    __tablename__ = 'interactions'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'), nullable=False)

    entry_date = Column(Date, default=date.today)

    # Fuzzy period
    start_date_str = Column(String) # e.g., 2024/00/00
    end_date_str = Column(String)   # e.g., Present, None

    category = Column(String)  # Conversation, Meal, Event, Observation, Contact, Gift, Collaboration
    channel = Column(String)   # In Person, Call, Text, Passive
    tags = Column(String)  # Comma separated tags
    content = Column(Text)
    user_feeling = Column(Text)

    person = relationship("Person", back_populates="interactions")
    answers = relationship("InteractionAnswer", back_populates="interaction", cascade="all, delete-orphan")

class InteractionAnswer(Base):
    __tablename__ = 'interaction_answers'
    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, ForeignKey('interactions.id'))
    question_id = Column(Integer, ForeignKey('profiling_questions.id'))
    answer_value = Column(String) # Can be numeric (0,1,3,5) or text

    interaction = relationship("Interaction", back_populates="answers")
    question = relationship("ProfilingQuestion")

class ProfilingData(Base):
    __tablename__ = 'profiling_data'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'), nullable=False)
    framework = Column(String)  # MBTI, Big5, etc.
    result = Column(String)
    confidence_level = Column(String)  # S, A, B, C
    evidence = Column(Text)

    person = relationship("Person", back_populates="profiling_data")

class Relationship(Base):
    __tablename__ = 'relationships'
    id = Column(Integer, primary_key=True)
    person_a_id = Column(Integer, ForeignKey('people.id'), nullable=False)
    person_b_id = Column(Integer, ForeignKey('people.id'), nullable=False)
    relation_type = Column(String)  # e.g., Spouse, Colleague
    quality = Column(String)  # e.g., Good, Bad

    position_a_to_b = Column(String) # A's stance to B
    position_b_to_a = Column(String) # B's stance to A

    caution_flag = Column(Boolean, default=False) # Red dashed line in graph

class ProfilingQuestion(Base):
    __tablename__ = 'profiling_questions'
    id = Column(Integer, primary_key=True)
    category = Column(String) # MBTI, Physiognomy, Personal Info, etc.
    question_text = Column(Text)
    judgment_criteria = Column(Text)
    answer_type = Column(String) # 'numeric' (was scale), 'text', 'selection'
    options = Column(Text) # Comma separated options for 'selection' type
    target_trait = Column(String) # Keep for backward compat or specific traits

# Database Setup
DATABASE_URL = "sqlite:///human_crm.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
