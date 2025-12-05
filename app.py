import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import init_db, get_db, Person
from crud import (
    create_person, get_people, get_person, update_person,
    create_interaction, get_interactions_by_person,
    create_profiling_data, get_profiling_data_by_person,
    create_relationship, get_relationships_for_person,
    seed_questions, get_random_question
)

# --- Configuration & Setup ---
st.set_page_config(page_title="Human Relations CRM", layout="wide", page_icon="🧩")

# Initialize DB
init_db()
db = next(get_db())
seed_questions(db)

# --- Sidebar Navigation ---
st.sidebar.title("🧩 Menu")
page = st.sidebar.radio("Go to", ["People Directory", "Register Person", "Log Interaction", "Dashboard"])

# --- Helper Functions ---
def calculate_age(born):
    if not born:
        return "N/A"
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

# --- Pages ---

if page == "People Directory":
    st.title("📂 People Directory")

    people = get_people(db)

    if not people:
        st.info("No people registered yet. Go to 'Register Person' to add someone.")
    else:
        # Search bar
        search_query = st.text_input("Search by name", "")

        # Display as a table (using DataFrame for better sorting/filtering)
        data = []
        for p in people:
            if search_query.lower() in p.name.lower() or (p.nickname and search_query.lower() in p.nickname.lower()):
                data.append({
                    "ID": p.id,
                    "Name": p.name,
                    "Nickname": p.nickname,
                    "Status": p.status,
                    "Gender": p.gender,
                    "Age": calculate_age(p.birth_date),
                    "Last Interaction": "TODO" # Could be fetched via relationship
                })

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("### Quick Actions")
            selected_id = st.selectbox("Select a person to view/edit", [d["ID"] for d in data], format_func=lambda x: next(p.name for p in people if p.id == x))

            if st.button("Go to Dashboard"):
                st.session_state["selected_person_id"] = selected_id
                # Hacky way to switch page in Streamlit < 1.30 (or just notify user to switch)
                st.info(f"Selected {selected_id}. Please switch to 'Dashboard' tab manually (or implementation state logic).")
                # Better: Use query params or state management to auto-navigate if possible, but keeping it simple.
        else:
            st.warning("No matches found.")

elif page == "Register Person":
    st.title("👤 Register New Person")

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name (Required)")
            nickname = st.text_input("Nickname")
            gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Other", "Unknown"])
            blood_type = st.selectbox("Blood Type", ["A", "B", "O", "AB", "Unknown"])

        with col2:
            status = st.selectbox("Status", ["Acquaintance", "Friend", "Close Friend", "Colleague", "Family", "VIP", "Review Needed"])
            birth_date = st.date_input("Birth Date", value=None, min_value=date(1900, 1, 1))
            first_met_date = st.date_input("First Met Date", value=date.today())

        notes = st.text_area("Initial Notes")

        submitted = st.form_submit_button("Register")

        if submitted:
            if not name:
                st.error("Name is required.")
            else:
                create_person(db, name, nickname, birth_date, gender, blood_type, status, first_met_date, notes)
                st.success(f"Successfully registered {name}!")

