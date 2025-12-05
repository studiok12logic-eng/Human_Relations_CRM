from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Person(Base):
    __tablename__ = 'people'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    nickname = Column(String)
    birth_date = Column(Date)
    gender = Column(String)
    blood_type = Column(String)
    status = Column(String)  # e.g., Friend, Acquaintance, VIP
    first_met_date = Column(Date)
    notes = Column(Text)

    # Relationships
    interactions = relationship("Interaction", back_populates="person", cascade="all, delete-orphan")
    profiling_data = relationship("ProfilingData", back_populates="person", cascade="all, delete-orphan")

    # For relationships between people, it's a bit more complex.
    # We will query the Relationship table directly usually, but can define if needed.

class Interaction(Base):
    __tablename__ = 'interactions'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'), nullable=False)
    date = Column(DateTime, default=datetime.now)
    category = Column(String)  # Conversation, Meal, Event, Observation, Contact
    tags = Column(String)  # Comma separated tags
    content = Column(Text)
    user_feeling = Column(Text)

    person = relationship("Person", back_populates="interactions")

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

    # person_a = relationship("Person", foreign_keys=[person_a_id])
    # person_b = relationship("Person", foreign_keys=[person_b_id])

class ProfilingQuestion(Base):
    __tablename__ = 'profiling_questions'
    id = Column(Integer, primary_key=True)
    target_trait = Column(String)
    question_text = Column(Text)
    judgment_criteria = Column(Text)

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
