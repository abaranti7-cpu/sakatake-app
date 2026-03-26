import streamlit as st
import pandas as pd
import datetime
import uuid
import calendar
from supabase import create_client, Client

# ==========================================
# 1. Supabaseの接続設定と初期化
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

SCH_COLS = ["ID", "日付", "時間", "予定の内容", "顧客名", "担当者", "ステータス"]
EXP_COLS = ["ID", "日付", "項目", "金額", "支払った人", "ステータス"]
MSG_COLS = ["ID", "日時", "送信者", "宛先", "本文", "ステータス", "既読者"]
MEM_COLS = ["ID", "名前"]

# --- セッション状態（ログインユーザー）の初期化 ---
if "current_user" not in st.session_state:
    st.session_state["current_user"] = "阪口" # 初期値

current_user = st.session_state["current_user"]

# ==========================================
# 2. データベース操作用の関数
# ==========================================
def load_schedule():
    response = supabase.table("schedule").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=SCH_COLS)

def load_expenses():
    response = supabase.table("expenses").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=EXP_COLS)

def load_messages():
    response = supabase.table("messages").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=MSG_COLS)

def load_members():
    response = supabase.table("members").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=MEM_COLS)

def insert_schedule(data_dict):
    supabase.table("schedule").insert(data_dict).execute()

def insert_expense(data_dict):
    supabase.table("expenses").insert(data_dict).execute()

def insert_message(data_dict):
    supabase.table("messages").insert(data_dict).execute()

def delete_schedule(sch_id):
    supabase.table("schedule").update({"ステータス": "削除済み"}).eq("ID", sch_id).execute()

def delete_expense(exp_id):
    supabase.table("expenses").update({"ステータス": "削除済み"}).eq("ID", exp_id).execute()

# --- 新規追加：メンバー管理と個別既読の関数 ---
def insert_member(name):
    supabase.table("members").insert({"ID": str(uuid.uuid4()), "名前": name}).execute()

def delete_member(member_id):
    supabase.table("members").delete().eq("ID", member_id).execute()

def mark_as_read(msg_id, current_read_by, user_name):
    # 既存の既読者がいればカンマ区切りで追加、いなければそのまま追加
    new_read_by = user_name if not current_read_by else f"{current_read_by},{user_name}"
    supabase.table("messages").update({"既読者": new_read_by}).eq("ID", msg_id).execute()

# --------------------------------------------------
# ダイアログ（ポップアップ）の設定
# --------------------------------------------------
@st.dialog("⚠️ スケジュール削除（取り消し）の確認")
def confirm_delete_schedule(target_id):
    st.write("この予定を「削除済み」にしますか？")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します"):
        delete_schedule(target_id)
        st.success("削除済みに変更しました！画面を更新します...")
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("⚠️ 経費削除（取り消し）の確認")
def confirm_delete_expense(target_id):
    st.write("この経費を「削除済み」にしますか？")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します"):
        delete_expense(target_id)
        st.success("削除済みに変更しました！画面を更新します...")
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

def highlight_deleted(row):
    if row.get("ステータス") == "削除済み":
        return ["color: #aaaaaa; text-decoration: line-through; background-color: #f9f9f9"] * len(row)
    return [""] * len(row)

# ==========================================
# UI・画面構成
# ==========================================
df_msg = load_messages()
df_members = load_members()
member_names = df_members["名前"].tolist() if not df_members.empty else ["阪口", "竹之内"]

# 未確認メッセージの数を「自分宛て かつ 未読」で計算
unread_count = 0
if not df_msg.empty:
    for _, row in df_msg.iterrows():
        is_for_me = (row["宛先"] == "全員" or row["宛先"] == current_user)
        read_by = str(row.get("既読者", ""))
        if is_for_me and current_user not in read_by:
            unread_count += 1

if unread_count > 0:
    msg_menu_label = f"💬 メッセージ 🔴未読{unread_count}件"
else:
    msg_menu_label = "💬 メッセージ"

menu = st.sidebar.radio(
    "📂 メニュー",
    [
        msg_menu_label, 
        "✏️ メッセージの入力", 
        "🗓️ 月間カレンダー", 
        "📋 日別カレンダー", 
        "📜 スケジュール一覧", 
        "📝 スケジュール登録", 
        "📊 月別経費", 
        "🧾 経費一覧", 
        "💰 経費登録",
        "⚙️ 管理・ログイン" # 追加
    ]
)

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **ログイン中: {current_user}**")

st.title(f"阪竹行政書士事務所 共有アプリ")
today = datetime.date.today()

