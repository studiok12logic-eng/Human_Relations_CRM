import streamlit as st
import pandas as pd
from datetime import datetime, date
import streamlit.components.v1 as components
from pyvis.network import Network
import tempfile
import os
import random

from database import init_db, get_db, Person, InteractionAnswer, ProfilingQuestion
from crud import (
    create_person, get_people, get_person, update_person, delete_person,
    create_interaction, get_interactions_by_person,
    create_profiling_data, get_profiling_data_by_person,
    create_relationship, get_relationships_for_person, get_all_relationships,
    seed_questions, get_random_question, get_all_questions,
    create_question, update_question, delete_question, get_question_answer_counts
)

# --- Configuration & Setup ---
st.set_page_config(page_title="Human Relations CRM", layout="wide", page_icon="🧩")

# Initialize DB
init_db()
db = next(get_db())
seed_questions(db)

# --- Navigation State Management ---
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "人物一覧"

def navigate_to(page_name):
    st.session_state["current_page"] = page_name
    # Since we can't programmatically set the sidebar widget value easily without rerun/key hacks,
    # we just update state and hope the user flows naturally, or we use a hack.
    # The hack is to use the key in the radio button equal to a session state var.

# --- Sidebar Navigation ---
st.sidebar.title("🧩 メニュー")
# Use index to control selection
page_options = ["人物一覧", "人物登録", "交流ログ", "ダッシュボード", "相関図", "質問リスト"]
# Find current index
try:
    current_index = page_options.index(st.session_state["current_page"])
except ValueError:
    current_index = 0

page = st.sidebar.radio("移動", page_options, index=current_index, key="nav_radio")

# Update state if changed via sidebar
if page != st.session_state["current_page"]:
    st.session_state["current_page"] = page
    st.rerun()

# --- Helper Functions ---
def calculate_age(born):
    if not born:
        return "不明"
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

# --- Pages ---

if page == "人物一覧":
    st.title("📂 人物一覧")

    people = get_people(db)

    if not people:
        st.info("人物が登録されていません。「人物登録」から追加してください。")
    else:
        col_search, col_sort = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("検索 (名前・タグ・ステータス)", "")
        with col_sort:
            sort_option = st.selectbox("並び替え", ["名前順", "グループ順", "ステータス順"])

        # Sorting logic (simple)
        sorted_people = people
        if sort_option == "グループ順":
            sorted_people = sorted(people, key=lambda x: x.tags if x.tags else "zzz")
        elif sort_option == "ステータス順":
            sorted_people = sorted(people, key=lambda x: x.status if x.status else "zzz")
        # Default is already sorted by yomigana in CRUD

        # Display as a table (using DataFrame for better sorting/filtering)
        data = []
        for p in sorted_people:
            # Search filter
            search_target = f"{p.last_name} {p.first_name} {p.nickname} {p.tags} {p.status}"
            if search_query.lower() in search_target.lower():
                data.append({
                    "ID": p.id,
                    "名前": f"{p.last_name} {p.first_name}",
                    "ニックネーム": p.nickname,
                    "グループ": p.tags,
                    "ステータス": p.status,
                    "性別": p.gender,
                    "年齢": calculate_age(p.birth_date),
                })

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("### 操作")
            selected_row_id = st.selectbox("人物を選択", [d["ID"] for d in data], format_func=lambda x: next(f"{p.last_name} {p.first_name}" for p in people if p.id == x))

            col_act1, col_act2, col_act3 = st.columns([1, 1, 4])
            with col_act1:
                if st.button("編集・詳細"):
                    st.session_state["selected_person_id"] = selected_row_id
                    navigate_to("ダッシュボード")
                    st.rerun()

            with col_act2:
                if st.button("削除", type="primary"):
                    delete_person(db, selected_row_id)
                    st.success("削除しました。")
                    st.rerun()

        else:
            st.warning("見つかりませんでした。")

