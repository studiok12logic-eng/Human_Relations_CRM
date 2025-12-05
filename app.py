import streamlit as st
import pandas as pd
from datetime import datetime, date
import streamlit.components.v1 as components
from pyvis.network import Network
import tempfile
import os

from database import init_db, get_db, Person
from crud import (
    create_person, get_people, get_person, update_person,
    create_interaction, get_interactions_by_person,
    create_profiling_data, get_profiling_data_by_person,
    create_relationship, get_relationships_for_person, get_all_relationships,
    seed_questions, seed_mbti_questions, get_random_question, get_all_questions
)

# --- Configuration & Setup ---
st.set_page_config(page_title="Human Relations CRM", layout="wide", page_icon="🧩")

# Initialize DB
init_db()
db = next(get_db())
seed_questions(db)
seed_mbti_questions(db)

# --- Sidebar Navigation ---
st.sidebar.title("🧩 メニュー")
page = st.sidebar.radio("移動", ["人物一覧", "人物登録", "交流ログ", "ダッシュボード", "相関図", "質問リスト"])

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
        # Search bar
        search_query = st.text_input("名前で検索", "")

        # Display as a table (using DataFrame for better sorting/filtering)
        data = []
        for p in people:
            if search_query.lower() in p.name.lower() or (p.nickname and search_query.lower() in p.nickname.lower()):
                data.append({
                    "ID": p.id,
                    "名前": p.name,
                    "ニックネーム": p.nickname,
                    "グループ/タグ": p.tags,
                    "MBTI": p.mbti_result,
                    "ステータス": p.status,
                    "性別": p.gender,
                    "年齢": calculate_age(p.birth_date),
                })

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("### クイックアクション")
            selected_id = st.selectbox("詳細を見る人物を選択", [d["ID"] for d in data], format_func=lambda x: next(p.name for p in people if p.id == x))

            if st.button("ダッシュボードへ移動"):
                st.session_state["selected_person_id"] = selected_id
                st.info(f"ID: {selected_id} を選択しました。「ダッシュボード」タブに移動してください。")
        else:
            st.warning("見つかりませんでした。")

elif page == "人物登録":
    st.title("👤 新規人物登録")

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("名前 (必須)")
            nickname = st.text_input("ニックネーム")
            gender = st.selectbox("性別", ["男性", "女性", "ノンバイナリー", "その他", "不明"])
            blood_type = st.selectbox("血液型", ["A", "B", "O", "AB", "不明"])
            tags = st.text_input("グループ/タグ (例: 〇〇家, 〇〇高校同級生)")

        with col2:
            status = st.selectbox("ステータス", ["知人", "友人", "親友", "同僚", "家族", "VIP", "要レビュー"])
            birth_date = st.date_input("生年月日", value=None, min_value=date(1900, 1, 1))
            first_met_date = st.date_input("初対面日", value=date.today())
            mbti_result = st.text_input("MBTI結果 (例: INFP)")

        notes = st.text_area("メモ")

        submitted = st.form_submit_button("登録")

        if submitted:
            if not name:
                st.error("名前は必須です。")
            else:
                create_person(db, name, nickname, birth_date, gender, blood_type, status, first_met_date, notes, tags, mbti_result)
                st.success(f"{name} さんを登録しました！")

