import streamlit as st
import pandas as pd
import datetime
import uuid
import calendar
from supabase import create_client, Client

# ==========================================
# 1. ページ設定とフォント統一 (Noto Sans JP)
# ==========================================
st.set_page_config(page_title="阪竹事務所", layout="centered")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
    }
    .deleted-text {
        color: #999999;
        text-decoration: line-through;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Supabaseの接続設定
# ==========================================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ==========================================
# 3. 🔐 ログイン（認証）管理システム
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = "阪口" # 初期表示名
if "last_login" not in st.session_state:
    st.session_state["last_login"] = None

# 7日間の経過チェック
if st.session_state["logged_in"] and st.session_state["last_login"]:
    days_since_login = (datetime.datetime.now() - st.session_state["last_login"]).days
    if days_since_login >= 7:
        st.session_state["logged_in"] = False
        st.warning("セッションの有効期限（7日間）が切れました。再度ログインしてください。")

# ログイン画面の表示（未ログイン時）
if not st.session_state["logged_in"]:
    st.title("🔐 阪竹事務所 システムログイン")
    st.write("Supabaseで登録したメールアドレスとパスワードを入力してください。")
    with st.form("login_form"):
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        if st.form_submit_button("ログイン", type="primary"):
            try:
                # Supabaseで認証チェック
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["logged_in"] = True
                    st.session_state["last_login"] = datetime.datetime.now()
                    st.rerun()
            except Exception:
                st.error("ログインに失敗しました。メールアドレスとパスワードを確認してください。")
    st.stop() # ログインが完了するまで、この下にあるメイン画面のコードは実行しない

current_user = st.session_state["current_user"]

# ==========================================
# 4. データベース取得関数
# ==========================================
def fetch_table(table_name, order_col="ID", ascending=False):
    response = supabase.table(table_name).select("*").order(order_col, desc=not ascending).execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

# ==========================================
# 5. ポップアップ（ダイアログ）設定
# ==========================================
@st.dialog("⚠️ 削除の確認")
def confirm_delete(table_name, target_id):
    st.write("このデータを「削除済み」にしますか？\n（一覧には履歴として残ります）")
    col1, col2 = st.columns(2)
    if col1.button("はい、削除します", type="primary"):
        supabase.table(table_name).update({"ステータス": "削除済み"}).eq("ID", target_id).execute()
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("✅ 復元の確認")
def confirm_restore(table_name, target_id):
    st.write("このデータを有効な状態に戻しますか？")
    col1, col2 = st.columns(2)
    if col1.button("元に戻す", type="primary"):
        supabase.table(table_name).update({"ステータス": "有効"}).eq("ID", target_id).execute()
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("⚠️ 移動記録の削除")
def confirm_delete_travel(target_id, date_str):
    st.write("削除しますか？\n(その日の連番は自動で詰め直されます)")
    col1, col2 = st.columns(2)
    if col1.button("削除する", type="primary"):
        supabase.table("travel_logs").update({"ステータス": "削除済み"}).eq("ID", target_id).execute()
        res = supabase.table("travel_logs").select("*").eq("日付", date_str).neq("ステータス", "削除済み").order("連番").execute()
        for i, row in enumerate(res.data):
            if row["連番"] != i + 1:
                supabase.table("travel_logs").update({"連番": i + 1}).eq("ID", row["ID"]).execute()
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("✅ 移動記録の復元")
def confirm_restore_travel(target_id, date_str):
    st.write("有効な状態に戻しますか？\n(その日の最後の連番として復活します)")
    col1, col2 = st.columns(2)
    if col1.button("元に戻す", type="primary"):
        res = supabase.table("travel_logs").select("連番").eq("日付", date_str).neq("ステータス", "削除済み").execute()
        max_seq = max([r["連番"] for r in res.data]) if res.data else 0
        supabase.table("travel_logs").update({"ステータス": "有効", "連番": max_seq + 1}).eq("ID", target_id).execute()
        st.rerun()
    if col2.button("キャンセル"):
        st.rerun()

@st.dialog("📝 事件簿の編集")
def edit_case_record(row):
    with st.form(f"edit_form_{row['ID']}"):
        st.write(f"**案件: {row['受託番号']} ({row['事件の名称']})**")
        status_list = ['相談中', '受任（着手）', '進行中', '完了', 'キャンセル']
        status = st.selectbox("進捗状況", status_list, index=status_list.index(row['進捗状況']) if row['進捗状況'] in status_list else 0)
        
        parsed_comp = pd.to_datetime(row['完了日']).date() if pd.notna(row['完了日']) and row['完了日'] else None
        comp_date = st.date_input("完了日 (空欄可)", value=parsed_comp)
        
        fee = st.number_input("報酬額", value=int(row['報酬額'] if pd.notna(row['報酬額']) else 0), step=1000)
        job_req = st.text_input("職務上請求書 使用番号", value=row.get('職務上請求書番号', ''))
        receipt = st.text_input("領収証番号", value=row.get('領収証番号', ''))
        summary = st.text_area("業務の概要・結果", value=row.get('業務概要', ''))
        memo = st.text_area("備考", value=row.get('備考', ''))
        
        if st.form_submit_button("更新する"):
            supabase.table("case_records").update({
                "進捗状況": status, "完了日": str(comp_date) if comp_date else None,
                "報酬額": fee, "職務上請求書番号": job_req, "領収証番号": receipt,
                "業務概要": summary, "備考": memo
            }).eq("ID", row['ID']).execute()
            st.success("更新しました！")
            st.rerun()

# ==========================================
# 6. メニューとサイドバー（ログイン後）
# ==========================================
today = datetime.date.today()
df_members = fetch_table("members", "名前", True)
member_names = df_members["名前"].tolist() if not df_members.empty else ["阪口", "竹之内"]

df_msg = fetch_table("messages", "日時")
unread_count = 0
if not df_msg.empty:
    for _, row in df_msg.iterrows():
        if (row["宛先"] == "全員" or row["宛先"] == current_user) and current_user not in str(row.get("既読者", "")):
            unread_count += 1
msg_label = f"💬 メッセージ 🔴{unread_count}" if unread_count > 0 else "💬 メッセージ"

menu = st.sidebar.radio("📂 メニュー", [
    msg_label, '✏️ メッセージ入力', '🗓️ 月間カレンダー', '📋 日別一覧', '📜 スケジュール一覧', '📝 スケジュール登録', 
    '📊 月別経費', '🧾 経費一覧', '💰 経費登録', '🚗 移動記録入力', '🚗 移動記録一覧', '📁 事件簿入力', '📁 事件簿一覧', '⚙️ 管理・設定'
])
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **表示名: {current_user}**")
st.title("阪竹事務所 Webシステム")
# ==========================================
# 管理・設定・メッセージ機能
# ==========================================
if menu == "⚙️ 管理・設定":
    st.header("⚙️ 管理・設定")
    
    st.subheader("🚪 システムからログアウト")
    st.write("この端末から完全にログアウトし、次回アクセス時にパスワードを要求するようにします。")
    if st.button("ログアウトする", type="primary"):
        supabase.auth.sign_out()
        st.session_state["logged_in"] = False
        st.session_state["last_login"] = None
        st.rerun()
        
    st.markdown("---")
    st.subheader("👤 表示名切り替え (メッセージ等用)")
    selected_user = st.selectbox("自分の表示名を選択", member_names, index=member_names.index(current_user) if current_user in member_names else 0)
    if st.button("表示名を切り替える"):
        st.session_state["current_user"] = selected_user
        st.rerun()
        
    st.markdown("---")
    if current_user == "阪口":
        st.subheader("👥 メンバー管理 (管理者権限)")
        with st.form("add_member"):
            new_name = st.text_input("新規メンバー名")
            if st.form_submit_button("追加") and new_name:
                supabase.table("members").insert({"ID": str(uuid.uuid4()), "名前": new_name}).execute()
                st.rerun()
        
        for _, row in df_members.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"・ {row['名前']}")
            if row['名前'] in ["阪口", "竹之内"]: col2.write("削除不可")
            else:
                if col2.button("削除", key=f"del_mem_{row['ID']}"):
                    supabase.table("members").delete().eq("ID", row['ID']).execute()
                    st.rerun()
    else:
        st.info("※メンバー管理は表示名「阪口」での利用時のみ可能です。")

