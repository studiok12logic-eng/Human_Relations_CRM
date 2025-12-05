import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import streamlit.components.v1 as components
from pyvis.network import Network
import tempfile
import os
import random
from PIL import Image
from streamlit_cropper import st_cropper
from io import BytesIO

from database import init_db, get_db, Person, InteractionAnswer, ProfilingQuestion
from crud import (
    create_person, get_people, get_person, update_person, delete_person,
    create_interaction, get_interactions_by_person,
    create_profiling_data, get_profiling_data_by_person,
    create_relationship, get_relationships_for_person, get_all_relationships,
    seed_questions, get_random_question, get_all_questions,
    create_question, update_question, delete_question, get_question_answer_counts,
    create_person_history, get_person_history, delete_person_history
)

# --- Configuration & Setup ---
st.set_page_config(page_title="Human Relations CRM", layout="wide", page_icon="🧩")

# Initialize DB
init_db()
db = next(get_db())
seed_questions(db)

# --- Constants ---
RELATIONSHIP_TEMPLATES = [
    {"label": "親子", "forward": "親", "backward": "子", "type": "vertical"},
    {"label": "兄弟姉妹", "forward": "兄・姉", "backward": "弟・妹", "type": "vertical"},
    {"label": "夫婦・パートナー", "forward": "パートナー", "backward": "パートナー", "type": "horizontal"},
    {"label": "上司・部下", "forward": "上司", "backward": "部下", "type": "vertical"},
    {"label": "先輩・後輩", "forward": "先輩", "backward": "後輩", "type": "vertical"},
    {"label": "師弟", "forward": "師匠", "backward": "弟子", "type": "vertical"},
    {"label": "同僚", "forward": "同僚", "backward": "同僚", "type": "horizontal"},
    {"label": "友人", "forward": "友人", "backward": "友人", "type": "horizontal"},
    {"label": "ライバル", "forward": "ライバル", "backward": "ライバル", "type": "horizontal"},
]

# --- Navigation State Management ---
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "人物一覧"

def navigate_to(page_name):
    st.session_state["current_page"] = page_name

# --- Sidebar Navigation ---
st.sidebar.title("🧩 メニュー")
page_options = ["人物一覧", "人物登録", "交流ログ", "ダッシュボード", "相関図", "質問リスト"]

# Global Search
st.sidebar.markdown("---")
search_keyword = st.sidebar.text_input("🔍 全文検索", placeholder="名前、タグ、内容...")

# Page Selection
try:
    current_index = page_options.index(st.session_state["current_page"])
except ValueError:
    current_index = 0

page = st.sidebar.radio("移動", page_options, index=current_index, key="nav_radio")

if page != st.session_state["current_page"]:
    st.session_state["current_page"] = page
    st.rerun()

# --- Helper Functions ---
def calculate_age(born, birth_year=None, birth_month=None, birth_day=None):
    today = date.today()
    if born:
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    if birth_year and birth_month and birth_day:
        return today.year - birth_year - ((today.month, today.day) < (birth_month, birth_day))

    if birth_year:
        return today.year - birth_year # Rough estimate

    return "不明"

def get_last_interaction_date(person_id):
    interactions = get_interactions_by_person(db, person_id)
    if interactions:
        return interactions[0].entry_date
    return None

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        try:
            # Create assets/avatars directory if not exists
            upload_dir = "assets/avatars"
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename
            file_ext = os.path.splitext(uploaded_file.name)[1]
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}{file_ext}"
            file_path = os.path.join(upload_dir, filename)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            return file_path
        except Exception as e:
            st.error(f"画像の保存に失敗しました: {e}")
            return None
    return None

# --- Global Search Logic ---
if search_keyword:
    st.title("🔍 検索結果")
    st.write(f"検索キーワード: **{search_keyword}**")

    # Search People
    people = get_people(db)
    matched_people = []
    for p in people:
        target = f"{p.last_name} {p.first_name} {p.nickname} {p.tags} {p.status} {p.notes or ''} {p.prediction_notes or ''}"
        if search_keyword.lower() in target.lower():
            matched_people.append(p)

    if matched_people:
        st.subheader("👤 人物")
        for p in matched_people:
            with st.expander(f"{p.last_name} {p.first_name}"):
                st.write(f"ステータス: {p.status} | タグ: {p.tags}")
                if st.button("詳細へ", key=f"search_p_{p.id}"):
                    st.session_state["selected_person_id"] = p.id
                    navigate_to("ダッシュボード")
                    st.rerun()

    # Search Interactions
    # This is inefficient for large DBs but fine for local tool
    # Iterate all people to get interactions
    matched_interactions = []
    for p in people:
        interactions = get_interactions_by_person(db, p.id)
        for i in interactions:
            target = f"{i.content} {i.user_feeling or ''} {i.tags or ''} {i.category or ''} {i.channel or ''}"
            # Check answers
            for ans in i.answers:
                 target += f" {ans.answer_value}"

            if search_keyword.lower() in target.lower():
                matched_interactions.append(i)

    if matched_interactions:
        st.subheader("📝 交流ログ")
        for i in matched_interactions:
            p = next((x for x in people if x.id == i.person_id), None)
            name = f"{p.last_name} {p.first_name}" if p else "Unknown"
            with st.expander(f"{i.entry_date} - {name} ({i.category})"):
                st.write(i.content)
                if st.button("人物ダッシュボードへ", key=f"search_i_{i.id}"):
                    st.session_state["selected_person_id"] = i.person_id
                    navigate_to("ダッシュボード")
                    st.rerun()

    if not matched_people and not matched_interactions:
        st.warning("見つかりませんでした。")

    st.divider()

# --- Pages ---

