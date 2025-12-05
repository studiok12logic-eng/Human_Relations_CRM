import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Person, Interaction, Relationship, ProfilingQuestion
from crud import (
    create_person, create_interaction, create_relationship, create_question,
    get_people, get_interactions_by_person, get_relationships_for_person, get_all_questions
)
from datetime import date

class TestCRM(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_create_person(self):
        p = create_person(self.db, "Tanaka", "Taro", "tanaka", "taro", "Taro-chan", date(1990, 1, 1), "Male", "A", "Friend", date(2023, 1, 1), "Memo", "Group1", "path/to/avatar", False)
        self.assertEqual(p.last_name, "Tanaka")
        self.assertEqual(p.avatar_path, "path/to/avatar")

    def test_create_interaction_with_channel(self):
        p = create_person(self.db, "Tanaka", "Taro", "tanaka", "taro", None, None, None, None, "Friend", None, None)
        i = create_interaction(self.db, p.id, "Meal", "Lunch", "yummy", "Good", date.today(), channel="In Person")
        self.assertEqual(i.channel, "In Person")

        interactions = get_interactions_by_person(self.db, p.id)
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].channel, "In Person")

    def test_create_relationship_with_caution(self):
        p1 = create_person(self.db, "A", "A", None, None, None, None, None, None, "F", None, None)
        p2 = create_person(self.db, "B", "B", None, None, None, None, None, None, "F", None, None)

        r = create_relationship(self.db, p1.id, p2.id, "Rival", "Bad", caution_flag=True)
        self.assertTrue(r.caution_flag)

        rels = get_relationships_for_person(self.db, p1.id)
        self.assertEqual(len(rels), 1)
        self.assertTrue(rels[0].caution_flag)

    def test_create_question_with_options(self):
        q = create_question(self.db, "Info", "Select One", "None", "selection", options="Option1,Option2")
        self.assertEqual(q.answer_type, "selection")
        self.assertEqual(q.options, "Option1,Option2")

        qs = get_all_questions(self.db)
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].options, "Option1,Option2")

if __name__ == '__main__':
    unittest.main()