elif menu.startswith("💬 メッセージ"):
    st.header("💬 メッセージ一覧")
    if df_msg.empty: st.write("メッセージはありません")
    else:
        for _, row in df_msg.iterrows():
            is_for_me = (row["宛先"] == "全員" or row["宛先"] == current_user)
            read_by = str(row.get("既読者", ""))
            is_unread = is_for_me and (current_user not in read_by)
            
            with st.container(border=True):
                st.markdown(f"**{'🔴' if is_unread else '✅'} 宛先: {row['宛先']}** （送信: {row['送信者']} / {row['日時']}）")
                st.write(row["本文"])
                if is_unread and st.button("確認済みにする", key=f"msg_{row['ID']}"):
                    new_read = current_user if not read_by else f"{read_by},{current_user}"
                    supabase.table("messages").update({"既読者": new_read}).eq("ID", row["ID"]).execute()
                    st.rerun()

elif menu == '✏️ メッセージ入力':
    st.header("✏️ メッセージ入力")
    with st.form("msg_input", clear_on_submit=True):
        st.write(f"投稿者: {current_user}")
        receiver = st.selectbox("宛先", ["全員"] + member_names)
        content = st.text_area("本文")
        if st.form_submit_button("送信"):
            if content:
                now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
                supabase.table("messages").insert({"ID": str(uuid.uuid4()), "日時": now_str, "送信者": current_user, "宛先": receiver, "本文": content, "ステータス": "未確認", "既読者": ""}).execute()
                st.success("送信しました！")