if page == "人物一覧":
    # Header and View Mode
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.title("📂 人物一覧")
    with h_col2:
        view_mode = st.radio("表示形式", ["テーブル", "カード"], horizontal=True, label_visibility="collapsed")

    people = get_people(db)

    if not people:
        st.info("人物が登録されていません。「人物登録」から追加してください。")
    else:
        # Initialize session state for filters and search results
        if "pl_search_executed" not in st.session_state:
            st.session_state["pl_search_executed"] = False

        # Fixed 3 rows for filters
        # We use st.form to ensure search only triggers on submission
        filter_configs = []

        with st.form("person_list_search_form"):
            for i in range(3):
                fc1, fc2, fc3 = st.columns([2, 2, 3])
                with fc1:
                    st.selectbox(f"col_{i}", ["名前", "グループ", "ステータス", "性別", "年齢", "最終接触日"], key=f"f_col_{i}", label_visibility="collapsed")
                with fc2:
                    st.selectbox(f"op_{i}", ["含む", "一致する", "以上", "以下"], key=f"f_op_{i}", label_visibility="collapsed")
                with fc3:
                    st.text_input(f"val_{i}", key=f"f_val_{i}", label_visibility="collapsed", placeholder="値")

            # Centered Buttons inside form
            b_col_L, b_col_S, b_col_R, b_col_E = st.columns([1, 1, 1, 1])

            submitted_search = False
            submitted_reset = False

            with b_col_S:
                submitted_search = st.form_submit_button("🔍 検索", type="primary", use_container_width=True)
            with b_col_R:
                submitted_reset = st.form_submit_button("リセット", use_container_width=True)

            if submitted_search:
                st.session_state["pl_search_executed"] = True
                st.rerun()

            if submitted_reset:
                st.session_state["pl_search_executed"] = False
                # Manually clear session state keys for the inputs
                for i in range(3):
                    st.session_state[f"f_val_{i}"] = ""
                st.rerun()

        # Re-construct filter configs from session state (available after rerun or if persistent)
        for i in range(3):
            c = st.session_state.get(f"f_col_{i}")
            o = st.session_state.get(f"f_op_{i}")
            v = st.session_state.get(f"f_val_{i}")
            if v:
                filter_configs.append({"col": c, "op": o, "val": v})

        st.divider()

        # Sorting Logic (Session State)
        if "pl_sort_col" not in st.session_state:
            st.session_state["pl_sort_col"] = "名前"
        if "pl_sort_asc" not in st.session_state:
            st.session_state["pl_sort_asc"] = True

        # Apply Filters & Sort
        filtered_people = []
        today = date.today()

        # Decide source: if search executed, apply filters. Else, empty?
        # Requirement: "Until search button is pressed, do not search."
        # This usually means show nothing or show all?
        # Typically "do not search" means "show initial state" or "show nothing".
        # Given "Search and Reset", usually Reset shows all or Search shows filtered.
        # If "do not search until button pressed" implies the list should be empty initially?
        # Or does it mean "don't apply *new* filters until pressed"?
        # User said: "Until search execution button is pressed, do not search." (検索実行ボタンを押すまでは検索しない)
        # Often this means the list is empty or shows everything but doesn't react to typing immediately.
        # Context: "List page". Usually you want to see the list.
        # I will assume it means "don't re-filter on every keystroke" (which is standard Streamlit behavior if not using forms).
        # But wait, "Search row has 3 lines... do not search until pressed".
        # If I show all people by default, that's fine. If I show nothing, that's also valid.
        # Let's assume "Show all people initially (or previous search)" but "Don't update based on inputs until clicked".
        # Actually, if I use `st.session_state["pl_search_executed"]`, I can control this.
        # If not executed, maybe show all? Or show none?
        # Let's show ALL by default if no filters are active/pressed?
        # Or maybe the user wants an empty screen?
        # "Remove filter sorting in list... Remove add button... make 3 search rows... do not search until button pressed".
        # I'll stick to: Show all people if no search active (or reset), apply filters when Search is pressed.

        target_people = people

        if st.session_state["pl_search_executed"]:
            temp_filtered = []
            for p in target_people:
                match = True
                age = calculate_age(p.birth_date, p.birth_year, p.birth_month, p.birth_day)
                last_contact = get_last_interaction_date(p.id)

                for f in filter_configs:
                    val_to_check = ""
                    if f["col"] == "名前": val_to_check = f"{p.last_name} {p.first_name}"
                    elif f["col"] == "グループ": val_to_check = p.tags or ""
                    elif f["col"] == "ステータス": val_to_check = p.status or ""
                    elif f["col"] == "性別": val_to_check = p.gender or ""
                    elif f["col"] == "年齢": val_to_check = str(age)
                    elif f["col"] == "最終接触日": val_to_check = last_contact.strftime('%Y-%m-%d') if last_contact else ""

                    target_val = f["val"]

                    if f["op"] == "含む":
                        if target_val.lower() not in val_to_check.lower(): match = False
                    elif f["op"] == "一致する":
                        if target_val.lower() != val_to_check.lower(): match = False
                    elif f["op"] == "以上":
                        try:
                            if float(val_to_check) < float(target_val): match = False
                        except: match = False
                    elif f["op"] == "以下":
                        try:
                            if float(val_to_check) > float(target_val): match = False
                        except: match = False

                if match:
                    temp_filtered.append(p)
            filtered_people = temp_filtered
        else:
            filtered_people = people # Default show all? Or show none? I'll show all as it's a "List".

        # Sorting
        def sort_key(p):
            k = st.session_state["pl_sort_col"]
            val = ""
            if k == "名前": val = f"{p.last_name} {p.first_name}"
            elif k == "グループ": val = p.tags or "zzz"
            elif k == "ステータス": val = p.status or "zzz"
            elif k == "性別": val = p.gender or "zzz"
            elif k == "年齢": val = calculate_age(p.birth_date, p.birth_year, p.birth_month, p.birth_day)
            elif k == "最終接触":
                 d = get_last_interaction_date(p.id)
                 val = d.strftime('%Y-%m-%d') if d else "0000-00-00"
            return val

        filtered_people = sorted(filtered_people, key=sort_key, reverse=not st.session_state["pl_sort_asc"])

        if not filtered_people:
            st.warning("該当する人物が見つかりませんでした。")
        else:
            if view_mode == "テーブル":
                # Helper for header sort button
                def sort_header(col_name, label):
                    # Sort icon
                    icon = "↕"
                    if st.session_state["pl_sort_col"] == col_name:
                         icon = "▲" if st.session_state["pl_sort_asc"] else "▼"
                    if st.button(f"{label} {icon}", key=f"sort_btn_{col_name}", use_container_width=True):
                         if st.session_state["pl_sort_col"] == col_name:
                             st.session_state["pl_sort_asc"] = not st.session_state["pl_sort_asc"]
                         else:
                             st.session_state["pl_sort_col"] = col_name
                             st.session_state["pl_sort_asc"] = True
                         st.rerun()

                # Table Header with Sort Buttons and compacted layout
                # Columns: Icon(1), Name(2), Gender(1), Group(2), Age(1), Birthday(2), LastContact(2), Action(2)
                h0, h1, h2, h3, h4, h5, h6, h7 = st.columns([0.5, 2, 1, 2, 1, 2, 2, 2])
                with h0: st.write("") # Icon Header placeholder
                with h1: sort_header("名前", "名前")
                with h2: sort_header("性別", "性別")
                with h3: sort_header("グループ", "グループ")
                with h4: sort_header("年齢", "年齢")
                with h5: sort_header("誕生日", "誕生日") # No sort for this in crud yet properly but we'll map to something
                with h6: sort_header("最終接触", "最終接触")
                with h7: st.markdown("**操作**") # No sort

                st.divider()

                for p in filtered_people:
                    with st.container():
                        last_contact = get_last_interaction_date(p.id)
                        last_contact_str = last_contact.strftime('%Y-%m-%d') if last_contact else "なし"
                        age = calculate_age(p.birth_date, p.birth_year, p.birth_month, p.birth_day)

                        # Birthday Flag (1 month)
                        birthday_flag = ""
                        # Logic: if birth_month/day exists
                        if p.birth_month and p.birth_day:
                            # Simple check: is it within next 30 days?
                            b_date = date(today.year, p.birth_month, p.birth_day)
                            if b_date < today:
                                b_date = date(today.year + 1, p.birth_month, p.birth_day)

                            delta = (b_date - today).days
                            if 0 <= delta <= 30:
                                birthday_flag = "🎂"
                        elif p.birth_date:
                             # Legacy
                             b_date = date(today.year, p.birth_date.month, p.birth_date.day)
                             if b_date < today:
                                b_date = date(today.year + 1, p.birth_date.month, p.birth_date.day)
                             delta = (b_date - today).days
                             if 0 <= delta <= 30:
                                birthday_flag = "🎂"

                        # Last Contact Flag (3 months)
                        contact_flag = ""
                        if last_contact:
                            delta_days = (today - last_contact).days
                            if delta_days >= 90:
                                contact_flag = "⚠️" # 3 months

                        birthday_display = ""
                        if p.birth_year: birthday_display += f"{p.birth_year}年"
                        if p.birth_month: birthday_display += f"{p.birth_month}月"
                        if p.birth_day: birthday_display += f"{p.birth_day}日"
                        if not birthday_display and p.birth_date: birthday_display = p.birth_date.strftime('%Y/%m/%d')
                        if birthday_flag: birthday_display += f" {birthday_flag}"

                        c0, c1, c2, c3, c4, c5, c6, c7 = st.columns([0.5, 2, 1, 2, 1, 2, 2, 2])

                        # Icon
                        with c0:
                             if p.avatar_path and os.path.exists(p.avatar_path):
                                 st.image(p.avatar_path, use_container_width=True)
                             else:
                                 st.write("👤")

                        c1.write(f"{p.last_name} {p.first_name}")
                        c2.write(p.gender or "-")
                        c3.write(p.tags or "-")
                        c4.write(str(age))
                        c5.write(birthday_display or "-")
                        c6.write(f"{last_contact_str} {contact_flag}")

                        with c7:
                            b1, b2, b3 = st.columns(3)
                            with b1:
                                if st.button("詳細", key=f"det_{p.id}"):
                                    st.session_state["selected_person_id"] = p.id
                                    navigate_to("ダッシュボード")
                                    st.rerun()
                            with b2:
                                if st.button("編集", key=f"edit_{p.id}"):
                                    st.session_state["edit_person_id"] = p.id
                                    navigate_to("人物登録")
                                    st.rerun()
                            with b3:
                                if st.button("削除", key=f"del_{p.id}", type="primary"):
                                    delete_person(db, p.id)
                                    st.rerun()

            elif view_mode == "カード":
                cols = st.columns(3) # Adjust to 3 columns to give more space for internal layout
                for i, p in enumerate(filtered_people):
                    with cols[i % 3]:
                        with st.container(border=True):
                            # Internal Layout: Left (Icon) - Right (Info)
                            c_card_l, c_card_r = st.columns([1, 2])

                            with c_card_l:
                                if p.avatar_path and os.path.exists(p.avatar_path):
                                    st.image(p.avatar_path, use_container_width=True)
                                else:
                                    st.write("👤")

                            with c_card_r:
                                # Name (Kanji)
                                st.markdown(f"**{p.last_name} {p.first_name}**")
                                # Name (Kana) - small
                                yomi = f"{p.yomigana_last or ''} {p.yomigana_first or ''}".strip()
                                if yomi:
                                    st.caption(f"{yomi}")
                                # Nickname - small
                                if p.nickname:
                                    st.caption(f"({p.nickname})")

                                # Info
                                age = calculate_age(p.birth_date, p.birth_year, p.birth_month, p.birth_day)
                                last_contact = get_last_interaction_date(p.id)
                                lc_str = last_contact.strftime('%Y-%m-%d') if last_contact else "-"

                                st.markdown(f"<small>{p.gender or '-'} / {age}歳</small>", unsafe_allow_html=True)
                                st.markdown(f"<small>最終: {lc_str}</small>", unsafe_allow_html=True)

                            # Bottom Actions
                            b1, b2, b3 = st.columns(3)
                            with b1:
                                if st.button("詳細", key=f"c_det_{p.id}", use_container_width=True):
                                     st.session_state["selected_person_id"] = p.id
                                     navigate_to("ダッシュボード")
                                     st.rerun()
                            with b2:
                                if st.button("編集", key=f"c_edit_{p.id}", use_container_width=True):
                                     st.session_state["edit_person_id"] = p.id
                                     navigate_to("人物登録")
                                     st.rerun()
                            with b3:
                                if st.button("削除", key=f"c_del_{p.id}", type="primary", use_container_width=True):
                                     delete_person(db, p.id)
                                     st.rerun()

                            # Flags (Optional, maybe below or overlaid? User didn't specify position, but good to keep)
                            # Adding flags at bottom or overlay if needed.
                            # User said "Bottom: Detail, Edit, Delete". Flags can be small alerts above buttons or part of info.
                            # I'll put them above buttons if critical.
                            contact_flag = ""
                            if last_contact:
                                delta_days = (today - last_contact).days
                                if delta_days >= 90:
                                    st.caption("⚠️ 疎遠")