# ==========================================
# 💬 メッセージ
# ==========================================
if menu.startswith("💬 メッセージ"):
    st.header("💬 メッセージ")
    
    if df_msg.empty:
        st.info("現在、メッセージはありません。")
    else:
        df_msg_sorted = df_msg.sort_values(by="日時", ascending=False)
        
        for _, row in df_msg_sorted.iterrows():
            # 自分が宛先に含まれているか、自分が読んだか判定
            is_for_me = (row["宛先"] == "全員" or row["宛先"] == current_user)
            read_by = str(row.get("既読者", ""))
            is_unread = is_for_me and (current_user not in read_by)

            with st.container(border=True):
                if is_unread:
                    st.markdown(f"**🔴 宛先: {row['宛先']}** （送信者: {row['送信者']} / {row['日時']}）")
                    st.write(row["本文"])
                    if st.button("確認済みにする", key=f"btn_{row['ID']}"):
                        mark_as_read(row["ID"], read_by, current_user)
                        st.rerun()
                else:
                    st.markdown(f"<span style='color: gray;'>✅ 宛先: {row['宛先']} （送信者: {row['送信者']} / {row['日時']}）</span>", unsafe_allow_html=True)
                    st.write(row["本文"])

# ==========================================
# ✏️ メッセージの入力
# ==========================================
elif menu == "✏️ メッセージの入力":
    st.header("✏️ メッセージの入力")
    
    with st.form("message_form", clear_on_submit=True):
        st.write(f"**投稿者:** {current_user}")
        
        receiver_options = ["全員"] + member_names
        receiver = st.selectbox("宛先", receiver_options)
            
        content = st.text_area("メッセージ本文")
        submit_msg = st.form_submit_button("送信")
        
    if submit_msg:
        jst = datetime.timezone(datetime.timedelta(hours=9))
        now_str = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M")
        
        new_row = {
            "ID": str(uuid.uuid4()), 
            "日時": now_str, 
            "送信者": current_user, 
            "宛先": receiver, 
            "本文": content, 
            "ステータス": "未確認",
            "既読者": "" # 最初は誰も読んでいない状態
        }
        insert_message(new_row)
        st.success("✅ メッセージを送信しました！")

# ==========================================
# ⚙️ 管理・ログイン（新規追加）
# ==========================================
elif menu == "⚙️ 管理・ログイン":
    st.header("⚙️ 管理・ログイン")

    st.subheader("👤 ログインユーザー切り替え")
    current_index = member_names.index(current_user) if current_user in member_names else 0
    selected_user = st.selectbox("ユーザーを選択", member_names, index=current_index)
    
    if st.button("切り替える"):
        st.session_state["current_user"] = selected_user
        st.success(f"{selected_user} さんとしてログインしました！")
        st.rerun()

    st.markdown("---")

    # 阪口さんのみメンバー管理可能
    if current_user == "阪口":
        st.subheader("👥 メンバー管理 (管理者権限)")
        
        with st.form("add_member_form", clear_on_submit=True):
            new_name = st.text_input("新規メンバー名")
            if st.form_submit_button("追加"):
                if new_name:
                    insert_member(new_name)
                    st.success(f"「{new_name}」さんを追加しました！")
                    st.rerun()
                else:
                    st.error("名前を入力してください")

        st.write("**登録済みメンバー**")
        for _, row in df_members.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"・ {row['名前']}")
            
            if row['名前'] in ["阪口", "竹之内"]:
                col2.markdown("<span style='color:gray'>削除不可</span>", unsafe_allow_html=True)
            else:
                if col2.button("削除", key=f"del_mem_{row['ID']}"):
                    delete_member(row['ID'])
                    st.success("削除しました！")
                    st.rerun()
    else:
        st.info("※ メンバーの追加・削除は、管理者（阪口）でのログイン時のみ可能です。")

# ==========================================
# 🗓️ 月間カレンダー (変更なし)
# ==========================================
elif menu == "🗓️ 月間カレンダー":
    st.header("🗓️ 月間カレンダー")
    col_y, col_m = st.columns(2)
    with col_y:
        selected_year = st.selectbox("年", [today.year - 1, today.year, today.year + 1], index=1, key="cal_a_y")
    with col_m:
        selected_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1, key="cal_a_m")

    df_schedule = load_schedule()
    active_sch = df_schedule[df_schedule["ステータス"] != "削除済み"] if not df_schedule.empty else pd.DataFrame(columns=SCH_COLS)

    cal_matrix = calendar.monthcalendar(selected_year, selected_month)
    md_cal = "| 月 | 火 | 水 | 木 | 金 | 土 | 日 |\n|---|---|---|---|---|---|---|\n"
    
    for week in cal_matrix:
        row_str = "|"
        for day in week:
            if day == 0:
                row_str += " |"
            else:
                date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
                day_events = active_sch[active_sch["日付"] == date_str]
                cell_text = f"**{day}**<br>"
                for _, event in day_events.iterrows():
                    cell_text += f"<span style='font-size: 0.8em;'>・{event['時間']}: {event['予定の内容']}</span><br>"
                row_str += f" {cell_text} |"
        md_cal += row_str + "\n"
    st.markdown(md_cal, unsafe_allow_html=True)

