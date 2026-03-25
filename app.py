import streamlit as st
import pandas as pd
import os
import datetime
import uuid

EXPENSE_FILE = "expenses.csv"
SCHEDULE_FILE = "schedule.csv"

# データの項目（削除用の「ID」と、経費用の「ステータス」を追加しています）
SCH_COLS = ["ID", "日付", "時間", "顧客名", "予定の内容", "担当者"]
EXP_COLS = ["ID", "日付", "項目", "金額", "支払った人", "ステータス"]

# データを読み込む関数（古いデータにも自動でIDなどを付与してエラーを防ぎます）
def load_data(file_name, columns):
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        for col in columns:
            if col not in df.columns:
                if col == "ステータス":
                    df[col] = "有効"
                elif col == "ID":
                    df[col] = [str(uuid.uuid4()) for _ in range(len(df))] # 古いデータにも一意のIDを付与
                else:
                    df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --------------------------------------------------
# ダイアログ（ポップアップ）の設定
# --------------------------------------------------
@st.dialog("⚠️ 削除の確認")
def confirm_delete_schedule(target_id, df):
    st.write("本当にこの予定を削除しますか？\nこの操作は元に戻せません。")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します"):
        # 対象のIDを除外して保存（完全削除）
        df = df[df["ID"] != target_id]
        save_data(df, SCHEDULE_FILE)
        st.success("削除しました！画面を更新します...")
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("⚠️ 削除（取り消し）の確認")
def confirm_delete_expense(target_id, df):
    st.write("この経費を「削除済み」にしますか？\n※データ自体は取り消し線付きで残ります。")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します"):
        # 該当IDのステータスを「削除済み」に変更（ソフトデリート）
        df.loc[df["ID"] == target_id, "ステータス"] = "削除済み"
        save_data(df, EXPENSE_FILE)
        st.success("削除済みに変更しました！画面を更新します...")
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

# --------------------------------------------------
# 1. メニュー（セレクトボックスからラジオボタンに変更）
# --------------------------------------------------
menu = st.sidebar.radio(
    "📂 メニュー",
    ["スケジュール確認", "スケジュール登録", "経費確認", "経費登録"]
)

st.title("阪竹行政書士事務所 共有アプリ")

# ==========================================
# 🗓️ スケジュール確認画面
# ==========================================
if menu == "スケジュール確認":
    st.header("🗓️ スケジュール確認")
    df_schedule = load_data(SCHEDULE_FILE, SCH_COLS)
    
    if df_schedule.empty:
        st.info("現在、登録されている予定はありません。")
    else:
        # 表示用に並び替え、裏側用の「ID列」は隠して表示
        display_df = df_schedule.sort_values(by=["日付", "時間"]).drop(columns=["ID"])
        st.dataframe(display_df, hide_index=True, use_container_width=True)
        
        # 2. 登録済みスケジュールの削除機能
        st.markdown("---")
        st.subheader("🗑️ 予定の削除")
        
        # プルダウンで見やすく表示するための設定
        def format_sch(sch_id):
            row = df_schedule[df_schedule["ID"] == sch_id].iloc[0]
            return f"{row['日付']} {row['時間']} | {row['予定の内容']} ({row['顧客名']})"
        
        selected_sch_id = st.selectbox(
            "削除したい予定を選んでください", 
            options=df_schedule["ID"].tolist(),
            format_func=format_sch
        )
        
        if st.button("選択した予定を削除"):
            confirm_delete_schedule(selected_sch_id, df_schedule) # ダイアログを呼び出し

# ==========================================
# 📝 スケジュール登録画面
# ==========================================
elif menu == "スケジュール登録":
    st.header("📝 スケジュール登録")
    df_schedule = load_data(SCHEDULE_FILE, SCH_COLS)
    
    with st.form("schedule_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付")
        with col2:
            time_val = st.time_input("時間", value=datetime.time(9, 0))
            
        customer = st.text_input("お客様 / 顧客名 (例: 〇〇様、〇〇株式会社など)")
        task = st.text_input("予定の内容 (例: 相続の初回面談、入管への申請手続きなど)")
        assignee = st.selectbox("担当者", ["全員", "阪口", "竹之内"])
        
        submit = st.form_submit_button("予定を追加")
        
    if submit:
        # 重複しない専用のID（UUID）を自動生成して保存
        new_data = pd.DataFrame([{
            "ID": str(uuid.uuid4()), 
            "日付": date, 
            "時間": time_val.strftime("%H:%M"), 
            "顧客名": customer, 
            "予定の内容": task, 
            "担当者": assignee
        }])
        df_schedule = pd.concat([df_schedule, new_data], ignore_index=True)
        save_data(df_schedule, SCHEDULE_FILE)
        st.success("✅ 予定を保存しました！「スケジュール確認」画面で一覧を見ることができます。")

# ==========================================
# 📊 経費確認画面（3. 経費も確認と登録に分割）
# ==========================================
elif menu == "経費確認":
    st.header("📊 経費確認")
    df_expense = load_data(EXPENSE_FILE, EXP_COLS)
    
    if df_expense.empty:
        st.info("現在、登録されている経費はありません。")
    else:
        # 4. 「削除済み」の行に取り消し線を引き、文字色をグレーにする装飾機能
        def highlight_deleted(row):
            if row.get("ステータス") == "削除済み":
                return ["color: #aaaaaa; text-decoration: line-through; background-color: #f9f9f9"] * len(row)
            return [""] * len(row)
        
        display_df_exp = df_expense.sort_values(by=["日付"], ascending=False).drop(columns=["ID"])
        # 作成した装飾機能（highlight_deleted）を表に適用して表示
        st.dataframe(display_df_exp.style.apply(highlight_deleted, axis=1), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗑️ 経費の削除（取り消し）")
        
        # すでに削除済みのものはリストに出さないようにする
        active_expenses = df_expense[df_expense["ステータス"] != "削除済み"]
        
        if active_expenses.empty:
            st.write("削除できる有効な経費データがありません。")
        else:
            def format_exp(exp_id):
                row = active_expenses[active_expenses["ID"] == exp_id].iloc[0]
                return f"{row['日付']} | {row['項目']} : {row['金額']}円 ({row['支払った人']})"
            
            selected_exp_id = st.selectbox(
                "削除（取り消し）したい経費を選んでください", 
                options=active_expenses["ID"].tolist(),
                format_func=format_exp
            )
            
            if st.button("選択した経費を削除"):
                confirm_delete_expense(selected_exp_id, df_expense)

# ==========================================
# 💰 経費登録画面
# ==========================================
elif menu == "経費登録":
    st.header("💰 経費登録")
    df_expense = load_data(EXPENSE_FILE, EXP_COLS)
    
    with st.form("expense_form", clear_on_submit=True):
        e_date = st.date_input("支払日")
        item = st.text_input("項目 (例: コピー用紙、交通費など)")
        amount = st.number_input("金額 (円)", min_value=0, step=100)
        payer = st.selectbox("支払った人", ["阪口", "竹之内"])
        e_submit = st.form_submit_button("経費を登録")
        
    if e_submit:
        new_data = pd.DataFrame([{
            "ID": str(uuid.uuid4()), 
            "日付": e_date, 
            "項目": item, 
            "金額": amount, 
            "支払った人": payer,
            "ステータス": "有効" # 初期設定は「有効」
        }])
        df_expense = pd.concat([df_expense, new_data], ignore_index=True)
        save_data(df_expense, EXPENSE_FILE)
        st.success("✅ 経費を保存しました！「経費確認」画面で一覧を見ることができます。")