elif page == "交流ログ":
    st.title("📝 交流ログ")

    people = get_people(db)
    if not people:
        st.error("まずは人物を登録してください。")
    else:
        # Select Person
        person_options = {p.id: f"{p.name} ({p.nickname})" if p.nickname else p.name for p in people}
        # Pre-select if passed from other page
        default_index = 0
        if "selected_person_id" in st.session_state:
            try:
                ids = list(person_options.keys())
                default_index = ids.index(st.session_state["selected_person_id"])
            except ValueError:
                pass

        person_id = st.selectbox("人物を選択", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

        tab1, tab2 = st.tabs(["交流記録", "プロファイリング入力"])

        with tab1:
            with st.form("interaction_form"):
                col1, col2 = st.columns(2)
                with col1:
                    i_date = st.date_input("日付", value=date.today())
                    i_time = st.time_input("時間", value=datetime.now().time())
                with col2:
                    category = st.selectbox("カテゴリ", ["会話", "食事", "イベント", "観察", "連絡"])
                    tags = st.text_input("タグ (カンマ区切り, 例: 仕事, 飲み会)")

                content = st.text_area("内容 / 詳細")
                user_feeling = st.text_area("自分の感情 / メモ")

                submitted_log = st.form_submit_button("ログを保存")
                if submitted_log:
                    dt = datetime.combine(i_date, i_time)
                    create_interaction(db, person_id, category, content, tags, user_feeling, dt)
                    st.success("交流ログを保存しました！")

        with tab2:
            with st.form("profiling_form"):
                st.subheader("性格分析データの追加")
                framework = st.selectbox("フレームワーク", ["MBTI", "Big5", "エニアグラム", "VIA強み", "その他"])
                result = st.text_input("結果 (例: 'INTJ', '開放性が高い')")
                confidence = st.select_slider("確信度", options=["C (低)", "B", "A", "S (高)"])
                evidence = st.text_area("根拠 / 理由")

                submitted_prof = st.form_submit_button("プロファイリングデータを保存")
                if submitted_prof:
                    create_profiling_data(db, person_id, framework, result, confidence, evidence)
                    st.success("データを保存しました！")

elif page == "ダッシュボード":
    people = get_people(db)
    if not people:
        st.warning("人物が登録されていません。")
    else:
        # Sidebar selection for dashboard to keep main area clean
        person_options = {p.id: f"{p.name}" for p in people}

        # Determine selection
        default_index = 0
        if "selected_person_id" in st.session_state:
             try:
                ids = list(person_options.keys())
                default_index = ids.index(st.session_state["selected_person_id"])
             except ValueError:
                pass

        selected_id = st.sidebar.selectbox("ダッシュボード表示対象", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

        # Load Data
        person = get_person(db, selected_id)
        interactions = get_interactions_by_person(db, selected_id)
        profiling = get_profiling_data_by_person(db, selected_id)
        relationships = get_relationships_for_person(db, selected_id)

        # --- HEADER ---
        col_h1, col_h2 = st.columns([1, 3])
        with col_h1:
            st.image("https://placehold.co/150x150?text=Avatar", width=150) # Placeholder
        with col_h2:
            st.title(f"{person.name}")
            if person.nickname:
                st.caption(f"{person.nickname}")

            # Display MBTI and Group
            if person.mbti_result:
                st.info(f"MBTI: **{person.mbti_result}**")
            if person.tags:
                st.write(f"🏷️ グループ: {person.tags}")

            st.markdown(f"**ステータス:** {person.status} | **性別:** {person.gender} | **年齢:** {calculate_age(person.birth_date)}")
            st.markdown(f"**メモ:** {person.notes}")

        st.divider()

        # --- LAYOUT ---
        col_main, col_side = st.columns([2, 1])

        with col_main:
            st.subheader("📅 タイムライン")
            if interactions:
                for i in interactions:
                    with st.expander(f"{i.date.strftime('%Y-%m-%d')} - {i.category}"):
                        st.markdown(f"**内容:** {i.content}")
                        if i.tags:
                            st.caption(f"タグ: {i.tags}")
                        if i.user_feeling:
                            st.info(f"感情: {i.user_feeling}")
            else:
                st.info("交流ログはまだありません。")

        with col_side:
            # --- Profiling ---
            st.subheader("🧠 性格分析")
            if profiling:
                for p_data in profiling:
                    st.success(f"**{p_data.framework}**: {p_data.result} (確信度: {p_data.confidence_level})")
                    if p_data.evidence:
                        st.caption(f"根拠: {p_data.evidence}")
            else:
                st.markdown("*データなし*")

            # --- Relationships ---
            st.subheader("🔗 関係性")
            if relationships:
                for r in relationships:
                    # Determine who is the other person
                    other_id = r.person_b_id if r.person_a_id == person.id else r.person_a_id
                    other_p = next((p for p in people if p.id == other_id), None)
                    if other_p:
                        st.markdown(f"- **{other_p.name}**: {r.relation_type} ({r.quality})")
            else:
                st.markdown("*関係性の記録なし*")

            # --- Analysis Assist ---
            st.divider()
            st.subheader("💡 分析アシスト")
            st.markdown("理解を深めるために質問してみましょう:")
            q = get_random_question(db)
            if q:
                st.info(f"**対象:** {q.target_trait}\n\nQ: {q.question_text}")
                with st.expander("判断基準"):
                    st.write(q.judgment_criteria)
                if st.button("次の質問"):
                    st.rerun()
            else:
                st.write("質問データベースが空です。")

elif page == "相関図":
    st.title("🌐 人物相関図")

    people = get_people(db)
    if not people:
        st.warning("人物が登録されていません。")
    else:
        # --- Add Relationship Form ---
        with st.expander("🔗 関係性を追加する", expanded=False):
            with st.form("relation_page_form"):
                person_options = {p.id: p.name for p in people}
                col1, col2, col3 = st.columns(3)

                with col1:
                    p1_id = st.selectbox("人物 A", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p1")
                with col2:
                    p2_id = st.selectbox("人物 B", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p2")
                with col3:
                    rel_type = st.text_input("関係性 (例: 配偶者, ライバル)")

                quality = st.selectbox("関係の質", ["良好", "普通", "険悪", "複雑"])

                submitted_rel = st.form_submit_button("関係を保存")

                if submitted_rel:
                    if p1_id == p2_id:
                        st.error("同一人物間の関係は登録できません。")
                    else:
                        create_relationship(db, p1_id, p2_id, rel_type, quality)
                        st.success("関係性を保存しました！")

        st.divider()

        # --- Visualization Controls ---
        filter_mode = st.radio("表示モード", ["全体", "グループ(チャンク)別", "特定の人物中心"], horizontal=True)

        selected_chunk = None
        center_person_id = None

        if filter_mode == "グループ(チャンク)別":
            # Extract all unique tags
            all_tags = set()
            for p in people:
                if p.tags:
                    # Handle comma separated tags
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

        # Filter nodes and edges based on mode
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")

        # Dictionary to keep track of added nodes to avoid duplicates
        added_nodes = set()

        filtered_people = []

        if filter_mode == "全体":
            filtered_people = people
        elif filter_mode == "グループ(チャンク)別" and selected_chunk:
            filtered_people = [p for p in people if p.tags and selected_chunk in [t.strip() for t in p.tags.split(',')]]
        elif filter_mode == "特定の人物中心" and center_person_id:
            # Get center person and their direct connections
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

        # Add Nodes
        for p in filtered_people:
            # Create a label with name and maybe MBTI/Group
            label = p.name
            title = f"Name: {p.name}\nStatus: {p.status}\nMBTI: {p.mbti_result}\nGroup: {p.tags}"
            color = "#97c2fc"
            if p.id == center_person_id:
                color = "#ffb3b3" # Highlight center

            net.add_node(p.id, label=label, title=title, color=color)
            added_nodes.add(p.id)

        # Add Edges
        # Only add edges if both nodes are in the filtered list
        filtered_ids = {p.id for p in filtered_people}

        for r in relationships:
            if r.person_a_id in filtered_ids and r.person_b_id in filtered_ids:
                label = r.relation_type
                color = "gray"
                if r.quality == "良好": color = "green"
                elif r.quality == "険悪": color = "red"

                net.add_edge(r.person_a_id, r.person_b_id, title=r.relation_type, label=label, color=color)

        # Visualization
        try:
            # Streamlit components for Pyvis
            # Save and read graph as HTML file (PyVis quirk with Streamlit)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                net.save_graph(tmp.name)
                with open(tmp.name, 'r', encoding='utf-8') as f:
                    html_bytes = f.read()

                st.components.v1.html(html_bytes, height=600, scrolling=True)

            # Cleanup temp file
            os.unlink(tmp.name)

        except Exception as e:
            st.error(f"グラフ描画中にエラーが発生しました: {e}")

elif page == "質問リスト":
    st.title("❓ プロファイリング質問リスト")
    st.markdown("相手のことをより深く知るための質問集です。")

    questions = get_all_questions(db)

    # Group by trait
    grouped_qs = {}
    for q in questions:
        if q.target_trait not in grouped_qs:
            grouped_qs[q.target_trait] = []
        grouped_qs[q.target_trait].append(q)

    for trait, qs in grouped_qs.items():
        with st.expander(f"{trait} に関する質問", expanded=True):
            for q in qs:
                st.markdown(f"**Q:** {q.question_text}")
                st.caption(f"判断基準: {q.judgment_criteria}")
                st.divider()