elif page == "人物登録":
    st.title("👤 新規人物登録")

    with st.form("register_form"):
        # Special 'Self' registration check
        is_self = st.checkbox("自分の情報を登録する")

        col1, col2 = st.columns(2)
        with col1:
            last_name = st.text_input("姓 (必須)")
            first_name = st.text_input("名 (必須)")
            yomigana_last = st.text_input("姓 (よみがな)")
            yomigana_first = st.text_input("名 (よみがな)")
            nickname = st.text_input("ニックネーム")

        with col2:
            gender = st.selectbox("性別", ["男性", "女性", "ノンバイナリー", "その他", "不明"])
            blood_type = st.selectbox("血液型", ["A", "B", "O", "AB", "不明"])

            # Group selection - allow adding new
            # Get existing tags
            existing_people = get_people(db)
            all_tags = set()
            for p in existing_people:
                if p.tags:
                    for t in p.tags.split(','):
                        all_tags.add(t.strip())

            tag_options = list(all_tags)
            selected_tags = st.multiselect("グループ (既存)", tag_options)
            new_tags = st.text_input("新しいグループ/タグ (カンマ区切り)")

            # Combine tags
            final_tags = ", ".join(selected_tags)
            if new_tags:
                if final_tags:
                    final_tags += ", " + new_tags
                else:
                    final_tags = new_tags

            # Status - configurable? For now hardcoded list + "Other"
            status_options = ["知人", "友人", "親友", "同僚", "家族", "VIP", "要レビュー"]
            status = st.selectbox("ステータス", status_options)

            birth_date = st.date_input("生年月日", value=None, min_value=date(1900, 1, 1))
            first_met_date = st.date_input("初対面日", value=date.today())

            # Avatar (URL or Path)
            avatar_path = st.text_input("アイコン画像URL / パス")

        notes = st.text_area("メモ")

        submitted = st.form_submit_button("登録")

        if submitted:
            if not last_name or not first_name:
                st.error("姓と名は必須です。")
            else:
                create_person(db, last_name, first_name, yomigana_last, yomigana_first, nickname, birth_date, gender, blood_type, status, first_met_date, notes, final_tags, avatar_path, is_self)
                st.success(f"{last_name} {first_name} さんを登録しました！")