# ==========================================
# スケジュール・経費機能
# ==========================================
elif menu == '🗓️ 月間カレンダー':
    st.header("🗓️ 月間カレンダー")
    df_sch = fetch_table("schedule", "日付", True)
    active_sch = df_sch[df_sch["ステータス"] != "削除済み"] if not df_sch.empty else pd.DataFrame()
    
    col_y, col_m = st.columns(2)
    s_year = col_y.selectbox("年", [today.year-1, today.year, today.year+1], index=1)
    s_month = col_m.selectbox("月", list(range(1,13)), index=today.month-1)
    
    cal_matrix = calendar.monthcalendar(s_year, s_month)
    md_cal = "| 月 | 火 | 水 | 木 | 金 | 土 | 日 |\n|---|---|---|---|---|---|---|\n"
    for week in cal_matrix:
        row_str = "|"
        for day in week:
            if day == 0: row_str += " |"
            else:
                date_str = f"{s_year}-{s_month:02d}-{day:02d}"
                events = active_sch[active_sch["日付"] == date_str] if not active_sch.empty else []
                cell_text = f"**{day}**<br>"
                for _, event in events.iterrows() if not active_sch.empty else []:
                    cell_text += f"<span style='font-size:0.8em; color:blue;'>🔴{event['時間']}</span><br>"
                row_str += f" {cell_text} |"
        md_cal += row_str + "\n"
    st.markdown(md_cal, unsafe_allow_html=True)

elif menu == '📋 日別一覧':
    st.header("📋 日別一覧")
    col_y, col_m = st.columns(2)
    s_year = col_y.selectbox("年", [today.year-1, today.year, today.year+1], index=1)
    s_month = col_m.selectbox("月", list(range(1,13)), index=today.month-1)
    
    df_sch = fetch_table("schedule", "日付", True)
    active_sch = df_sch[df_sch["ステータス"] != "削除済み"] if not df_sch.empty else pd.DataFrame()
    _, num_days = calendar.monthrange(s_year, s_month)
    
    for day in range(1, num_days + 1):
        date_str = f"{s_year}-{s_month:02d}-{day:02d}"
        events = active_sch[active_sch["日付"] == date_str] if not active_sch.empty else []
        with st.container(border=True):
            st.markdown(f"#### {day}日")
            if len(events) == 0: st.write("予定なし")
            else:
                for _, event in events.iterrows(): st.write(f"⏰ {event['時間']} | {event['予定の内容']} ({event['顧客名']}) - {event['担当者']}")