elif page == "人物登録":
    st.title("👤 人物登録・編集")

    # Initialize uploader key
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    existing_people = get_people(db)
    existing_self = next((p for p in existing_people if p.is_self), None)

    # Check for Edit Mode
    edit_mode_id = st.session_state.get("edit_person_id", None)
    edit_person_obj = None

    # Initialize defaults
    default_last = ""
    default_first = ""
    default_y_last = ""
    default_y_first = ""
    default_nick = ""
    default_gender = "不明"
    default_blood = "不明"
    default_is_self = False

    default_by = None
    default_bm = None
    default_bd = None
    default_fy = date.today().year
    default_fm = date.today().month
    default_fd = date.today().day

    default_notes = ""
    default_strategy = ""
    default_tags = []

    if edit_mode_id:
        edit_person_obj = get_person(db, edit_mode_id)
        if edit_person_obj:
            st.info(f"編集中: {edit_person_obj.last_name} {edit_person_obj.first_name}")
            default_last = edit_person_obj.last_name
            default_first = edit_person_obj.first_name
            default_y_last = edit_person_obj.yomigana_last or ""
            default_y_first = edit_person_obj.yomigana_first or ""
            default_nick = edit_person_obj.nickname or ""
            default_gender = edit_person_obj.gender or "不明"
            default_blood = edit_person_obj.blood_type or "不明"
            default_is_self = edit_person_obj.is_self

            default_by = edit_person_obj.birth_year
            default_bm = edit_person_obj.birth_month
            default_bd = edit_person_obj.birth_day

            default_fy = edit_person_obj.first_met_year
            default_fm = edit_person_obj.first_met_month
            default_fd = edit_person_obj.first_met_day

            default_notes = edit_person_obj.notes or ""
            default_strategy = edit_person_obj.strategy or ""
            if edit_person_obj.tags:
                default_tags = [t.strip() for t in edit_person_obj.tags.split(',')]

            # Avatar?
            # Handling existing avatar selection in session state is complex.
            # We will show current avatar.

    # Initialize session state for temporary tags
    if "reg_temp_tags" not in st.session_state:
        st.session_state["reg_temp_tags"] = []

    # Initialize session state for uploaded avatars
    if "reg_uploaded_avatars" not in st.session_state:
        st.session_state["reg_uploaded_avatars"] = []

    # Initialize session state for selected avatar
    if "reg_selected_avatar_index" not in st.session_state:
        st.session_state["reg_selected_avatar_index"] = None


    # Header with Is Self Checkbox
    c_head_1, c_head_2 = st.columns([3, 1])
    with c_head_1:
        st.subheader("基本情報")
    with c_head_2:
        # Is Self Check logic
        if existing_self and not (edit_person_obj and edit_person_obj.is_self):
            is_self = st.checkbox("自分の情報を登録する", value=False, disabled=True, help="既に自分が登録されています")
        else:
            is_self = st.checkbox("自分の情報を登録する", value=default_is_self)


    col_main_l, col_main_r = st.columns(2)

    # -- LEFT COLUMN (Basic Info) --
    with col_main_l:
        # Grouped Name Inputs: [Last Name Col] [First Name Col]
        c_n_last, c_n_first = st.columns(2)

        with c_n_last:
            last_name = st.text_input("姓", value=default_last, label_visibility="collapsed", placeholder="姓")
            yomigana_last = st.text_input("せい", value=default_y_last, label_visibility="collapsed", placeholder="せい")

        with c_n_first:
            first_name = st.text_input("名", value=default_first, label_visibility="collapsed", placeholder="名")
            yomigana_first = st.text_input("めい", value=default_y_first, label_visibility="collapsed", placeholder="めい")

        st.write("") # Spacer

        # Nick, Gender, Blood
        nickname = st.text_input("ニックネーム", value=default_nick, label_visibility="collapsed", placeholder="ニックネーム")

        c_l5, c_l6 = st.columns(2)
        with c_l5:
            g_opts = ["男性", "女性", "ノンバイナリー", "その他", "性別不明"]
            g_default_val = default_gender
            if g_default_val == "不明": g_default_val = "性別不明"

            g_idx = g_opts.index(g_default_val) if g_default_val in g_opts else 4
            # For selectbox, label_visibility="collapsed" is risky if not clear.
            # But requested.
            gender = st.selectbox("性別", g_opts, index=g_idx, label_visibility="collapsed")

        with c_l6:
            b_opts = ["A", "B", "O", "AB", "血液型不明"]
            b_default_val = default_blood
            if b_default_val == "不明": b_default_val = "血液型不明"

            b_idx = b_opts.index(b_default_val) if b_default_val in b_opts else 4
            blood_type = st.selectbox("血液型", b_opts, index=b_idx, label_visibility="collapsed")


    # -- RIGHT COLUMN (Group & Dates) --
    with col_main_r:
        # Group Logic
        all_tags = set()
        for p in existing_people:
            if p.tags:
                for t in p.tags.split(','):
                    all_tags.add(t.strip())
        for t in st.session_state["reg_temp_tags"]:
            all_tags.add(t)
        for t in default_tags:
            all_tags.add(t)
        tag_options = sorted(list(all_tags))

        selected_tags = st.multiselect("グループ", tag_options, default=default_tags, label_visibility="collapsed")

        # New Group Input & Button (Below)
        c_g_in, c_g_btn = st.columns([3, 1])
        with c_g_in:
            new_tag_input = st.text_input("グループ追加", label_visibility="collapsed", placeholder="新規グループ")
        with c_g_btn:
             if st.button("追加"):
                if new_tag_input and new_tag_input not in tag_options:
                    st.session_state["reg_temp_tags"].append(new_tag_input)
                    st.rerun()

        st.write("") # Spacer

        # Dates (Rows)
        # Row 1: Birth Date
        d_row1_1, d_row1_2 = st.columns([1, 4])
        with d_row1_1:
             st.write("生年月日")

        with d_row1_2:
             by_col, bm_col, bd_col = st.columns(3)
             with by_col:
                birth_year = st.number_input("年", min_value=1900, max_value=date.today().year, value=default_by, placeholder="不明", key="reg_by", label_visibility="collapsed")
             with bm_col:
                bm_idx = default_bm if default_bm else 0
                birth_month = st.selectbox("月", [None] + list(range(1, 13)), index=bm_idx, format_func=lambda x: f"{x}月" if x else "月", key="reg_bm", label_visibility="collapsed")
             with bd_col:
                bd_idx = default_bd if default_bd else 0
                birth_day = st.selectbox("日", [None] + list(range(1, 32)), index=bd_idx, format_func=lambda x: f"{x}日" if x else "日", key="reg_bd", label_visibility="collapsed")

        # Row 2: First Met
        d_row2_1, d_row2_2 = st.columns([1, 4])
        with d_row2_1:
             st.write("初対面日")

        with d_row2_2:
            if is_self:
                st.info("設定不要")
                first_met_year = None
                first_met_month = None
                first_met_day = None
            else:
                fy_col, fm_col, fd_col = st.columns(3)
                with fy_col:
                    first_met_year = st.number_input("年", min_value=1900, max_value=date.today().year, value=default_fy, placeholder="不明", key="reg_fy", label_visibility="collapsed")
                with fm_col:
                    fm_idx = default_fm if default_fm else 0
                    first_met_month = st.selectbox("月", [None] + list(range(1, 13)), index=fm_idx, format_func=lambda x: f"{x}月" if x else "月", key="reg_fm", label_visibility="collapsed")
                with fd_col:
                    fd_idx = default_fd if default_fd else 0
                    first_met_day = st.selectbox("日", [None] + list(range(1, 32)), index=fd_idx, format_func=lambda x: f"{x}日" if x else "日", key="reg_fd", label_visibility="collapsed")

    st.markdown("---")

    # -- ICON SECTION --
    st.subheader("アイコン設定")

    # Uploader with dynamic key to clear
    uploaded_avatar_file = st.file_uploader("画像をアップロード", type=["jpg", "png", "jpeg"], key=f"avatar_uploader_{st.session_state['uploader_key']}")

    if uploaded_avatar_file:
        img = Image.open(uploaded_avatar_file)
        w, h = img.size

        # Check Aspect Ratio (Allow small tolerance)
        # If not square, show cropper
        if abs(w - h) > 2:
            st.info("アスペクト比が1:1ではありません。切り抜き範囲を指定してください。")
            cropped_img = st_cropper(img, aspect_ratio=(1, 1), box_color='#FF0000')
            if st.button("切り抜きを確定して追加"):
                # Resize
                resized = cropped_img.resize((200, 200))
                # Save to session
                # Convert to bytes
                buf = BytesIO()
                resized.save(buf, format="PNG")
                byte_im = buf.getvalue()

                st.session_state["reg_uploaded_avatars"].append({
                    "name": f"crop_{uploaded_avatar_file.name}",
                    "bytes": byte_im
                })
                # Clear uploader
                st.session_state["uploader_key"] += 1
                st.rerun()
        else:
            # Already square. Resize and confirm?
            # User said "Image name should be hidden after upload".
            # So we should process it.
            # But to hide it, we must clear uploader, which requires rerun.
            # So we can auto-add it.
            resized = img.resize((200, 200))
            buf = BytesIO()
            resized.save(buf, format="PNG")
            byte_im = buf.getvalue()

            st.session_state["reg_uploaded_avatars"].append({
                "name": uploaded_avatar_file.name,
                "bytes": byte_im
            })
            st.session_state["uploader_key"] += 1
            st.rerun()


    # Display Images in Grid (8 per row)
    if st.session_state["reg_uploaded_avatars"]:
        st.write("画像を選択してください:")
        # Use simple iteration for grid
        cols = st.columns(8)
        for i, img_data in enumerate(st.session_state["reg_uploaded_avatars"]):
            with cols[i % 8]:
                st.image(img_data["bytes"], width=80) # Slightly smaller for 8 cols
                # Selection button
                label = "✔" if st.session_state["reg_selected_avatar_index"] == i else "〇"
                if st.button(label, key=f"sel_img_{i}", type="primary" if st.session_state["reg_selected_avatar_index"] == i else "secondary"):
                    st.session_state["reg_selected_avatar_index"] = i
                    st.rerun()

    st.markdown("---")

    # -- BOTTOM SECTION --
    notes = st.text_area("人物詳細 (旧: メモ)", value=default_notes)
    strategy = st.text_area("攻略方法", value=default_strategy)

    btn_label = "更新" if edit_mode_id else "登録"
    submitted = st.button(btn_label, type="primary")

    cancel_edit = False
    if edit_mode_id:
        if st.button("編集をキャンセル"):
            cancel_edit = True

    if cancel_edit:
        st.session_state["edit_person_id"] = None
        st.rerun()

    if submitted:
        if not last_name and not first_name:
            st.error("姓または名のどちらかは必須です。")
        else:
            # Handle tags
            final_tags = ", ".join(selected_tags)

            # Handle status
            status = "自分" if is_self else (edit_person_obj.status if edit_person_obj else "未設定")

            p_id_to_update = None

            # Prepare Dates
            b_y = int(birth_year) if birth_year else None
            b_m = birth_month
            b_d = birth_day

            f_y = int(first_met_year) if first_met_year else None
            f_m = first_met_month
            f_d = first_met_day

            # Legacy Date Calc
            legacy_b_date = None
            if b_y and b_m and b_d:
                try: legacy_b_date = date(b_y, b_m, b_d)
                except: pass

            legacy_f_date = None
            if f_y and f_m and f_d:
                try: legacy_f_date = date(f_y, f_m, f_d)
                except: pass

            if edit_mode_id:
                # Update
                update_person(db, edit_mode_id,
                              last_name=last_name, first_name=first_name,
                              yomigana_last=yomigana_last, yomigana_first=yomigana_first,
                              nickname=nickname, gender=gender, blood_type=blood_type,
                              status=status, notes=notes, tags=final_tags, is_self=is_self, strategy=strategy,
                              birth_year=b_y, birth_month=b_m, birth_day=b_d,
                              first_met_year=f_y, first_met_month=f_m, first_met_day=f_d,
                              birth_date=legacy_b_date, first_met_date=legacy_f_date) # Update legacy too
                p_id_to_update = edit_mode_id
                st.success(f"{last_name} {first_name} さんの情報を更新しました！")
                st.session_state["edit_person_id"] = None # Exit edit mode
            else:
                # Create Person
                new_p = create_person(db, last_name, first_name, yomigana_last, yomigana_first, nickname, legacy_b_date, gender, blood_type, status, legacy_f_date, notes, final_tags, None, is_self, strategy=strategy,
                                      birth_year=b_y,
                                      birth_month=b_m,
                                      birth_day=b_d,
                                      first_met_year=f_y,
                                      first_met_month=f_m,
                                      first_met_day=f_d)
                p_id_to_update = new_p.id
                st.success(f"{last_name} {first_name} さんを登録しました！")

            # Handle Avatar Logic
            final_avatar_path = None
            if st.session_state["reg_selected_avatar_index"] is not None:
                try:
                    selected_img_data = st.session_state["reg_uploaded_avatars"][st.session_state["reg_selected_avatar_index"]]

                    # Target folder: account/{id}/icon_imag/
                    target_dir = f"account/{p_id_to_update}/icon_imag"
                    os.makedirs(target_dir, exist_ok=True)

                    # Filename
                    # Keep original filename or generate? keeping original seems fine but safe to timestamp
                    file_ext = os.path.splitext(selected_img_data["name"])[1]
                    filename = f"icon{file_ext}" # Requirement says "click icon", not specific naming, but keeping it simple.
                    file_path = os.path.join(target_dir, filename)

                    with open(file_path, "wb") as f:
                        f.write(selected_img_data["bytes"])

                    final_avatar_path = file_path

                    # Update person with avatar path
                    update_person(db, p_id_to_update, avatar_path=final_avatar_path)

                except Exception as e:
                    st.error(f"画像保存エラー: {e}")

            if edit_mode_id:
                 # Clean up session for temp
                 pass

            # Reset temporary states
            st.session_state["reg_temp_tags"] = []
            st.session_state["reg_uploaded_avatars"] = []
            st.session_state["reg_selected_avatar_index"] = None

