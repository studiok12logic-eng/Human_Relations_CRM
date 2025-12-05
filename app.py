import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- データベース周りの関数 ---
def init_db():
    """データベースとテーブルがあれば接続、なければ作成する"""
    conn = sqlite3.connect('human_crm.db')
    c = conn.cursor()
    # テーブル作成（まだなければ）
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            name TEXT,
            category TEXT,
            content TEXT,
            appearance TEXT,
            expression TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_log(name, category, content, appearance, expression):
    """データをDBに保存する"""
    conn = sqlite3.connect('human_crm.db')
    c = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO logs (date, name, category, content, appearance, expression) VALUES (?, ?, ?, ?, ?, ?)',
              (date_str, name, category, content, appearance, expression))
    conn.commit()
    conn.close()

def get_logs():
    """全データを取得してDataFrameで返す"""
    conn = sqlite3.connect('human_crm.db')
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC", conn)
    conn.close()
    return df

# --- アプリ本体 ---
st.set_page_config(page_title="Human CRM v2", layout="wide")
init_db()  # 起動時にDBがあるか確認

st.title("🧩 Human Relations CRM (SQLite版)")
mode = st.radio("Mode", ["ログ入力", "データ閲覧"], horizontal=True)

if mode == "ログ入力":
    with st.form("log_form"):
        name = st.text_input("名前")
        category = st.selectbox("カテゴリ", ["会話", "観察", "食事", "連絡"])
        content = st.text_area("内容・気づき")
        with st.expander("観察メモ（服装・表情など）"):
            appearance = st.text_input("服装・外見")
            expression = st.text_input("表情・癖")
            
        submitted = st.form_submit_button("記録する")
        
        if submitted:
            add_log(name, category, content, appearance, expression)
            st.success(f"{name}さんのログをDBに保存しました！")

else:
    st.subheader("📝 データベースの中身")
    df = get_logs()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("まだ記録がありません。")