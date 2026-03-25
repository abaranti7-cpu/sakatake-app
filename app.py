import streamlit as st
import pandas as pd
import os
import datetime
import uuid
import calendar

EXPENSE_FILE = "expenses.csv"
SCHEDULE_FILE = "schedule.csv"

# 並び順のご要望に合わせて列を定義（スケジュールにもステータスを追加）
SCH_COLS = ["ID", "日付", "時間", "予定の内容", "顧客名", "担当者", "ステータス"]
EXP_COLS = ["ID", "日付", "項目", "金額", "支払った人", "ステータス"]

# データを読み込む関数（古いデータにも自動で足りない列を補足します）
def load_data(file_name, columns):
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        for col in columns:
            if col not in df.columns:
                if col == "ステータス":
                    df[col] = "有効"
                elif col == "ID":
                    df[col] = [str(uuid.uuid4()) for _ in range(len(df))]
                else:
                    df[col] = ""
        # 指定した列の順番に並び替えて返す
        return df[columns]
    else:
        return pd.DataFrame(columns=columns)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --------------------------------------------------
# ダイアログ（ポップアップ）の設定
# --------------------------------------------------
@st.dialog("⚠️ スケジュール削除（取り消し）の確認")
def confirm_delete_schedule(target_id, df):
    st.write("この予定を「削除済み」にしますか？\n※データ自体は取り消し線付きで残ります。")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します"):
        df.loc[df["ID"] == target_id, "ステータス"] = "削除済み"
        save_data(df, SCHEDULE_FILE)
        st.success("削除済みに変更しました！画面を更新します...")
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("⚠️ 経費削除（取り消し）の確認")
def confirm_delete_expense(target_id, df):
    st.write("この経費を「削除済み」にしますか？\n※データ自体は取り消し線付きで残ります。")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します"):
        df.loc[df["ID"] == target_id, "ステータス"] = "削除済み"
        save_data(df, EXPENSE_FILE)
        st.success("削除済みに変更しました！画面を更新します...")
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

# --------------------------------------------------
# 共通機能：削除済みの行をグレーアウトする装飾
# --------------------------------------------------
def highlight_deleted(row):
    if row.get("ステータス") == "削除済み":
        return ["color: #aaaaaa; text-decoration: line-through; background-color: #f9f9f9"] * len(row)
    return [""] * len(row)

# --------------------------------------------------
# メニュー設定
# --------------------------------------------------
menu = st.sidebar.radio(
    "📂 メニュー",
    ["月間カレンダー", "日別カレンダー", "スケジュール一覧", "スケジュール登録", "月別経費", "経費一覧", "経費登録"]
)

st.title("阪竹行政書士事務所 共有アプリ")

# 今日の日付を取得（カレンダーなどの初期値用）
today = datetime.date.today()

# ==========================================
# 🗓️ パターンA：月間カレンダー
# ==========================================
if menu == "月間カレンダー":
    st.header("🗓️ 月間カレンダー")
    
    col_y, col_m = st.columns(2)
    with col_y:
        selected_year = st.selectbox("年", [today.year - 1, today.year, today.year + 1], index=1, key="cal_a_y")
    with col_m:
        selected_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1, key="cal_a_m")

    df_schedule = load_data(SCHEDULE_FILE, SCH_COLS)
    active_sch = df_schedule[df_schedule["ステータス"] != "削除済み"]

    # カレンダーのHTML（マークダウン）を生成
    cal_matrix = calendar.monthcalendar(selected_year, selected_month)
    md_cal = "| 月 | 火 | 水 | 木 | 金 | 土 | 日 |\n|---|---|---|---|---|---|---|\n"
    
    for week in cal_matrix:
        row = "|"
        for day in week:
            if day == 0:
                row += " |" # 空白の日
            else:
                date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
                day_events = active_sch[active_sch["日付"] == date_str]
                
                # セル内のテキストを作成
                cell_text = f"**{day}**<br>"
                for _, event in day_events.iterrows():
                    cell_text += f"<span style='font-size: 0.8em;'>・{event['時間']}: {event['予定の内容']}</span><br>"
                row += f" {cell_text} |"
        md_cal += row + "\n"
        
    st.markdown(md_cal, unsafe_allow_html=True)

# ==========================================
# 📋 パターンB：日別カレンダー
# ==========================================
elif menu == "日別カレンダー":
    st.header("📋 日別カレンダー")
    
    col_y, col_m = st.columns(2)
    with col_y:
        selected_year = st.selectbox("年", [today.year - 1, today.year, today.year + 1], index=1, key="cal_b_y")
    with col_m:
        selected_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1, key="cal_b_m")

    df_schedule = load_data(SCHEDULE_FILE, SCH_COLS)
    active_sch = df_schedule[df_schedule["ステータス"] != "削除済み"]
    
    # その月の日数を取得
    _, num_days = calendar.monthrange(selected_year, selected_month)
    
    for day in range(1, num_days + 1):
        date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
        day_events = active_sch[active_sch["日付"] == date_str]
        
        # Streamlitのコンテナで枠を作る
        with st.container(border=True):
            st.markdown(f"#### {day}日")
            if day_events.empty:
                st.write(" ") # 予定なし
            else:
                for _, event in day_events.iterrows():
                    st.write(f"⏰ {event['時間']} | {event['予定の内容']} ({event['顧客名']}) - 担当:{event['担当者']}")