elif page == "交流ログ":
    st.title("📝 交流ログ")

    people = get_people(db)
    if not people:
        st.error("まずは人物を登録してください。")
    else:
        # Select Person
        person_options = {p.id: f"{p.last_name} {p.first_name}" for p in people}
        default_index = 0
        if "selected_person_id" in st.session_state and st.session_state["selected_person_id"] in person_options:
            try:
                ids = list(person_options.keys())
                default_index = ids.index(st.session_state["selected_person_id"])
            except ValueError:
                pass

        person_id = st.selectbox("人物を選択", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

        answer_counts = get_question_answer_counts(db, person_id)

        with st.form("interaction_form"):
            col1, col2 = st.columns(2)
            with col1:
                i_date = st.date_input("入力日", value=date.today())
                start_date_str = st.text_input("開始期間 (例: 2024/04/01, 2024年春)")
                end_date_str = st.text_input("終了期間 (例: 2024/04/05, 現在)")

            with col2:
                # Extended Categories
                cat_options = ["会話", "食事", "イベント", "観察", "連絡", "Gift/貸借", "Collaboration", "その他"]
                category = st.selectbox("カテゴリ", cat_options)
                category_new = st.text_input("カテゴリ追加 (上記にない場合)")
                if category_new:
                    category = category_new

                # Channel
                channel_options = ["対面 (In Person)", "通話 (Call/Remote)", "メッセージ (Text)", "観測 (Passive)"]
                channel = st.selectbox("接触手段 (Channel)", channel_options)

                tags = st.text_input("タグ (カンマ区切り)")

            content = st.text_area("内容 / 詳細")
            user_feeling = st.text_area("自分の感情 / メモ")

            st.divider()
            st.markdown("### 質問リストからの回答 (任意)")

            questions = get_all_questions(db)
            q_options = {q.id: f"{q.question_text} (回答数: {answer_counts.get(q.id, 0)})" for q in questions}
            selected_q_ids = st.multiselect("質問を選択", list(q_options.keys()), format_func=lambda x: q_options[x])

            answers = []
            for qid in selected_q_ids:
                q = next(q_ for q_ in questions if q_.id == qid)
                st.markdown(f"**Q: {q.question_text}**")

                # Check answer_type/input_type
                # Existing 'scale' or 'numeric' -> Slider
                # 'text' -> Text Input
                # 'selection' -> Selectbox

                atype = q.answer_type or "text"

                if atype in ['scale', 'numeric']:
                     val = st.select_slider(f"回答 ({q.id})", options=["0", "1", "3", "5"], key=f"ans_{qid}")
                     answers.append({'question_id': qid, 'answer_value': val})
                elif atype == 'selection':
                    opts = []
                    if q.options:
                        opts = [o.strip() for o in q.options.split(',')]
                    val = st.selectbox(f"回答 ({q.id})", options=opts, key=f"ans_{qid}")
                    answers.append({'question_id': qid, 'answer_value': val})
                else:
                    val = st.text_input(f"回答 ({q.id})", key=f"ans_{qid}")
                    answers.append({'question_id': qid, 'answer_value': val})

            submitted_log = st.form_submit_button("ログを保存")
            if submitted_log:
                create_interaction(db, person_id, category, content, tags, user_feeling, i_date, start_date_str, end_date_str, answers, channel)
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
        history = get_person_history(db, selected_id)

        # --- HEADER & EDIT ---
        with st.expander("👤 人物情報の編集", expanded=False):
            with st.form("edit_person_form"):
                new_last = st.text_input("姓", value=person.last_name)
                new_first = st.text_input("名", value=person.first_name)
                new_tags = st.text_input("グループ", value=person.tags or "")
                new_status = st.text_input("ステータス", value=person.status or "")
                new_notes = st.text_area("メモ", value=person.notes or "")
                new_prediction = st.text_area("性格分析予想 (付き合い方・考え方)", value=person.prediction_notes or "")

                # Update Avatar
                uploaded_avatar = st.file_uploader("アイコン画像更新", type=["jpg", "png", "jpeg"])

                st.markdown("---")
                st.write("経歴の追加")
                new_hist_date = st.text_input("日付 (例: 2010/04)")
                new_hist_content = st.text_input("内容")

                if st.form_submit_button("保存"):
                    new_avatar_path = person.avatar_path
                    if uploaded_avatar:
                        new_avatar_path = save_uploaded_file(uploaded_avatar)

                    update_person(db, person.id, last_name=new_last, first_name=new_first, tags=new_tags, status=new_status, notes=new_notes, prediction_notes=new_prediction)
                    # Need to update avatar separately or kwargs it? update_person takes kwargs
                    if new_avatar_path != person.avatar_path:
                        update_person(db, person.id, avatar_path=new_avatar_path)

                    if new_hist_content:
                        create_person_history(db, person.id, new_hist_date, new_hist_content)

                    st.success("更新しました。")
                    st.rerun()

                if st.form_submit_button("削除 (注意: 元に戻せません)", type="primary"):
                     delete_person(db, person.id)
                     st.warning("削除しました。")
                     st.rerun()

            # Manage History
            if history:
                st.markdown("##### 経歴の管理")
                for h in history:
                    c1, c2, c3 = st.columns([1, 4, 1])
                    with c1: st.write(h.date_str or "---")
                    with c2: st.write(h.content)
                    with c3:
                        if st.button("🗑️", key=f"del_hist_{h.id}"):
                            delete_person_history(db, h.id)
                            st.rerun()

        col_h1, col_h2 = st.columns([1, 3])
        with col_h1:
            if person.avatar_path:
                if os.path.exists(person.avatar_path):
                     st.image(person.avatar_path, width=150)
                elif person.avatar_path.startswith("http"):
                     st.image(person.avatar_path, width=150)
                else:
                     st.warning(f"画像が見つかりません: {person.avatar_path}")
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

            if history:
                with st.expander("📜 経歴", expanded=True):
                    for h in history:
                        st.markdown(f"- **{h.date_str or '---'}**: {h.content}")

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

                    # Icons based on Channel
                    icon = "📝"
                    if i.channel:
                        if "対面" in i.channel: icon = "🤝"
                        elif "通話" in i.channel: icon = "📞"
                        elif "メッセージ" in i.channel: icon = "💬"
                        elif "観測" in i.channel: icon = "👁️"

                    with st.expander(f"{icon} {date_display} - {i.category}"):
                        st.markdown(f"**手段:** {i.channel or '未設定'}")
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
                        caution = "⚠️" if r.caution_flag else ""
                        st.markdown(f"- {caution} **{other_p.last_name} {other_p.first_name}**: {r.relation_type} ({r.quality}){pos_str}")
            else:
                st.markdown("*関係性の記録なし*")

elif page == "相関図":
    st.title("🌐 人物相関図")

    people = get_people(db)
    if not people:
        st.warning("人物が登録されていません。")
    else:
        # --- Add Relationship Form ---
        with st.expander("🔗 関係性を追加する", expanded=True):
            with st.form("relation_page_form"):
                person_options = {p.id: f"{p.last_name} {p.first_name}" for p in people}
                col1, col2 = st.columns(2)

                default_p1_index = 0
                if "selected_person_id" in st.session_state and st.session_state["selected_person_id"] in person_options:
                     try:
                        ids = list(person_options.keys())
                        default_p1_index = ids.index(st.session_state["selected_person_id"])
                     except ValueError:
                        pass

                with col1:
                    p1_id = st.selectbox("人物 A (主体)", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p1", index=default_p1_index)
                with col2:
                    p2_id = st.selectbox("人物 B (対象)", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p2")

                # Template Selection
                template_labels = ["カスタム (手動入力)"] + [t["label"] for t in RELATIONSHIP_TEMPLATES]
                selected_template_label = st.selectbox("関係性テンプレート", template_labels)

                rel_type_default = ""
                pos_a_b_default = ""
                pos_b_a_default = ""

                if selected_template_label != "カスタム (手動入力)":
                    tmpl = next(t for t in RELATIONSHIP_TEMPLATES if t["label"] == selected_template_label)
                    rel_type_default = tmpl["label"]
                    pos_a_b_default = tmpl["forward"]
                    pos_b_a_default = tmpl["backward"]

                # We can't update text_input values dynamically easily within a form without session state hack or using `st.rerun` before form submit.
                # Since we are inside a form, `st.rerun` is tricky.
                # However, the user requirement is "Allow user to select".
                # If they select a template, we can just use those values if the text inputs are empty, or we can assume the inputs are for override.
                # Better UX: Show the template values as help or use them in backend if custom input is empty.
                # But to make it editable, we should probably output the values.
                # Limitation: Streamlit forms don't update widgets based on other widgets inside the form easily.
                # So I'll put the template selector OUTSIDE the form or just accept that the text inputs need to be filled manually OR handled by logic.
                # Let's try putting template selector inside, but we can't pre-fill the text inputs dynamically.
                # Solution: If template is selected, ignore text inputs OR use them if filled?
                # Best approach for this limitation: Use separate submit button for template vs custom? No.
                # I will trust the user to type if Custom, or I will use the template values if provided.

                # RE-DESIGN: Move Template Selection outside form?
                # If I move it outside, I can update session state defaults for the form.

            # --- Better Form Design for Templates ---
            c_temp, c_dummy = st.columns([1, 1])
            with c_temp:
                 template_labels = ["カスタム (手動入力)"] + [t["label"] for t in RELATIONSHIP_TEMPLATES]
                 # We need `st.selectbox` to trigger rerun to update defaults
                 selected_template = st.selectbox("テンプレートから選択", template_labels)

            # Determine default values
            def_rel = ""
            def_ab = ""
            def_ba = ""

            if selected_template != "カスタム (手動入力)":
                tmpl = next(t for t in RELATIONSHIP_TEMPLATES if t["label"] == selected_template)
                def_rel = tmpl["label"]
                def_ab = tmpl["forward"]
                def_ba = tmpl["backward"]

            with st.form("relation_save_form"):
                 # Re-declare P1/P2 inside form or pass them? P1/P2 selection should be inside form or persistent.
                 # Let's put everything in the form but use `value=` with the determined defaults.
                 # Note: changing `value` of a widget with same key only works if the widget is re-rendered.

                 c1, c2 = st.columns(2)
                 with c1:
                    p1_id = st.selectbox("人物 A", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p1_final", index=default_p1_index)
                 with c2:
                    p2_id = st.selectbox("人物 B", options=person_options.keys(), format_func=lambda x: person_options[x], key="rel_p2_final")

                 col3, col4 = st.columns(2)
                 with col3:
                    rel_type = st.text_input("関係性", value=def_rel)
                    quality = st.selectbox("関係の質", ["良好", "普通", "険悪", "複雑"])
                 with col4:
                     caution_flag = st.checkbox("⚠️ 混ぜるな危険 (Caution Flag)", help="相関図で赤色の破線で表示されます")

                 col5, col6 = st.columns(2)
                 with col5:
                    pos_a_b = st.text_input("Aから見たBの立場", value=def_ab)
                 with col6:
                    pos_b_a = st.text_input("Bから見たAの立場", value=def_ba)

                 submitted_rel = st.form_submit_button("関係を保存")

                 if submitted_rel:
                    if p1_id == p2_id:
                        st.error("同一人物間の関係は登録できません。")
                    else:
                        create_relationship(db, p1_id, p2_id, rel_type, quality, pos_a_b, pos_b_a, caution_flag)
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

            # Caution alert in node if needed? No, user asked for edges.

            shape = "box"
            image = None
            if p.avatar_path and os.path.exists(p.avatar_path):
                 shape = "circularImage"
                 image = p.avatar_path
            elif p.avatar_path and p.avatar_path.startswith("http"):
                 shape = "circularImage"
                 image = p.avatar_path

            net.add_node(p.id, label=label, title=title, color=color, shape=shape, image=image)

        for r in relationships:
            if r.person_a_id in filtered_ids and r.person_b_id in filtered_ids:
                label = r.relation_type
                hover_text = f"{r.relation_type}\nQuality: {r.quality}"
                if r.position_a_to_b: hover_text += f"\nA->B: {r.position_a_to_b}"
                if r.position_b_to_a: hover_text += f"\nB->A: {r.position_b_to_a}"
                if r.caution_flag: hover_text += "\n⚠️ CAUTION / NG"

                color = "gray"
                dashes = False

                if r.quality == "良好": color = "green"
                elif r.quality == "険悪": color = "red"

                if r.caution_flag:
                    color = "red"
                    dashes = True

                net.add_edge(r.person_a_id, r.person_b_id, title=hover_text, label=label, color=color, dashes=dashes)

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
                    if q.options:
                        st.caption(f"選択肢: {q.options}")
                    st.divider()

    elif mode == "質問管理(追加・編集)":
        with st.form("add_question"):
            st.subheader("新規質問追加")
            q_text = st.text_input("質問文")
            q_cat = st.text_input("カテゴリ (例: MBTI, 価値観, 個人情報, NG項目)")
            q_criteria = st.text_area("判断基準")

            # New Input Types
            type_map = {"数値 (Scale)": "numeric", "自由記述 (Text)": "text", "選択式 (Selection)": "selection"}
            q_type_label = st.selectbox("回答タイプ", list(type_map.keys()))
            q_type = type_map[q_type_label]

            q_options = st.text_input("選択肢 (カンマ区切り, 選択式のみ有効)")

            if st.form_submit_button("追加"):
                create_question(db, q_cat, q_text, q_criteria, q_type, options=q_options)
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

                    # Reverse Map
                    rev_map = {v: k for k, v in type_map.items()}
                    current_label = rev_map.get(q.answer_type, "自由記述 (Text)")

                    # Find index
                    try:
                        idx = list(type_map.keys()).index(current_label)
                    except:
                        idx = 1 # text

                    e_type_label = st.selectbox("タイプ", list(type_map.keys()), index=idx)
                    e_type = type_map[e_type_label]

                    e_options = st.text_input("選択肢", value=q.options or "")

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("更新"):
                            update_question(db, q.id, question_text=e_text, category=e_cat, judgment_criteria=e_crit, answer_type=e_type, options=e_options)
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
                    "options": q.options,
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
                                options=row.get("options", ""),
                                target_trait=row.get("target_trait", "")
                            )
                            count += 1
                    st.success(f"{count} 件の質問を取り込みました。")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
