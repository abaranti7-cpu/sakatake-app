import streamlit as st
import pandas as pd
import os

# 1. データを保存するファイルの名前を指定します
EXPENSE_FILE = "expenses.csv"
SCHEDULE_FILE = "schedule.csv"

# 2. データを読み込む・保存する「裏方の仕組み（関数）」を作ります
def load_data(file_name, columns):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)
    else:
        # ファイルがない場合（最初）は、空の表を作ります
        return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# 左側のサイドバーでメニューを作成
menu = st.sidebar.selectbox("メニューを選択してください", ["スケジュール", "経費管理"])
st.title("阪竹行政書士事務所 共有アプリ")

# ==========================================
# スケジュール管理画面
# ==========================================
if menu == "スケジュール":
    st.header("📅 スケジュール管理")
    
    # 保存されている予定データを読み込む
    df_schedule = load_data(SCHEDULE_FILE, ["日付", "予定の内容", "担当者"])
    
    with st.form("schedule_form", clear_on_submit=True):
        st.subheader("新しい予定の登録")
        date = st.date_input("日付")
        task = st.text_input("予定の内容 (例: 相続の面談、入管への申請など)")
        assignee = st.selectbox("担当者", ["阪口", "補助スタッフ"])
        submit = st.form_submit_button("予定を追加")
        
    if submit:
        # 入力されたデータを新しい行として追加し、保存する
        new_data = pd.DataFrame([{"日付": date, "予定の内容": task, "担当者": assignee}])
        df_schedule = pd.concat([df_schedule, new_data], ignore_index=True)
        save_data(df_schedule, SCHEDULE_FILE)
        st.success("✅ 予定を保存しました！")
        st.rerun() # 画面をリロードして最新の表を表示

    st.markdown("---")
    st.subheader("📝 予定一覧")
    # 読み込んだデータを表として表示
    st.dataframe(df_schedule, hide_index=True, use_container_width=True)

# ==========================================
# 経費管理画面
# ==========================================
elif menu == "経費管理":
    st.header("💰 経費管理")
    
    # 保存されている経費データを読み込む
    df_expense = load_data(EXPENSE_FILE, ["日付", "項目", "金額", "支払った人"])
    
    with st.form("expense_form", clear_on_submit=True):
        st.subheader("経費の入力")
        e_date = st.date_input("支払日")
        item = st.text_input("項目 (例: コピー用紙、交通費など)")
        amount = st.number_input("金額 (円)", min_value=0, step=100)
        payer = st.selectbox("支払った人", ["阪口", "補助スタッフ"])
        e_submit = st.form_submit_button("経費を登録")
        
    if e_submit:
        # 入力されたデータを新しい行として追加し、保存する
        new_data = pd.DataFrame([{"日付": e_date, "項目": item, "金額": amount, "支払った人": payer}])
        df_expense = pd.concat([df_expense, new_data], ignore_index=True)
        save_data(df_expense, EXPENSE_FILE)
        st.success("✅ 経費を保存しました！")
        st.rerun() # 画面をリロードして最新の表を表示

    st.markdown("---")
    st.subheader("📝 経費一覧")
    # 読み込んだデータを表として表示
    st.dataframe(df_expense, hide_index=True, use_container_width=True)