import streamlit as st
import pandas as pd
from datetime import date, datetime
import random
import time
import os
import io
import qrcode
import gspread
from google.oauth2.service_account import Credentials

# 1. Cấu hình giao diện Streamlit
st.set_page_config(page_title="THẦY HOÀNG HIỀN HẬU", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        .teacher-banner {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        .big-font { font-size: 22px !important; font-weight: bold; }
        .stButton>button { width: 100%; height: 45px; font-size: 16px !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. Kết nối Google Sheets linh hoạt
current_dir = os.path.dirname(os.path.abspath(__file__))
JSON_KEY_FILE = os.path.join(current_dir, "service_account.json")
SHEET_TITLE = "Database_So_Theo_Doi_Hoc_Tap"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_google_sheets_connection():
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(SHEET_TITLE)

try:
    sh = get_google_sheets_connection()
    ws_grades = sh.worksheet("grades")
    ws_logs = sh.worksheet("behavior_logs")
    ws_auth = sh.worksheet("auth_sessions")
except Exception as e:
    st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
    st.stop()

# ==================== PHẦN XỬ LÝ QUÉT QR TRÊN ĐIỆN THOẠI ====================
query_params = st.query_params
if "auth_token" in query_params:
    token = query_params["auth_token"]
    st.markdown('<div class="teacher-banner">📱 XÁC THỰC QUYỀN GIÁO VIÊN</div>', unsafe_allow_html=True)
    st.write("")
    st.info(f"Yêu cầu mở khóa phiên: **{token}**")
    
    auth_pass = st.text_input("Nhập mã bảo mật giáo viên:", type="password", key="mobile_auth_key")
    if st.button("✅ Phê duyệt đăng nhập cho máy tính lớp", type="primary"):
        if auth_pass == "Toan6Tin9":
            try:
                cell_matches = ws_auth.findall(token)
                if cell_matches:
                    for c in cell_matches:
                        ws_auth.update_cell(c.row, 3, "APPROVED")
                else:
                    ws_auth.append_row([token, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "APPROVED"])
                st.success("🎉 ĐÃ PHÊ DUYỆT THÀNH CÔNG!")
                st.balloons()
                st.info("Máy tính tại lớp học đã được mở quyền quản trị.")
            except Exception as err:
                st.error(f"Lỗi phê duyệt: {err}")
        else:
            st.error("Mã bảo mật không chính xác!")
    st.stop()

# ==================== GIAO DIỆN CHÍNH (MÁY TÍNH LỚP HỌC) ====================
st.markdown('<div class="teacher-banner">✨ LỚP HỌC THẦY HOÀNG HIỀN HẬU ✨</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_base_data():
    try:
        ws_config = sh.worksheet("CONFIG")
        df_c = pd.DataFrame(ws_config.get_all_records())
        df_g = pd.DataFrame(ws_grades.get_all_records())
        df_l = pd.DataFrame(ws_logs.get_all_records())
        
        for df in [df_c, df_g, df_l]:
            if not df.empty:
                df.columns = [str(c).lower().strip() for c in df.columns]
                if "ma_hs" in df.columns and "stt" not in df.columns:
                    df.rename(columns={"ma_hs": "stt"}, inplace=True)
        return df_c, df_g, df_l
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_config, df_grades, df_logs = load_base_data()

@st.cache_data(ttl=300)
def load_class_students(class_name):
    try:
        ws_class = sh.worksheet(str(class_name).strip())
        df = pd.DataFrame(ws_class.get_all_records())
        if not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            df["stt_display"] = df["stt"].astype(str).str.strip()
            df["lop"] = str(class_name).strip()
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# 3. Quản trị đăng nhập bằng mã QR
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "qr_session_id" not in st.session_state:
    st.session_state["qr_session_id"] = f"SES_{random.randint(1000, 9999)}_{int(time.time())}"

st.sidebar.title("⚙️ QUẢN TRỊ LỚP HỌC")
st.sidebar.markdown("---")

if not st.session_state["authenticated"]:
    st.sidebar.subheader("📲 Đăng nhập bằng mã QR")
    st.sidebar.caption("Dùng Zalo / Camera điện thoại quét mã bên dưới để mở khóa:")
    
    current_session = st.session_state["qr_session_id"]
    auth_url = f"https://lophocthayhoanghienhau.streamlit.app/?auth_token={current_session}"
    
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(auth_url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img_qr.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), caption="Mã QR xác thực phiên", use_container_width=True)
    
    col_c1, col_c2 = st.sidebar.columns(2)
    with col_c1:
        if st.button("⚡ Đã duyệt xong"):
            try:
                records = ws_auth.get_all_records()
                is_approved = any(
                    str(r.get("SESSION_ID", "")).strip() == current_session and str(r.get("STATUS", "")).strip().upper() == "APPROVED"
                    for r in records
                )
                if is_approved:
                    st.session_state["authenticated"] = True
                    st.sidebar.success("Xác thực thành công!")
                    st.rerun()
                else:
                    st.sidebar.warning("Chưa nhận được phê duyệt từ điện thoại.")
            except Exception as e:
                st.sidebar.error(f"Lỗi kiểm tra: {e}")
    with col_c2:
        if st.button("🔄 Đổi mã mới"):
            st.session_state["qr_session_id"] = f"SES_{random.randint(1000, 9999)}_{int(time.time())}"
            st.rerun()
else:
    st.sidebar.success("🔓 Chế độ: **Giáo viên quản trị**")
    if st.sidebar.button("Đăng xuất"):
        st.session_state["authenticated"] = False
        st.session_state["qr_session_id"] = f"SES_{random.randint(1000, 9999)}_{int(time.time())}"
        st.rerun()

st.sidebar.markdown("---")

# Bộ lọc Môn và Lớp
if not df_config.empty and "mon_hoc" in df_config.columns:
    available_mon = sorted(df_config["mon_hoc"].dropna().unique().tolist())
else:
    available_mon = ["Toán", "Tin"]

selected_mon = st.sidebar.selectbox("📖 Chọn Môn học:", available_mon)

if not df_config.empty and "mon_hoc" in df_config.columns and "lop" in df_config.columns:
    mon_cfg = df_config[df_config["mon_hoc"].astype(str).str.strip().str.lower() == selected_mon.strip().lower()]
    available_classes = sorted(mon_cfg["lop"].dropna().unique().tolist())
    if not mon_cfg.empty and "so_cot_tx" in mon_cfg.columns:
        num_tx = int(pd.to_numeric(mon_cfg["so_cot_tx"], errors="coerce").fillna(2).iloc[0])
    else:
        num_tx = 4 if "toán" in selected_mon.lower() else 2
else:
    available_classes = ["6A2", "6A3"] if selected_mon == "Toán" else ["9A1", "9A2", "9A5", "9A6", "9A7"]
    num_tx = 4 if "toán" in selected_mon.lower() else 2

tx_cols = [f"tx{i+1}" for i in range(num_tx)]
selected_lop = st.sidebar.selectbox("🏫 Chọn Lớp:", available_classes)

if st.sidebar.button("🔄 Tải lại dữ liệu"):
    st.cache_resource.clear()
    st.cache_data.clear()
    st.rerun()

current_students = load_class_students(selected_lop)

# Lọc điểm và nhật ký
mon_keyword = selected_mon.strip().lower()
if not df_grades.empty and "lop" in df_grades.columns and "mon_hoc" in df_grades.columns:
    current_grades = df_grades[
        (df_grades["lop"].astype(str).str.strip().str.upper() == str(selected_lop).strip().upper()) & 
        (df_grades["mon_hoc"].astype(str).str.lower().str.contains(mon_keyword))
    ].copy()
    if "stt" in current_grades.columns:
        current_grades["stt"] = current_grades["stt"].astype(str).str.strip()
else:
    current_grades = pd.DataFrame()

if not df_logs.empty and "lop" in df_logs.columns and "mon_hoc" in df_logs.columns:
    current_logs = df_logs[
        (df_logs["lop"].astype(str).str.strip().str.upper() == str(selected_lop).strip().upper()) & 
        (df_logs["mon_hoc"].astype(str).str.lower().str.contains(mon_keyword))
    ].copy()
    if "stt" in current_logs.columns:
        current_logs["stt"] = current_logs["stt"].astype(str).str.strip()
    if "delta" in current_logs.columns:
        current_logs["delta"] = current_logs["delta"].astype(str).str.replace(",", ".", regex=False)
        current_logs["delta"] = pd.to_numeric(current_logs["delta"], errors="coerce").fillna(0.0)
        current_logs["delta"] = current_logs["delta"].apply(lambda x: x / 100.0 if abs(x) >= 20.0 else x)
else:
    current_logs = pd.DataFrame()

if not current_students.empty:
    if not current_grades.empty and "stt" in current_grades.columns:
        merged_view = current_students.merge(current_grades, left_on=["stt_display", "lop"], right_on=["stt", "lop"], how="left")
    else:
        merged_view = current_students.copy()
else:
    merged_view = pd.DataFrame()

for c in tx_cols:
    if c not in merged_view.columns:
        merged_view[c] = ""

if not current_logs.empty and "type" in current_logs.columns and "stt" in current_logs.columns:
    plus_df = current_logs[current_logs["type"].astype(str).str.upper().str.strip() == "PLUS"]
    minus_df = current_logs[current_logs["type"].astype(str).str.upper().str.strip() == "MINUS"]
    plus_map = plus_df.groupby("stt")["delta"].sum().to_dict()
    minus_map = minus_df.groupby("stt")["delta"].sum().to_dict()
else:
    plus_map, minus_map = {}, {}

if not merged_view.empty and "stt_display" in merged_view.columns:
    merged_view["Diem_Cong"] = merged_view["stt_display"].astype(str).map(plus_map).fillna(0.0).round(2)
    merged_view["Diem_Tru"] = merged_view["stt_display"].astype(str).map(minus_map).fillna(0.0).round(2)
else:
    merged_view["Diem_Cong"] = 0.0
    merged_view["Diem_Tru"] = 0.0

# ==================== NỘI DUNG CÁC TAB ====================
st.markdown(f"# 📺 LỚP: {selected_lop} — MÔN: {selected_mon}")

if st.session_state["authenticated"]:
    tab_tv, tab_picker, tab_leaderboard, tab_export = st.tabs([
        "📋 Bảng Tổng Hợp Chiếu TV", 
        "🎯 Gọi Tên Ngẫu Nhiên", 
        "🏆 Bảng Xếp Hạng Tích Cực",
        "📥 Xuất Điểm vnEdu"
    ])
else:
    tab_tv, tab_leaderboard = st.tabs([
        "📋 Bảng Tổng Hợp Chiếu TV", 
        "🏆 Bảng Xếp Hạng Tích Cực"
    ])
    tab_picker = None
    tab_export = None

# TAB 1: BẢNG TỔNG HỢP VÀ GHI ĐIỂM
with tab_tv:
    if st.session_state["authenticated"] and not current_students.empty:
        st.markdown("#### ⚡ Ghi nhận thi đua nhanh tại lớp")
        student_options = [f"{row['stt_display']} - {row['ho_va_ten']}" for _, row in current_students.iterrows()]
        col_type, col_hs, col_val, col_btn = st.columns([2, 3, 2, 2])
        with col_type:
            action_type = st.radio("Hành động:", ["⭐ Cộng điểm (+)", "⚠️ Nhắc nhở (-)"], horizontal=True, key=f"act_type_{selected_lop}")
        with col_hs:
            selected_student_str = st.selectbox("Chọn học sinh:", student_options, key=f"quick_student_{selected_lop}")
        
        target_stt = selected_student_str.split(" - ")[0].strip()
        
        if "Cộng điểm" in action_type:
            with col_val:
                delta_score = st.select_slider("Mức cộng (+):", options=[0.25, 0.5, 0.75, 1.0], value=0.25, format_func=lambda x: f"+{x:.2f}")
            with col_btn:
                st.write("")
                if st.button("⭐ Cộng điểm ngay", type="primary", key="btn_quick_add"):
                    ws_logs.append_row([
                        f"L{len(df_logs)+1}", target_stt, str(selected_lop), selected_mon,
                        str(date.today()), "PLUS", float(delta_score), "Xung phong phát biểu", ""
                    ], value_input_option="USER_ENTERED")
                    st.success(f"Đã cộng +{delta_score:.2f}!")
                    time.sleep(0.8)
                    st.cache_data.clear()
                    st.rerun()
        else:
            with col_val:
                minus_score = st.select_slider("Mức phạt (-):", options=[-0.25, -0.5, -0.75, -1.0], value=-0.25, format_func=lambda x: f"{x:.2f}")
            with col_btn:
                st.write("")
                if st.button("⚠️ Ghi nhận lỗi", type="secondary", key="btn_quick_sub"):
                    ws_logs.append_row([
                        f"L{len(df_logs)+1}", target_stt, str(selected_lop), selected_mon,
                        str(date.today()), "MINUS", float(minus_score), "Nhắc nhở nề nếp / học tập", ""
                    ], value_input_option="USER_ENTERED")
                    st.warning(f"Đã trừ {minus_score:.2f} điểm!")
                    time.sleep(0.8)
                    st.cache_data.clear()
                    st.rerun()
        st.markdown("---")

    st.markdown("### 🌟 Tiến độ & Tương tác toàn lớp")
    if not merged_view.empty:
        cols_show = [c for c in ["stt_display", "ho_va_ten", "Diem_Cong", "Diem_Tru"] + tx_cols if c in merged_view.columns]
        display_df = merged_view[cols_show].copy()
        rename_dict = {"stt_display": "STT", "ho_va_ten": "Họ và Tên", "Diem_Cong": "⭐ Điểm (+)", "Diem_Tru": "⚠️ Nhắc nhở (-)"}
        for c in tx_cols:
            rename_dict[c] = c.upper()
        display_df.rename(columns=rename_dict, inplace=True)
        st.dataframe(display_df.style.format({"⭐ Điểm (+)": "{:.2f}", "⚠️ Nhắc nhở (-)": "{:.2f}"}), use_container_width=True, hide_index=True, height=450)

# TAB 2: QUAY TÊN NGẪU NHIÊN
if tab_picker is not None:
    with tab_picker:
        st.markdown("### 🎯 Vòng quay gọi bài công bằng")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            picker_type = st.radio("Mục tiêu gọi tên:", ["Theo cột điểm TX", "⭐ Theo điểm thưởng (+)"], horizontal=True)
            if picker_type == "Theo cột điểm TX":
                target_tx = st.selectbox("Chọn cột TX cần kiểm tra:", tx_cols)
                picker_mode = st.radio("Chế độ lọc:", ["Ưu tiên bạn chưa có điểm ở cột này", "Ngẫu nhiên toàn bộ lớp"])
                if not merged_view.empty:
                    pool = merged_view[merged_view[target_tx].astype(str).str.strip() == ""] if picker_mode == "Ưu tiên bạn chưa có điểm ở cột này" else merged_view
                    if pool.empty: pool = merged_view
                else: pool = pd.DataFrame()
            else:
                target_tx = "tx1"
                st.info("💡 Ưu tiên các bạn chưa có sao thưởng (0.00), sau đó đến nhóm điểm thưởng thấp nhất lớp.")
                if not merged_view.empty:
                    zero_star_pool = merged_view[merged_view["Diem_Cong"] == 0.0]
                    pool = zero_star_pool if not zero_star_pool.empty else merged_view[merged_view["Diem_Cong"] == merged_view["Diem_Cong"].min()]
                else: pool = pd.DataFrame()

            btn_spin = st.button("🎲 QUAY GỌI TÊN", type="primary")

        with col_p2:
            if btn_spin and not pool.empty:
                chosen_row = pool.sample(n=1).iloc[0]
                placeholder = st.empty()
                all_names = current_students["ho_va_ten"].tolist() if "ho_va_ten" in current_students.columns else ["Học sinh"]
                for _ in range(10):
                    temp_name = random.choice(all_names)
                    placeholder.markdown(f"<h1 style='text-align: center; color: #3498db;'>🎲 {temp_name}</h1>", unsafe_allow_html=True)
                    time.sleep(0.08)
                ten_hs = chosen_row.get('ho_va_ten', 'Học sinh')
                stt_hs = chosen_row.get('stt_display', '')
                d_cong = chosen_row.get('Diem_Cong', 0.0)
                placeholder.markdown(f"<h1 style='text-align: center; color: #2ecc71; border: 3px solid #2ecc71; padding: 15px; border-radius: 12px;'>🎉 {ten_hs} (STT: {stt_hs}) — ⭐ +{d_cong:.2f}</h1>", unsafe_allow_html=True)
                st.session_state["chosen_student"] = chosen_row
                
            if "chosen_student" in st.session_state:
                s = st.session_state["chosen_student"]
                ten_hien_thi = s.get('ho_va_ten', 'Học sinh')
                stt_hien_thi = str(s.get('stt_display', ''))
                st.markdown(f"#### 📝 Đánh giá: **STT {stt_hien_thi} - {ten_hien_thi}**")
                action = st.radio("Chọn thao tác:", ["Vào điểm trực tiếp cột TX", "Cộng điểm thưởng (+)", "Trừ điểm / Ghi nhận lỗi (-)"], horizontal=True)
                
                if action == "Vào điểm trực tiếp cột TX":
                    col_target_sel = st.selectbox("Chọn cột TX:", tx_cols, key="tx_pick_box")
                    c_score, c_save = st.columns([2, 1])
                    score_val = c_score.number_input(f"Nhập điểm {col_target_sel.upper()}:", min_value=0.0, max_value=10.0, value=8.0, step=0.25, format="%.2f")
                    if c_save.button("💾 Lưu điểm TX"):
                        cell_list = ws_grades.findall(stt_hien_thi)
                        col_index = ["tx1", "tx2", "tx3", "tx4", "tx5", "tx6"].index(col_target_sel) + 4
                        updated = False
                        for cell in cell_list:
                            row_vals = ws_grades.row_values(cell.row)
                            if len(row_vals) >= 3 and str(row_vals[1]).strip().upper() == str(selected_lop).strip().upper():
                                ws_grades.update_cell(cell.row, col_index, float(score_val))
                                updated = True
                                break
                        if not updated:
                            new_row = [stt_hien_thi, str(selected_lop), selected_mon] + [""] * 6
                            new_row[col_index - 1] = float(score_val)
                            ws_grades.append_row(new_row, value_input_option="USER_ENTERED")
                        st.success("Đã lưu điểm thành công!")
                        time.sleep(0.8)
                        st.cache_data.clear()
                        st.rerun()

                elif action == "Cộng điểm thưởng (+)":
                    c_r, c_val, c_save = st.columns([2, 1, 1])
                    reason = c_r.selectbox("Lý do:", ["Hăng hái phát biểu", "Câu trả lời xuất sắc", "Bài tập làm tốt", "Khác"])
                    delta_val = c_val.select_slider("Số điểm:", options=[0.25, 0.5, 0.75, 1.0], value=0.5, format_func=lambda x: f"+{x:.2f}")
                    if c_save.button("⭐ Tặng sao"):
                        ws_logs.append_row([
                            f"L{len(df_logs)+1}", stt_hien_thi, str(selected_lop), selected_mon,
                            str(date.today()), "PLUS", float(delta_val), reason, ""
                        ], value_input_option="USER_ENTERED")
                        st.success("Đã cộng điểm!")
                        time.sleep(0.8)
                        st.cache_data.clear()
                        st.rerun()
                else:
                    c_err, c_val, c_save = st.columns([2, 1, 1])
                    err_type = c_err.selectbox("Lỗi:", ["Không thuộc bài", "Chưa nắm kiến thức", "Chưa làm bài tập", "Mất trật tự"])
                    minus_val = c_val.number_input("Điểm trừ:", min_value=-5.0, max_value=-0.25, value=-0.5, step=0.25, format="%.2f")
                    if c_save.button("⚠️ Ghi nhận lỗi"):
                        ws_logs.append_row([
                            f"L{len(df_logs)+1}", stt_hien_thi, str(selected_lop), selected_mon,
                            str(date.today()), "MINUS", float(minus_val), err_type, ""
                        ], value_input_option="USER_ENTERED")
                        st.warning("Đã ghi nhận nhắc nhở!")
                        time.sleep(0.8)
                        st.cache_data.clear()
                        st.rerun()

# TAB 3: BẢNG XẾP HẠNG
with tab_leaderboard:
    st.markdown("### 🏆 Bảng Vàng Tích Cực")
    if not merged_view.empty:
        top_stars = merged_view[merged_view["Diem_Cong"] > 0].sort_values(by="Diem_Cong", ascending=False)
        if not top_stars.empty:
            for idx, row in top_stars.head(5).iterrows():
                st.markdown(f"#### 🥇 **{row.get('ho_va_ten', '')}** (STT {row.get('stt_display', '')}) — ⭐ **+{row['Diem_Cong']:.2f} Điểm**")
        else:
            st.info("Chưa có điểm cộng tích cực nào được ghi nhận.")

# TAB 4: XUẤT VNEDU
if tab_export is not None:
    with tab_export:
        st.markdown("### 📥 Bảng điểm định dạng chuẩn vnEdu")
        if not merged_view.empty:
            cols_exp = [c for c in ["stt_display", "ho_va_ten"] + tx_cols if c in merged_view.columns]
            export_df = merged_view[cols_exp].copy()
            rename_exp = {"stt_display": "STT", "ho_va_ten": "Họ và Tên"}
            for c in tx_cols:
                rename_exp[c] = c.upper()
            export_df.rename(columns=rename_exp, inplace=True)
            st.dataframe(export_df, hide_index=True, use_container_width=True)