elif page == "交流ログ":
    st.title("📝 交流ログ")

    people = get_people(db)
    if not people:
        st.error("まずは人物を登録してください。")
    else:
        # Select Person
        person_options = {p.id: f"{p.last_name} {p.first_name}" for p in people}
        # Pre-select if passed from other page
        default_index = 0
        if "selected_person_id" in st.session_state and st.session_state["selected_person_id"] in person_options:
            try:
                ids = list(person_options.keys())
                default_index = ids.index(st.session_state["selected_person_id"])
            except ValueError:
                pass

        person_id = st.selectbox("人物を選択", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

        # Get answer counts for this person
        answer_counts = get_question_answer_counts(db, person_id)

        with st.form("interaction_form"):
            col1, col2 = st.columns(2)
            with col1:
                i_date = st.date_input("入力日", value=date.today())

                # Fuzzy Period
                start_date_str = st.text_input("開始期間 (例: 2024/04/01, 2024年春)")
                end_date_str = st.text_input("終了期間 (例: 2024/04/05, 現在)")

            with col2:
                category = st.selectbox("カテゴリ", ["会話", "食事", "イベント", "観察", "連絡", "その他"])
                category_new = st.text_input("カテゴリ追加 (上記にない場合)")
                if category_new:
                    category = category_new

                tags = st.text_input("タグ (カンマ区切り)")

            content = st.text_area("内容 / 詳細")
            user_feeling = st.text_area("自分の感情 / メモ")

            st.divider()
            st.markdown("### 質問リストからの回答 (任意)")

            questions = get_all_questions(db)
            # Format questions with answer count
            q_options = {q.id: f"{q.question_text} (回答数: {answer_counts.get(q.id, 0)})" for q in questions}
            selected_q_ids = st.multiselect("質問を選択", list(q_options.keys()), format_func=lambda x: q_options[x])

            answers = []
            for qid in selected_q_ids:
                q = next(q_ for q_ in questions if q_.id == qid)
                st.markdown(f"**Q: {q.question_text}**")
                if q.answer_type == 'scale':
                    val = st.select_slider(f"回答 ({q.id})", options=["0", "1", "3", "5"], key=f"ans_{qid}")
                    answers.append({'question_id': qid, 'answer_value': val})
                else:
                    val = st.text_input(f"回答 ({q.id})", key=f"ans_{qid}")
                    answers.append({'question_id': qid, 'answer_value': val})

            submitted_log = st.form_submit_button("ログを保存")
            if submitted_log:
                create_interaction(db, person_id, category, content, tags, user_feeling, i_date, start_date_str, end_date_str, answers)
                st.success("交流ログを保存しました！")

elif page == "ダッシュボード":
    people = get_people(db)
    if not people:
        st.warning("人物が登録されていません。")
    else:
        # Sidebar selection
        person_options = {p.id: f"{p.last_name} {p.first_name}" for p in people}
        default_index = 0
        if "selected_person_id" in st.session_state and st.session_state["selected_person_id"] in person_options:
             try:
                ids = list(person_options.keys())
                default_index = ids.index(st.session_state["selected_person_id"])
             except ValueError:
                pass

        selected_id = st.sidebar.selectbox("ダッシュボード表示対象", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

        # Load Data
        person = get_person(db, selected_id)
        interactions = get_interactions_by_person(db, selected_id)
        relationships = get_relationships_for_person(db, selected_id)

        # --- HEADER & EDIT ---
        with st.expander("👤 人物情報の編集", expanded=False):
            with st.form("edit_person_form"):
                new_last = st.text_input("姓", value=person.last_name)
                new_first = st.text_input("名", value=person.first_name)
                new_tags = st.text_input("グループ", value=person.tags or "")
                new_status = st.text_input("ステータス", value=person.status or "")
                new_notes = st.text_area("メモ", value=person.notes or "")
                new_prediction = st.text_area("性格分析予想 (付き合い方・考え方)", value=person.prediction_notes or "")

                if st.form_submit_button("保存"):
                    update_person(db, person.id, last_name=new_last, first_name=new_first, tags=new_tags, status=new_status, notes=new_notes, prediction_notes=new_prediction)
                    st.success("更新しました。")
                    st.rerun()

                if st.form_submit_button("削除 (注意: 元に戻せません)", type="primary"):
                     delete_person(db, person.id)
                     st.warning("削除しました。")
                     st.rerun()

        col_h1, col_h2 = st.columns([1, 3])
        with col_h1:
            if person.avatar_path:
                st.image(person.avatar_path, width=150)
            else:
                st.image("https://placehold.co/150x150?text=No+Image", width=150)
        with col_h2:
            st.title(f"{person.last_name} {person.first_name}")
            if person.nickname:
                st.caption(f"({person.nickname})")

            st.write(f"🏷️ グループ: {person.tags} | ステータス: {person.status}")
            st.markdown(f"**性別:** {person.gender} | **年齢:** {calculate_age(person.birth_date)}")
            if person.prediction_notes:
                st.info(f"🔮 **予想・付き合い方:** {person.prediction_notes}")

        st.divider()

        # --- Answer Rate / Profiling Summary ---
        st.subheader("📊 質問回答率 (カテゴリ別)")
        from crud import get_interaction_answers
        answers = get_interaction_answers(db, person.id)
        questions = get_all_questions(db)

        if answers:
            cat_counts = {}
            cat_totals = {}
            for q in questions:
                cat_totals[q.category] = cat_totals.get(q.category, 0) + 1

            answered_q_ids = set(a.question_id for a in answers)

            for qid in answered_q_ids:
                q = next((x for x in questions if x.id == qid), None)
                if q:
                    cat_counts[q.category] = cat_counts.get(q.category, 0) + 1

            cols = st.columns(len(cat_totals))
            for idx, (cat, total) in enumerate(cat_totals.items()):
                count = cat_counts.get(cat, 0)
                rate = count / total if total > 0 else 0
                with cols[idx % len(cols)]:
                    st.metric(label=cat, value=f"{count}/{total}", delta=f"{rate:.0%}")
        else:
            st.write("回答データがありません。")

        # --- LAYOUT ---
        col_main, col_side = st.columns([2, 1])

        with col_main:
            col_tl_head, col_tl_search = st.columns([1,1])
            with col_tl_head:
                st.subheader("📅 タイムライン")
            with col_tl_search:
                tl_search = st.text_input("タイムライン検索", placeholder="キーワード...")

            if st.button("交流ログを追加"):
                st.session_state["selected_person_id"] = person.id
                navigate_to("交流ログ")
                st.rerun()

            if interactions:
                for i in interactions:
                    if tl_search and (tl_search not in i.content and tl_search not in (i.tags or "") and tl_search not in (i.category or "")):
                        continue

                    date_display = i.entry_date.strftime('%Y-%m-%d')
                    if i.start_date_str:
                        date_display = f"{i.start_date_str} 〜 {i.end_date_str or ''}"

                    with st.expander(f"{date_display} - {i.category}"):
                        st.markdown(f"**内容:** {i.content}")
                        if i.tags:
                            st.caption(f"タグ: {i.tags}")
                        if i.user_feeling:
                            st.info(f"感情: {i.user_feeling}")
                        if i.answers:
                            st.write("---")
                            st.caption("回答:")
                            for ans in i.answers:
                                st.write(f"- {ans.question.question_text}: **{ans.answer_value}**")
            else:
                st.info("交流ログはまだありません。")

        with col_side:
            # --- Relationships ---
            st.subheader("🔗 関係性")
            if st.button("関係性を追加"):
                st.session_state["selected_person_id"] = person.id
                navigate_to("相関図")
                st.rerun()

            if relationships:
                for r in relationships:
                    other_id = r.person_b_id if r.person_a_id == person.id else r.person_a_id
                    other_p = next((p for p in people if p.id == other_id), None)
                    if other_p:
                        position = ""
                        if r.person_a_id == person.id:
                            position = r.position_a_to_b
                        else:
                            position = r.position_b_to_a

                        pos_str = f" ({position})" if position else ""
                        st.markdown(f"- **{other_p.last_name} {other_p.first_name}**: {r.relation_type} ({r.quality}){pos_str}")
            else:
                st.markdown("*関係性の記録なし*")

elif page == "相関図":
    st.title("🌐 人物相関図")

    people = get_people(db)
    if not people:
        st.warning("人物が登録されていません。")
    else:
        # --- Add Relationship Form ---
        with st.expander("🔗 関係性を追加する", expanded=False):
            with st.form("relation_page_form"):
                person_options = {p.id: f"{p.last_name} {p.first_name}" for p in people}
                col1, col2, col3 = st.columns(3)

                # Default selection from session if available
                default_p1_index = 0
                if "selected_person_id" in st.session_state and st.session_state["selected_person_id"] in person_options:
                     try:
                        ids = list(person_options.keys())
                        default_p1_index = ids.index(st.session_state["selected_person_id"])
                     except ValueError:
                        pass

                with col1:
                    p1_id = st.selectbox("人物 A", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p1", index=default_p1_index)
                with col2:
                    p2_id = st.selectbox("人物 B", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p2")
                with col3:
                    rel_type = st.text_input("関係性 (例: 配偶者, ライバル)")

                col4, col5, col6 = st.columns(3)
                with col4:
                    quality = st.selectbox("関係の質", ["良好", "普通", "険悪", "複雑"])
                with col5:
                    pos_a_b = st.text_input("Aから見たBの立場 (上司, 部下 etc)")
                with col6:
                    pos_b_a = st.text_input("Bから見たAの立場")

                submitted_rel = st.form_submit_button("関係を保存")

                if submitted_rel:
                    if p1_id == p2_id:
                        st.error("同一人物間の関係は登録できません。")
                    else:
                        create_relationship(db, p1_id, p2_id, rel_type, quality, pos_a_b, pos_b_a)
                        st.success("関係性を保存しました！")

        st.divider()

        # --- Visualization Controls ---
        filter_mode = st.radio("表示モード", ["全体", "グループ(チャンク)別", "特定の人物中心"], horizontal=True)

        selected_chunk = None
        center_person_id = None

        if filter_mode == "グループ(チャンク)別":
            all_tags = set()
            for p in people:
                if p.tags:
                    tags = [t.strip() for t in p.tags.split(',')]
                    all_tags.update(tags)
            if not all_tags:
                st.info("グループ/タグが設定されている人物がいません。")
            else:
                selected_chunk = st.selectbox("グループを選択", list(all_tags))

        elif filter_mode == "特定の人物中心":
             center_person_id = st.selectbox("中心人物を選択", options=person_options.keys(), format_func=lambda x: person_options[x])

        # --- Generate Graph ---
        relationships = get_all_relationships(db)
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")

        filtered_people = []
        if filter_mode == "全体":
            filtered_people = people
        elif filter_mode == "グループ(チャンク)別" and selected_chunk:
            filtered_people = [p for p in people if p.tags and selected_chunk in [t.strip() for t in p.tags.split(',')]]
        elif filter_mode == "特定の人物中心" and center_person_id:
            center_p = next((p for p in people if p.id == center_person_id), None)
            if center_p:
                filtered_people = [center_p]
                related_ids = set()
                for r in relationships:
                    if r.person_a_id == center_person_id:
                        related_ids.add(r.person_b_id)
                    elif r.person_b_id == center_person_id:
                        related_ids.add(r.person_a_id)
                for pid in related_ids:
                    p = next((pp for pp in people if pp.id == pid), None)
                    if p:
                        filtered_people.append(p)

        filtered_ids = {p.id for p in filtered_people}

        for p in filtered_people:
            age = calculate_age(p.birth_date)
            label = f"{p.last_name} {p.first_name}\n({age}歳)"
            title = f"Name: {p.last_name} {p.first_name}\nStatus: {p.status}\nGroup: {p.tags}"

            color = "#97c2fc"
            if p.id == center_person_id:
                color = "#ffb3b3"
            if p.is_self:
                color = "#ffffcc"

            shape = "box"
            image = None
            if p.avatar_path and p.avatar_path.startswith("http"):
                 shape = "circularImage"
                 image = p.avatar_path

            net.add_node(p.id, label=label, title=title, color=color, shape=shape, image=image)

        for r in relationships:
            if r.person_a_id in filtered_ids and r.person_b_id in filtered_ids:
                label = r.relation_type
                hover_text = f"{r.relation_type}\nQuality: {r.quality}"
                if r.position_a_to_b: hover_text += f"\nA->B: {r.position_a_to_b}"
                if r.position_b_to_a: hover_text += f"\nB->A: {r.position_b_to_a}"

                color = "gray"
                if r.quality == "良好": color = "green"
                elif r.quality == "険悪": color = "red"

                net.add_edge(r.person_a_id, r.person_b_id, title=hover_text, label=label, color=color)

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                net.save_graph(tmp.name)
                with open(tmp.name, 'r', encoding='utf-8') as f:
                    html_bytes = f.read()
                st.components.v1.html(html_bytes, height=600, scrolling=True)
            os.unlink(tmp.name)
        except Exception as e:
            st.error(f"グラフ描画中にエラーが発生しました: {e}")

elif page == "質問リスト":
    st.title("❓ プロファイリング質問リスト")

    mode = st.radio("モード", ["回答入力用リスト表示", "質問管理(追加・編集)", "CSVインポート/エクスポート"], horizontal=True)

    if mode == "回答入力用リスト表示":
        questions = get_all_questions(db)
        grouped_qs = {}
        for q in questions:
            if q.category not in grouped_qs:
                grouped_qs[q.category] = []
            grouped_qs[q.category].append(q)

        for cat, qs in grouped_qs.items():
            with st.expander(f"{cat}", expanded=True):
                for q in qs:
                    st.markdown(f"**Q:** {q.question_text}")
                    st.caption(f"判断基準: {q.judgment_criteria} | タイプ: {q.answer_type}")
                    st.divider()

    elif mode == "質問管理(追加・編集)":
        with st.form("add_question"):
            st.subheader("新規質問追加")
            q_text = st.text_input("質問文")
            q_cat = st.text_input("カテゴリ (例: MBTI, 価値観, 個人情報)")
            q_criteria = st.text_area("判断基準")
            q_type = st.selectbox("回答タイプ", ["scale", "text"])

            if st.form_submit_button("追加"):
                create_question(db, q_cat, q_text, q_criteria, q_type)
                st.success("追加しました")
                st.rerun()

        st.divider()
        st.subheader("既存の質問を編集/削除")
        questions = get_all_questions(db)
        for q in questions:
            with st.expander(f"ID:{q.id} {q.question_text[:20]}..."):
                with st.form(f"edit_q_{q.id}"):
                    e_text = st.text_input("質問文", value=q.question_text)
                    e_cat = st.text_input("カテゴリ", value=q.category)
                    e_crit = st.text_area("基準", value=q.judgment_criteria)
                    e_type = st.selectbox("タイプ", ["scale", "text"], index=0 if q.answer_type == "scale" else 1)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("更新"):
                            update_question(db, q.id, question_text=e_text, category=e_cat, judgment_criteria=e_crit, answer_type=e_type)
                            st.success("更新しました")
                            st.rerun()
                    with c2:
                        if st.form_submit_button("削除", type="primary"):
                            delete_question(db, q.id)
                            st.rerun()

    elif mode == "CSVインポート/エクスポート":
        st.subheader("エクスポート")
        questions = get_all_questions(db)
        if st.button("CSVダウンロード準備"):
            data = []
            for q in questions:
                data.append({
                    "category": q.category,
                    "question_text": q.question_text,
                    "judgment_criteria": q.judgment_criteria,
                    "answer_type": q.answer_type,
                    "target_trait": q.target_trait
                })
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="CSVをダウンロード",
                data=csv,
                file_name='questions.csv',
                mime='text/csv',
            )

        st.divider()
        st.subheader("インポート")
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv")
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df.head())
                if st.button("データベースに取り込み"):
                    count = 0
                    for index, row in df.iterrows():
                        if "question_text" in row and "category" in row:
                            create_question(
                                db,
                                category=row["category"],
                                question_text=row["question_text"],
                                judgment_criteria=row.get("judgment_criteria", ""),
                                answer_type=row.get("answer_type", "text"),
                                target_trait=row.get("target_trait", "")
                            )
                            count += 1
                    st.success(f"{count} 件の質問を取り込みました。")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
