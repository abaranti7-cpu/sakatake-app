import streamlit as st
import pandas as pd
import os
import datetime

# 1. データを保存するファイルの名前
EXPENSE_FILE = "expenses.csv"
SCHEDULE_FILE = "schedule.csv"

# 2. データを読み込む・保存する関数
def load_data(file_name, columns):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)
    else:
        return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# 左側のサイドバーでメニューを作成（「スケジュール確認」を一番上に追加）
menu = st.sidebar.selectbox(
    "メニューを選択してください",
    ["スケジュール確認", "スケジュール登録", "経費管理"]
)

st.title("阪竹行政書士事務所 共有アプリ")

# ==========================================
# 🗓️ スケジュール確認画面（新設）
# ==========================================
if menu == "スケジュール確認":
    st.header("🗓️ スケジュール確認")
    st.write("登録された今後の予定一覧です。")
    
    # データを読み込み（項目が増えています）
    df_schedule = load_data(SCHEDULE_FILE, ["日付", "時間", "顧客名", "予定の内容", "担当者"])
    
    if df_schedule.empty:
        st.info("現在、登録されている予定はありません。")
    else:
        # 日付と時間で並び替え（古い順）て見やすくする
        df_schedule = df_schedule.sort_values(by=["日付", "時間"]).reset_index(drop=True)
        # 表として表示
        st.dataframe(df_schedule, hide_index=True, use_container_width=True)

# ==========================================
# 📝 スケジュール登録画面（項目追加）
# ==========================================
elif menu == "スケジュール登録":
    st.header("📝 スケジュール登録")
    
    df_schedule = load_data(SCHEDULE_FILE, ["日付", "時間", "顧客名", "予定の内容", "担当者"])
    
    with st.form("schedule_form", clear_on_submit=True):
        st.subheader("新しい予定の入力")
        
        # 日付と時間を横並びにして見やすくする
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付")
        with col2:
            time = st.time_input("時間", value=datetime.time(9, 0)) # デフォルトを9時に設定
            
        customer = st.text_input("お客様 / 顧客名 (例: 〇〇株式会社、〇〇様)")
        task = st.text_input("予定の内容 (例: 相続の初回面談、入管への申請手続きなど)")
        assignee = st.selectbox("担当者", ["全員", "阪口", "竹之内"])
        
        submit = st.form_submit_button("予定を追加")
        
    if submit:
        # 新しい項目を含めてデータを保存
        new_data = pd.DataFrame([{
            "日付": date, 
            "時間": time, 
            "顧客名": customer, 
            "予定の内容": task, 
            "担当者": assignee
        }])
        df_schedule = pd.concat([df_schedule, new_data], ignore_index=True)
        save_data(df_schedule, SCHEDULE_FILE)
        st.success("✅ 予定を保存しました！「スケジュール確認」画面で一覧を見ることができます。")

# ==========================================
# 💰 経費管理画面
# ==========================================
elif menu == "経費管理":
    st.header("💰 経費管理")
    
    df_expense = load_data(EXPENSE_FILE, ["日付", "項目", "金額", "支払った人"])
    
    with st.form("expense_form", clear_on_submit=True):
        st.subheader("経費の入力")
        e_date = st.date_input("支払日")
        item = st.text_input("項目 (例: コピー用紙、交通費など)")
        amount = st.number_input("金額 (円)", min_value=0, step=100)
        # 経費の担当者も竹之内さんに合わせて変更しました
        payer = st.selectbox("支払った人", ["阪口", "竹之内"])
        e_submit = st.form_submit_button("経費を登録")
        
    if e_submit:
        new_data = pd.DataFrame([{"日付": e_date, "項目": item, "金額": amount, "支払った人": payer}])
        df_expense = pd.concat([df_expense, new_data], ignore_index=True)
        save_data(df_expense, EXPENSE_FILE)
        st.success("✅ 経費を保存しました！")
        st.rerun()

    st.markdown("---")
    st.subheader("📝 経費一覧")
    st.dataframe(df_expense, hide_index=True, use_container_width=True)