elif menu == '📜 スケジュール一覧' or menu == '🧾 経費一覧':
    table_name = "schedule" if menu == '📜 スケジュール一覧' else "expenses"
    st.header(menu)
    
    col1, col2, col3 = st.columns(3)
    filter_mode = col1.selectbox("表示範囲", ["全期間", "年", "月"])
    s_year = col2.selectbox("年指定", [today.year-1, today.year, today.year+1], index=1) if filter_mode in ["年", "月"] else None
    s_month = col3.selectbox("月指定", list(range(1,13)), index=today.month-1) if filter_mode == "月" else None
    
    df = fetch_table(table_name, "日付", False)
    if not df.empty:
        if filter_mode == "年": df = df[df["日付"].str.startswith(str(s_year))]
        elif filter_mode == "月": df = df[df["日付"].str.startswith(f"{s_year}-{s_month:02d}")]
    
    if df.empty: st.write("データがありません")
    else:
        for _, row in df.iterrows():
            is_deleted = row["ステータス"] == "削除済み"
            css_class = "deleted-text" if is_deleted else ""
            with st.container(border=True):
                col_text, col_btn = st.columns([4, 1])
                if table_name == "schedule":
                    col_text.markdown(f"<div class='{css_class}'><b>{row['日付']} {row['時間']} | {row['予定の内容']}</b><br>{row['顧客名']} (担当: {row['担当者']})</div>", unsafe_allow_html=True)
                else:
                    col_text.markdown(f"<div class='{css_class}'><b>{row['日付']} | {row['項目']}</b><br>支払: {row['支払った人']} | {row['金額']:,}円</div>", unsafe_allow_html=True)
                
                if is_deleted:
                    if col_btn.button("復元", key=f"res_{table_name}_{row['ID']}"): confirm_restore(table_name, row['ID'])
                else:
                    if col_btn.button("削除", key=f"del_{table_name}_{row['ID']}"): confirm_delete(table_name, row['ID'])

elif menu == '📝 スケジュール登録':
    st.header("📝 スケジュール登録")
    with st.form("sch_reg", clear_on_submit=True):
        date = st.date_input("日付")
        time_str = st.text_input("時間 (例: 10時、未定)")
        task = st.text_input("予定の内容")
        cust = st.text_input("顧客名")
        assignee = st.selectbox("担当者", ["全員"] + member_names)
        if st.form_submit_button("登録") and task:
            supabase.table("schedule").insert({"ID": str(uuid.uuid4()), "日付": str(date), "時間": time_str, "予定の内容": task, "顧客名": cust, "担当者": assignee, "ステータス": "有効"}).execute()
            st.success("予定を登録しました")

elif menu == '📊 月別経費':
    st.header("📊 月別経費")
    col_y, col_m = st.columns(2)
    s_year = col_y.selectbox("年", [today.year-1, today.year, today.year+1], index=1)
    s_month = col_m.selectbox("月", list(range(1,13)), index=today.month-1)
    
    df = fetch_table("expenses", "日付", True)
    df = df[(df["ステータス"] != "削除済み") & (df["日付"].str.startswith(f"{s_year}-{s_month:02d}"))] if not df.empty else pd.DataFrame()
    
    if df.empty: st.write("経費登録はありません")
    else:
        st.info(f"💰 合計: {df['金額'].sum():,} 円")
        for _, row in df.iterrows(): st.write(f"・ {row['日付']} | {row['項目']} : {row['金額']:,}円")