# ==========================================
# 📜 スケジュール一覧
# ==========================================
elif menu == "スケジュール一覧":
    st.header("📜 スケジュール一覧")
    df_schedule = load_data(SCHEDULE_FILE, SCH_COLS)
    
    if df_schedule.empty:
        st.info("データがありません。")
    else:
        # 表示用に並び替え、IDを隠す
        display_df = df_schedule.sort_values(by=["日付"]).drop(columns=["ID"])
        st.dataframe(display_df.style.apply(highlight_deleted, axis=1), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗑️ 予定の削除")
        active_sch = df_schedule[df_schedule["ステータス"] != "削除済み"]
        if not active_sch.empty:
            def format_sch(sch_id):
                row = active_sch[active_sch["ID"] == sch_id].iloc[0]
                return f"{row['日付']} {row['時間']} | {row['予定の内容']}"
            
            selected_sch_id = st.selectbox("削除する予定を選択", options=active_sch["ID"].tolist(), format_func=format_sch)
            if st.button("選択した予定を削除"):
                confirm_delete_schedule(selected_sch_id, df_schedule)

# ==========================================
# 📝 スケジュール登録
# ==========================================
elif menu == "スケジュール登録":
    st.header("📝 スケジュール登録")
    df_schedule = load_data(SCHEDULE_FILE, SCH_COLS)
    
    with st.form("schedule_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付")
        with col2:
            # 時間をテキスト入力に変更
            time_str = st.text_input("時間 (例: 10時、終日、未定)")
            
        task = st.text_input("予定の内容 (例: 相続の初回面談など)")
        customer = st.text_input("お客様 / 顧客名 (例: 〇〇様、〇〇株式会社など)")
        assignee = st.selectbox("担当者", ["全員", "阪口", "竹之内"])
        submit = st.form_submit_button("予定を追加")
        
    if submit:
        new_data = pd.DataFrame([{
            "ID": str(uuid.uuid4()), 
            "日付": date, 
            "時間": time_str, 
            "予定の内容": task, 
            "顧客名": customer, 
            "担当者": assignee,
            "ステータス": "有効"
        }])
        df_schedule = pd.concat([df_schedule, new_data], ignore_index=True)
        save_data(df_schedule, SCHEDULE_FILE)
        st.success("✅ 予定を保存しました！")

# ==========================================
# 📊 月別経費
# ==========================================
elif menu == "月別経費":
    st.header("📊 月別経費")
    
    col_y, col_m = st.columns(2)
    with col_y:
        selected_year = st.selectbox("年", [today.year - 1, today.year, today.year + 1], index=1, key="exp_y")
    with col_m:
        selected_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1, key="exp_m")

    df_expense = load_data(EXPENSE_FILE, EXP_COLS)
    active_exp = df_expense[df_expense["ステータス"] != "削除済み"]
    
    if active_exp.empty:
        st.info("データがありません。")
    else:
        # 選択した年・月に絞り込み
        target_month_str = f"{selected_year}-{selected_month:02d}"
        monthly_exp = active_exp[active_exp["日付"].str.startswith(target_month_str)]
        
        if monthly_exp.empty:
            st.write(f"{selected_year}年{selected_month}月の経費登録はありません。")
        else:
            total_amount = monthly_exp["金額"].sum()
            st.metric(label=f"💰 {selected_month}月の経費合計", value=f"{total_amount:,} 円")
            
            st.markdown("##### 登録内容")
            display_monthly = monthly_exp.sort_values(by=["日付"]).drop(columns=["ID", "ステータス"])
            st.dataframe(display_monthly, hide_index=True, use_container_width=True)

# ==========================================
# 🧾 経費一覧
# ==========================================
elif menu == "経費一覧":
    st.header("🧾 経費一覧")
    df_expense = load_data(EXPENSE_FILE, EXP_COLS)
    
    if df_expense.empty:
        st.info("データがありません。")
    else:
        display_df_exp = df_expense.sort_values(by=["日付"], ascending=False).drop(columns=["ID"])
        st.dataframe(display_df_exp.style.apply(highlight_deleted, axis=1), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗑️ 経費の削除")
        active_expenses = df_expense[df_expense["ステータス"] != "削除済み"]
        if not active_expenses.empty:
            def format_exp(exp_id):
                row = active_expenses[active_expenses["ID"] == exp_id].iloc[0]
                return f"{row['日付']} | {row['項目']} : {row['金額']}円"
            
            selected_exp_id = st.selectbox("削除する経費を選択", options=active_expenses["ID"].tolist(), format_func=format_exp)
            if st.button("選択した経費を削除"):
                confirm_delete_expense(selected_exp_id, df_expense)

# ==========================================
# 💰 経費登録
# ==========================================
elif menu == "経費登録":
    st.header("💰 経費登録")
    df_expense = load_data(EXPENSE_FILE, EXP_COLS)
    
    with st.form("expense_form", clear_on_submit=True):
        e_date = st.date_input("支払日")
        item = st.text_input("項目 (例: コピー用紙など)")
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
            "ステータス": "有効"
        }])
        df_expense = pd.concat([df_expense, new_data], ignore_index=True)
        save_data(df_expense, EXPENSE_FILE)
        st.success("✅ 経費を保存しました！")