elif page == "Log Interaction":
    st.title("📝 Log Interaction")

    people = get_people(db)
    if not people:
        st.error("Please register people first.")
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

        person_id = st.selectbox("Select Person", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

        tab1, tab2, tab3 = st.tabs(["Interaction", "Profiling Entry", "Add Relationship"])

        with tab1:
            with st.form("interaction_form"):
                col1, col2 = st.columns(2)
                with col1:
                    i_date = st.date_input("Date", value=date.today())
                    i_time = st.time_input("Time", value=datetime.now().time())
                with col2:
                    category = st.selectbox("Category", ["Conversation", "Meal", "Event", "Observation", "Contact"])
                    tags = st.text_input("Tags (comma separated, e.g., 'casual, work, angry')")

                content = st.text_area("Content / Details")
                user_feeling = st.text_area("Your Feeling / Memo")

                submitted_log = st.form_submit_button("Save Log")
                if submitted_log:
                    dt = datetime.combine(i_date, i_time)
                    create_interaction(db, person_id, category, content, tags, user_feeling, dt)
                    st.success("Interaction saved!")

        with tab2:
            with st.form("profiling_form"):
                st.subheader("Add Personality Analysis")
                framework = st.selectbox("Framework", ["MBTI", "Big5", "Enneagram", "VIA Strengths", "Other"])
                result = st.text_input("Result (e.g., 'INTJ', 'Openness High')")
                confidence = st.select_slider("Confidence Level", options=["C (Low)", "B", "A", "S (High)"])
                evidence = st.text_area("Evidence / Reason")

                submitted_prof = st.form_submit_button("Save Profiling Data")
                if submitted_prof:
                    create_profiling_data(db, person_id, framework, result, confidence, evidence)
                    st.success("Profiling data saved!")

        with tab3:
            with st.form("relation_form"):
                st.subheader("Add Relationship with Another Person")
                # Exclude current person
                other_people = {pid: name for pid, name in person_options.items() if pid != person_id}

                if not other_people:
                    st.warning("Need at least 2 people to form a relationship.")
                    submitted_rel = False
                else:
                    target_id = st.selectbox("Related to", options=other_people.keys(), format_func=lambda x: other_people[x])
                    rel_type = st.text_input("Relationship Type (e.g., Spouse, Rival, Ex-colleague)")
                    quality = st.selectbox("Quality", ["Good", "Neutral", "Bad", "Complicated"])

                    submitted_rel = st.form_submit_button("Save Relationship")

                if submitted_rel:
                    create_relationship(db, person_id, target_id, rel_type, quality)
                    st.success("Relationship saved!")


elif page == "Dashboard":
    people = get_people(db)
    if not people:
        st.warning("No people registered.")
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

        selected_id = st.sidebar.selectbox("Select Person for Dashboard", options=person_options.keys(), format_func=lambda x: person_options[x], index=default_index)

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
            st.caption(f"{person.nickname}" if person.nickname else "")
            st.markdown(f"**Status:** {person.status} | **Gender:** {person.gender} | **Age:** {calculate_age(person.birth_date)}")
            st.markdown(f"**Notes:** {person.notes}")

        st.divider()

        # --- LAYOUT ---
        col_main, col_side = st.columns([2, 1])

        with col_main:
            st.subheader("📅 Timeline")
            if interactions:
                for i in interactions:
                    with st.expander(f"{i.date.strftime('%Y-%m-%d')} - {i.category}"):
                        st.markdown(f"**Content:** {i.content}")
                        if i.tags:
                            st.caption(f"Tags: {i.tags}")
                        if i.user_feeling:
                            st.info(f"Feeling: {i.user_feeling}")
            else:
                st.info("No interactions logged yet.")

        with col_side:
            # --- Profiling ---
            st.subheader("🧠 Personality Profile")
            if profiling:
                for p_data in profiling:
                    st.success(f"**{p_data.framework}**: {p_data.result} (Conf: {p_data.confidence_level})")
                    if p_data.evidence:
                        st.caption(f"Ev: {p_data.evidence}")
            else:
                st.markdown("*No data yet.*")

            # --- Relationships ---
            st.subheader("🔗 Relationships")
            if relationships:
                for r in relationships:
                    # Determine who is the other person
                    other_id = r.person_b_id if r.person_a_id == person.id else r.person_a_id
                    other_p = next((p for p in people if p.id == other_id), None)
                    if other_p:
                        st.markdown(f"- **{other_p.name}**: {r.relation_type} ({r.quality})")
            else:
                st.markdown("*No relationships recorded.*")

            # --- Analysis Assist ---
            st.divider()
            st.subheader("💡 Analysis Assist")
            st.markdown("Try asking this to deepen understanding:")
            q = get_random_question(db)
            if q:
                st.info(f"**Target:** {q.target_trait}\n\nQ: {q.question_text}")
                with st.expander("Judgment Criteria"):
                    st.write(q.judgment_criteria)
                if st.button("New Question"):
                    st.rerun()
            else:
                st.write("No questions in database.")