elif menu == '💰 経費登録':
    st.header("💰 経費登録")
    with st.form("exp_reg", clear_on_submit=True):
        date = st.date_input("支払日")
        item = st.text_input("項目")
        amount = st.number_input("金額 (円)", min_value=0, step=100)
        payer = st.selectbox("支払った人", member_names)
        if st.form_submit_button("登録") and item:
            supabase.table("expenses").insert({"ID": str(uuid.uuid4()), "日付": str(date), "項目": item, "金額": int(amount), "支払った人": payer, "ステータス": "有効"}).execute()
            st.success("経費を登録しました")
            # ==========================================
# 🚗 移動記録機能（連番自動調整付き）
# ==========================================
elif menu == '🚗 移動記録入力':
    st.header("🚗 移動記録入力")
    with st.form("travel_reg", clear_on_submit=True):
        date = st.date_input("日付")
        seq_input = st.number_input("連番 (未記入なら自動で最後の番号になります)", min_value=1, value=None, step=1, help="間に割り込ませる場合のみ入力してください")
        dep = st.text_input("出発地 (例: 事務所)")
        st.markdown("<div style='text-align: center; color: gray;'>⬇️</div>", unsafe_allow_html=True)
        arr = st.text_input("到着地 (例: 東区役所)")
        note = st.text_input("備考")
        
        if st.form_submit_button("記録を追加", type="primary"):
            if dep and arr:
                date_str = str(date)
                # その日の有効な記録を取得して連番を計算
                res = supabase.table("travel_logs").select("*").eq("日付", date_str).neq("ステータス", "削除済み").execute()
                logs = res.data if res.data else []
                max_seq = max([log["連番"] for log in logs]) if logs else 0
                
                new_seq = int(seq_input) if seq_input else max_seq + 1
                
                # 間に割り込ませる場合、既存の番号を後ろにズラす
                if seq_input and int(seq_input) <= max_seq:
                    for log in logs:
                        if log["連番"] >= new_seq:
                            supabase.table("travel_logs").update({"連番": log["連番"] + 1}).eq("ID", log["ID"]).execute()
                
                # 新規登録
                supabase.table("travel_logs").insert({
                    "ID": str(uuid.uuid4()), "日付": date_str, "連番": new_seq,
                    "出発地": dep, "到着地": arr, "備考": note, "ステータス": "有効"
                }).execute()
                st.success("移動記録を保存しました！")
            else:
                st.error("出発地と到着地は必須です。")

elif menu == '🚗 移動記録一覧':
    st.header("🚗 移動記録一覧")
    col_y, col_m = st.columns(2)
    s_year = col_y.selectbox("年", [today.year-1, today.year, today.year+1], index=1)
    s_month = col_m.selectbox("月", list(range(1,13)), index=today.month-1)
    
    df_travel = fetch_table("travel_logs", "日付", True)
    if not df_travel.empty:
        df_travel = df_travel[df_travel["日付"].str.startswith(f"{s_year}-{s_month:02d}")]
        # 日付と連番で綺麗に並び替え
        df_travel = df_travel.sort_values(by=["日付", "連番"], ascending=[True, True])
        
    if df_travel.empty:
        st.write("記録がありません")
    else:
        for _, row in df_travel.iterrows():
            is_deleted = row["ステータス"] == "削除済み"
            css_class = "deleted-text" if is_deleted else ""
            with st.container(border=True):
                col_text, col_btn = st.columns([5, 1])
                col_text.markdown(f"""
                <div class='{css_class}'>
                    <b>{row['日付']} (連番: {row['連番']})</b><br>
                    {row['出発地']} ➡️ {row['到着地']}<br>
                    備考: {row['備考']}
                </div>
                """, unsafe_allow_html=True)
                
                if is_deleted:
                    if col_btn.button("復元", key=f"res_tv_{row['ID']}"): confirm_restore_travel(row['ID'], row['日付'])
                else:
                    if col_btn.button("削除", key=f"del_tv_{row['ID']}"): confirm_delete_travel(row['ID'], row['日付'])

