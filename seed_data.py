import random
from datetime import date, timedelta
from database import init_db, get_db, Person, Interaction, ProfilingQuestion
from crud import create_person, create_interaction, create_relationship, create_person_history

def seed_data():
    init_db()
    db = next(get_db())

    # Check if data already exists to avoid duplication
    if db.query(Person).count() > 0:
        print("Data already exists. Skipping seed.")
        return

    print("Seeding data...")

    # Data lists
    last_names = ["佐藤", "鈴木", "高橋", "田中", "渡辺", "伊藤", "山本", "中村", "小林", "加藤"]
    first_names_m = ["翔太", "蓮", "大翔", "陽翔", "陸", "湊", "悠真", "樹", "陽太", "大和"]
    first_names_f = ["陽葵", "凛", "結菜", "芽依", "詩", "結衣", "陽菜", "美月", "咲良", "莉子"]

    # Fake Kana map (simplified)
    kana_map = {
        "佐藤": "さとう", "鈴木": "すずき", "高橋": "たかはし", "田中": "たなか", "渡辺": "わたなべ",
        "伊藤": "いとう", "山本": "やまもと", "中村": "なかむら", "小林": "こばやし", "加藤": "かとう",
        "翔太": "しょうた", "蓮": "れん", "大翔": "ひろと", "陽翔": "はると", "陸": "りく",
        "湊": "みなと", "悠真": "ゆうま", "樹": "いつき", "陽太": "ひなた", "大和": "やまと",
        "陽葵": "ひまり", "凛": "りん", "結菜": "ゆいな", "芽依": "めい", "詩": "うた",
        "結衣": "ゆい", "陽菜": "ひな", "美月": "みづき", "咲良": "さくら", "莉子": "りこ"
    }

    groups = ["会社", "高校", "大学", "趣味", "家族", "イベント"]
    statuses = ["友人", "同僚", "親友", "知人", "要レビュー"]

    people_objs = []

    # Create Myself
    myself = create_person(
        db,
        last_name="山田",
        first_name="太郎",
        yomigana_last="やまだ",
        yomigana_first="たろう",
        nickname="自分",
        birth_date=date(1990, 1, 1),
        gender="男性",
        blood_type="A",
        status="自分",
        first_met_date=None,
        notes="これは自分です。",
        tags="家族",
        is_self=True,
        prediction_notes="内向的だが好奇心旺盛"
    )
    people_objs.append(myself)

    # Create Others
    for i in range(20):
        is_male = random.choice([True, False])
        ln = random.choice(last_names)
        fn = random.choice(first_names_m) if is_male else random.choice(first_names_f)

        y_ln = kana_map.get(ln, "")
        y_fn = kana_map.get(fn, "")

        b_year = random.randint(1980, 2000)
        b_month = random.randint(1, 12)
        b_day = random.randint(1, 28)

        p = create_person(
            db,
            last_name=ln,
            first_name=fn,
            yomigana_last=y_ln,
            yomigana_first=y_fn,
            nickname=f"{fn}ちゃん" if not is_male else f"{fn}くん",
            birth_date=date(b_year, b_month, b_day),
            gender="男性" if is_male else "女性",
            blood_type=random.choice(["A", "B", "O", "AB"]),
            status=random.choice(statuses),
            first_met_date=date(2023, random.randint(1, 12), random.randint(1, 28)),
            notes=f"ダミーデータ {i}",
            tags=random.choice(groups),
            prediction_notes="MBTI: INFP?"
        )
        people_objs.append(p)

        # Add History
        create_person_history(db, p.id, f"{b_year + 22}/04", "大学卒業")
        create_person_history(db, p.id, f"{b_year + 22}/05", f"{random.choice(groups)}に参加")

    # Create Interactions
    categories = ["会話", "食事", "イベント", "連絡"]
    for i in range(30):
        p = random.choice(people_objs)
        if p.is_self: continue

        create_interaction(
            db,
            person_id=p.id,
            category=random.choice(categories),
            content=f"最近の様子について話した。元気そうだった。",
            tags="日常",
            user_feeling="楽しかった",
            entry_date=date(2024, random.randint(1, 5), random.randint(1, 28)),
            channel="対面"
        )

    # Create Relationships
    for i in range(10):
        p1 = random.choice(people_objs)
        p2 = random.choice(people_objs)
        if p1.id == p2.id: continue

        create_relationship(
            db,
            person_a=p1.id,
            person_b=p2.id,
            rel_type="友人",
            quality="良好",
            caution_flag=False
        )

    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