# ==========================================
# 📋 日別カレンダー (変更なし)
# ==========================================
elif menu == "📋 日別カレンダー":
    st.header("📋 日別カレンダー")
    col_y, col_m = st.columns(2)
    with col_y:
        selected_year = st.selectbox("年", [today.year - 1, today.year, today.year + 1], index=1, key="cal_b_y")
    with col_m:
        selected_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1, key="cal_b_m")

    df_schedule = load_schedule()
    active_sch = df_schedule[df_schedule["ステータス"] != "削除済み"] if not df_schedule.empty else pd.DataFrame(columns=SCH_COLS)
    _, num_days = calendar.monthrange(selected_year, selected_month)
    
    for day in range(1, num_days + 1):
        date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
        day_events = active_sch[active_sch["日付"] == date_str]
        with st.container(border=True):
            st.markdown(f"#### {day}日")
            if day_events.empty:
                st.write(" ")
            else:
                for _, event in day_events.iterrows():
                    st.write(f"⏰ {event['時間']} | {event['予定の内容']} ({event['顧客名']}) - 担当:{event['担当者']}")

# ==========================================
# 📜 スケジュール一覧 (変更なし)
# ==========================================
elif menu == "📜 スケジュール一覧":
    st.header("📜 スケジュール一覧")
    df_schedule = load_schedule()
    if df_schedule.empty:
        st.info("データがありません。")
    else:
        display_df = df_schedule.sort_values(by=["日付"]).drop(columns=["ID"])
        st.dataframe(display_df.style.apply(highlight_deleted, axis=1), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🗑️ 予定の削除")
        active_sch = df_schedule[df_schedule["ステータス"] != "削除済み"]
        if not active_sch.empty:
            def format_sch(sch_id):
                row_data = active_sch[active_sch["ID"] == sch_id].iloc[0]
                return f"{row_data['日付']} {row_data['時間']} | {row_data['予定の内容']}"
            
            selected_sch_id = st.selectbox("削除する予定を選択", options=active_sch["ID"].tolist(), format_func=format_sch)
            if st.button("選択した予定を削除"):
                confirm_delete_schedule(selected_sch_id)

# ==========================================
# 📝 スケジュール登録 (担当者リストを連動)
# ==========================================
elif menu == "📝 スケジュール登録":
    st.header("📝 スケジュール登録")
    with st.form("schedule_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("日付")
        with col2:
            time_str = st.text_input("時間 (例: 10時、終日、未定)")
            
        task = st.text_input("予定の内容 (例: 相続の初回面談など)")
        customer = st.text_input("お客様 / 顧客名 (例: 〇〇様、〇〇株式会社など)")
        assignee = st.selectbox("担当者", ["全員"] + member_names)
        submit = st.form_submit_button("予定を追加")
        
    if submit:
        new_row = {
            "ID": str(uuid.uuid4()), 
            "日付": str(date), 
            "時間": time_str, 
            "予定の内容": task, 
            "顧客名": customer, 
            "担当者": assignee,
            "ステータス": "有効"
        }
        insert_schedule(new_row)
        st.success("✅ 予定を保存しました！")

# ==========================================
# 📊 月別経費 (変更なし)
# ==========================================
elif menu == "📊 月別経費":
    st.header("📊 月別経費")
    col_y, col_m = st.columns(2)
    with col_y:
        selected_year = st.selectbox("年", [today.year - 1, today.year, today.year + 1], index=1, key="exp_y")
    with col_m:
        selected_month = st.selectbox("月", list(range(1, 13)), index=today.month - 1, key="exp_m")

    df_expense = load_expenses()
    active_exp = df_expense[df_expense["ステータス"] != "削除済み"] if not df_expense.empty else pd.DataFrame(columns=EXP_COLS)
    
    if active_exp.empty:
        st.info("データがありません。")
    else:
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
# 🧾 経費一覧 (変更なし)
# ==========================================
elif menu == "🧾 経費一覧":
    st.header("🧾 経費一覧")
    df_expense = load_expenses()
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
                row_data = active_expenses[active_expenses["ID"] == exp_id].iloc[0]
                return f"{row_data['日付']} | {row_data['項目']} : {row_data['金額']}円"
            
            selected_exp_id = st.selectbox("削除する経費を選択", options=active_expenses["ID"].tolist(), format_func=format_exp)
            if st.button("選択した経費を削除"):
                confirm_delete_expense(selected_exp_id)

# ==========================================
# 💰 経費登録 (支払った人を連動)
# ==========================================
elif menu == "💰 経費登録":
    st.header("💰 経費登録")
    with st.form("expense_form", clear_on_submit=True):
        e_date = st.date_input("支払日")
        item = st.text_input("項目 (例: コピー用紙など)")
        amount = st.number_input("金額 (円)", min_value=0, step=100)
        payer = st.selectbox("支払った人", member_names)
        e_submit = st.form_submit_button("経費を登録")
        
    if e_submit:
        new_row = {
            "ID": str(uuid.uuid4()), 
            "日付": str(e_date), 
            "項目": item, 
            "金額": amount, 
            "支払った人": payer,
            "ステータス": "有効"
        }
        insert_expense(new_row)
        st.success("✅ 経費を保存しました！")