# ==========================================
# 📁 事件簿機能（法定帳簿対応）
# ==========================================
elif menu == '📁 事件簿入力':
    st.header("📁 事件簿入力")
    with st.form("case_reg", clear_on_submit=True):
        st.subheader("📋 基本情報")
        case_no = st.text_input("受託番号 (例: 2026-001)")
        c_name = st.text_input("依頼者 氏名")
        c_addr = st.text_input("依頼者 住所")
        title = st.text_input("事件の名称")
        
        c1, c2 = st.columns(2)
        cat = c1.selectbox("業務分類", ['相続', '遺言', '任意後見', '家族信託', 'その他'])
        status = c2.selectbox("進捗状況", ['相談中', '受任（着手）', '進行中', '完了', 'キャンセル'], index=1)
        
        acc_date = st.date_input("受託年月日")
        fee = st.number_input("報酬額（円・税込）", min_value=0, step=1000)
        ident = st.selectbox("本人確認", ['未完了', '運転免許証で確認済', 'マイナンバーカードで確認済', 'その他（面談等）'])
        
        st.subheader("📋 大阪府要件・その他")
        job_req = st.text_input("職務上請求書 使用番号")
        receipt = st.text_input("領収証番号")
        summary = st.text_area("業務の概要・結果")
        memo = st.text_area("社内用メモ（他士業連携など）")
        
        if st.form_submit_button("事件簿に登録する", type="primary"):
            if not case_no or not c_name or not title:
                st.error("受託番号、依頼者氏名、事件の名称は必須です")
            else:
                supabase.table("case_records").insert({
                    "ID": str(uuid.uuid4()), "受託番号": case_no, "依頼者名": c_name, "依頼者住所": c_addr,
                    "事件の名称": title, "業務分類": cat, "進捗状況": status, "受託日": str(acc_date),
                    "完了日": None, "報酬額": int(fee), "業務概要": summary,
                    "職務上請求書番号": job_req, "領収証番号": receipt, "本人確認": ident, "備考": memo, "ステータス": "有効"
                }).execute()
                st.success("事件簿に登録しました！")

elif menu == '📁 事件簿一覧':
    st.header("📁 事件簿一覧")
    st.caption("※PCからの出力(Excel/CSV)は、Supabase管理画面のTable Editorから「Export to CSV」で行ってください。")
    
    df_case = fetch_table("case_records", "受託日", False)
    if df_case.empty:
        st.write("事件簿の登録がありません")
    else:
        for _, row in df_case.iterrows():
            is_deleted = row["ステータス"] == "削除済み"
            css_class = "deleted-text" if is_deleted else ""
            title_prefix = "🗑️(削除済) " if is_deleted else ""
            
            # アコーディオン（開閉式）で表示
            with st.expander(f"{title_prefix}{row['受託番号']} : {row['事件の名称']} ({row['依頼者名']} 様) - {row['進捗状況']}"):
                st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)
                st.write(f"📍 **住所:** {row['依頼者住所']}")
                st.write(f"📋 **分類:** {row['業務分類']} | **本人確認:** {row['本人確認']}")
                st.write(f"💰 **報酬額:** {row['報酬額']:,} 円")
                if pd.notna(row['完了日']) and row['完了日']:
                    st.markdown(f"**🏁 完了日: <span style='color:green;'>{row['完了日']}</span>**", unsafe_allow_html=True)
                st.divider()
                st.write(f"📝 **概要・結果:** {row['業務概要']}")
                st.write(f"🧾 **職務上請求書:** {row['職務上請求書番号']} | **領収証:** {row['領収証番号']}")
                st.write(f"⚠️ **備考:** {row['備考']}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                # ボタンエリア
                if is_deleted:
                    col1, col2 = st.columns([5, 1])
                    if col2.button("復元", key=f"res_cr_{row['ID']}"): confirm_restore("case_records", row['ID'])
                else:
                    col_empty, col_edit, col_del = st.columns([4, 1, 1])
                    if col_edit.button("編集", key=f"edit_cr_{row['ID']}"): edit_case_record(row)
                    if col_del.button("削除", key=f"del_cr_{row['ID']}"): confirm_delete("case_records", row['ID'])