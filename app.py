import streamlit as st
import pandas as pd
from datetime import date
import random
import time
import os
import gspread
from google.oauth2.service_account import Credentials

# 1. Cấu hình giao diện Streamlit tối ưu hiển thị TV
st.set_page_config(page_title="THẦY HOÀNG HIỀN HẬU", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        header[data-testid="stHeader"] {
            display: none !important;
        }
        .block-container {
            padding-top: 2rem !important;
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

st.markdown('<div class="teacher-banner">✨ LỚP HỌC THẦY HOÀNG HIỀN HẬU ✨</div>', unsafe_allow_html=True)

# 2. Kết nối Google Sheets qua google-auth & gspread
current_dir = os.path.dirname(os.path.abspath(__file__))
JSON_KEY_FILE = os.path.join(current_dir, "service_account.json")
SHEET_TITLE = "Database_So_Theo_Doi_Hoc_Tap"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_sheets():
    creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open(SHEET_TITLE)
    return sh.worksheet("students"), sh.worksheet("grades"), sh.worksheet("behavior_logs")

try:
    ws_students, ws_grades, ws_logs = get_sheets()
except Exception as e:
    st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
    st.stop()

def load_all_data():
    df_s = pd.DataFrame(ws_students.get_all_records())
    df_g = pd.DataFrame(ws_grades.get_all_records())
    df_l = pd.DataFrame(ws_logs.get_all_records())
    
    for df in [df_s, df_g, df_l]:
        if not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            if "ma_hs" in df.columns and "stt" not in df.columns:
                df.rename(columns={"ma_hs": "stt"}, inplace=True)
                
    return df_s, df_g, df_l

df_students, df_grades, df_logs = load_all_data()

# 3. Quản lý trạng thái Đăng nhập
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

st.sidebar.title("⚙️ QUẢN TRỊ LỚP HỌC")

st.sidebar.markdown("---")
if not st.session_state["authenticated"]:
    st.sidebar.subheader("🔒 Đăng nhập Giáo viên")
    user_input = st.sidebar.text_input("Tài khoản:", key="login_user")
    pass_input = st.sidebar.text_input("Mật khẩu:", type="password", key="login_pass")
    
    if st.sidebar.button("Đăng nhập"):
        if user_input == "OHoang" and pass_input == "Toan6Tin9":
            st.session_state["authenticated"] = True
            st.sidebar.success("Đăng nhập thành công!")
            st.rerun()
        else:
            st.sidebar.error("Sai tài khoản hoặc mật khẩu!")
else:
    st.sidebar.success("🔓 Chế độ: **Giáo viên quản trị**")
    if st.sidebar.button("Đăng xuất"):
        st.session_state["authenticated"] = False
        st.rerun()

st.sidebar.markdown("---")

# Danh sách lựa chọn môn: "Toán" hoặc "Tin"
mon_list = ["Toán", "Tin"]
selected_mon = st.sidebar.selectbox("📖 Chọn Môn học:", mon_list)

# Cấu hình số cột TX: Toán 4 cột, Tin 2 cột
if selected_mon == "Toán":
    tx_cols = ["tx1", "tx2", "tx3", "tx4"]
else:
    tx_cols = ["tx1", "tx2"]

# Lọc danh sách lớp từ Google Sheet (dùng startswith để không bị nhầm số 6 ở cuối của 9A6)
if not df_students.empty and "lop" in df_students.columns:
    all_classes = [str(c).strip() for c in df_students["lop"].dropna().unique() if str(c).strip() != ""]
    if selected_mon == "Toán":
        available_classes = sorted([c for c in all_classes if c.startswith("6")])
    else:
        available_classes = sorted([c for c in all_classes if c.startswith("9")])
        
    if not available_classes:
        available_classes = sorted(all_classes)
else:
    available_classes = ["6A2", "6A3"] if selected_mon == "Toán" else ["9A1", "9A2", "9A5", "9A6", "9A7"]

selected_lop = st.sidebar.selectbox("🏫 Chọn Lớp:", available_classes)

if st.sidebar.button("🔄 Tải lại dữ liệu"):
    st.cache_resource.clear()
    st.rerun()

# Lọc học sinh theo lớp và tự động đánh số STT chuẩn 1..N
if not df_students.empty and "lop" in df_students.columns:
    current_students = df_students[df_students["lop"].astype(str).str.strip().str.upper() == str(selected_lop).strip().upper()].copy()
    if not current_students.empty:
        current_students.reset_index(drop=True, inplace=True)
        current_students["stt_display"] = (current_students.index + 1).astype(str)
else:
    current_students = pd.DataFrame()

# Lọc điểm theo lớp và môn
mon_keyword = "toán" if selected_mon == "Toán" else "tin"
if not df_grades.empty and "lop" in df_grades.columns and "mon_hoc" in df_grades.columns:
    current_grades = df_grades[
        (df_grades["lop"].astype(str).str.strip().str.upper() == str(selected_lop).strip().upper()) & 
        (df_grades["mon_hoc"].astype(str).str.lower().str.contains(mon_keyword))
    ].copy()
    if "stt" in current_grades.columns:
        current_grades["stt"] = current_grades["stt"].astype(str).str.strip()
else:
    current_grades = pd.DataFrame()

# Lọc nhật ký thi đua và chuẩn hóa số thập phân dấu chấm
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
else:
    current_logs = pd.DataFrame()

# Ghép dữ liệu hiển thị theo STT
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

# Tính tổng điểm cộng (+) và trừ (-)
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

# ==================== GIAO DIỆN CHÍNH ====================
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

# --- TAB 1: BẢNG TỔNG HỢP & GHI NHẬN NHANH ---
with tab_tv:
    if st.session_state["authenticated"] and not current_students.empty:
        st.markdown("#### ⚡ Ghi nhận điểm thưởng nhanh (Xung phong / Phát biểu)")
        
        student_options = [f"{row['stt_display']} - {row['ho_va_ten']}" for _, row in current_students.iterrows()]
        
        col_hs, col_diem, col_btn = st.columns([3, 2, 2])
        with col_hs:
            # Đoạn code mới (tự động làm mới khi đổi lớp):
            selected_student_str = st.selectbox("Chọn học sinh xung phong:", student_options, key=f"quick_student_{selected_lop}")
        with col_diem:
            delta_score = st.select_slider(
                "Mức điểm thưởng (+):",
                options=[0.25, 0.5, 0.75, 1.0],
                value=0.25,
                format_func=lambda x: f"+{x:.2f} điểm"
            )
        with col_btn:
            st.write("") 
            if st.button("⭐ Cộng điểm ngay", type="primary", key="btn_quick_add"):
                target_stt = selected_student_str.split(" - ")[0].strip()
                ws_logs.append_row([
                    f"L{len(df_logs)+1}", target_stt, str(selected_lop), selected_mon,
                    str(date.today()), "PLUS", float(delta_score), "Xung phong phát biểu", ""
                ], value_input_option="USER_ENTERED")
                st.success(f"Đã cộng +{delta_score:.2f} điểm cho {selected_student_str}!")
                time.sleep(1)
                st.cache_resource.clear()
                st.rerun()
        st.markdown("---")

    st.markdown("### 🌟 Tiến độ & Tương tác toàn lớp")
    if not merged_view.empty:
        cols_show = [c for c in ["stt_display", "ho_va_ten", "Diem_Cong", "Diem_Tru"] + tx_cols if c in merged_view.columns]
        display_df = merged_view[cols_show].copy()
        
        rename_dict = {
            "stt_display": "STT",
            "ho_va_ten": "Họ và Tên",
            "Diem_Cong": "⭐ Điểm (+)",
            "Diem_Tru": "⚠️ Nhắc nhở (-)"
        }
        for c in tx_cols:
            rename_dict[c] = c.upper()
            
        display_df.rename(columns=rename_dict, inplace=True)
        st.dataframe(
            display_df.style.format({
                "⭐ Điểm (+)": "{:.2f}",
                "⚠️ Nhắc nhở (-)": "{:.2f}"
            }),
            use_container_width=True,
            hide_index=True,
            height=450
        )
    else:
        st.info("Chưa có danh sách học sinh cho lớp này trên Google Sheets.")

# --- TAB 2: VÒNG QUAY NGẪU NHIÊN ---
if tab_picker is not None:
    with tab_picker:
        st.markdown("### 🎯 Vòng quay gọi bài ngẫu nhiên")
        
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            target_tx = st.selectbox("Chọn cột điểm cần kiểm tra:", tx_cols)
            picker_mode = st.radio("Chế độ lọc:", ["Ưu tiên bạn chưa có điểm ở cột này", "Ngẫu nhiên toàn bộ lớp"])
            
            if not merged_view.empty:
                if picker_mode == "Ưu tiên bạn chưa có điểm ở cột này":
                    pool = merged_view[merged_view[target_tx].astype(str).str.strip() == ""]
                    if pool.empty:
                        st.success("🎉 Tất cả học sinh đều đã có điểm ở cột này!")
                        pool = merged_view
                else:
                    pool = merged_view
            else:
                pool = pd.DataFrame()

            btn_spin = st.button("🎲 QUAY GỌI TÊN", type="primary")

        with col_p2:
            if btn_spin and not pool.empty:
                chosen_row = pool.sample(n=1).iloc[0]
                
                placeholder = st.empty()
                all_names = current_students["ho_va_ten"].tolist() if "ho_va_ten" in current_students.columns else ["Học sinh"]
                for _ in range(12):
                    temp_name = random.choice(all_names)
                    placeholder.markdown(f"<h1 style='text-align: center; color: #3498db;'>🎲 {temp_name}</h1>", unsafe_allow_html=True)
                    time.sleep(0.08)
                    
                ten_hs = chosen_row.get('ho_va_ten', 'Học sinh')
                stt_hs = chosen_row.get('stt_display', '')
                placeholder.markdown(f"<h1 style='text-align: center; color: #2ecc71; border: 3px solid #2ecc71; padding: 15px; border-radius: 12px;'>🎉 {ten_hs} (STT: {stt_hs})</h1>", unsafe_allow_html=True)
                st.session_state["chosen_student"] = chosen_row
                
            if "chosen_student" in st.session_state:
                s = st.session_state["chosen_student"]
                ten_hien_thi = s.get('ho_va_ten', 'Học sinh')
                stt_hien_thi = str(s.get('stt_display', ''))
                
                st.markdown(f"#### 📝 Chấm điểm cho: **STT {stt_hien_thi} - {ten_hien_thi}**")
                action = st.radio("Chọn thao tác:", ["Vào điểm trực tiếp cột TX", "Cộng điểm thưởng (+)", "Trừ điểm / Ghi nhận lỗi (-)"], horizontal=True)
                
                if action == "Vào điểm trực tiếp cột TX":
                    c_score, c_save = st.columns([2, 1])
                    score_val = c_score.number_input(f"Nhập điểm {target_tx.upper()}:", min_value=0.0, max_value=10.0, value=8.0, step=0.25, format="%.2f")
                    if c_save.button("💾 Lưu điểm TX"):
                        cell_list = ws_grades.findall(stt_hien_thi)
                        col_index = ["tx1", "tx2", "tx3", "tx4", "tx5", "tx6"].index(target_tx) + 4
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
                        time.sleep(1)
                        st.cache_resource.clear()
                        st.rerun()

                elif action == "Cộng điểm thưởng (+)":
                    c_r, c_val, c_save = st.columns([2, 1, 1])
                    reason = c_r.selectbox("Lý do:", ["Hăng hái phát biểu", "Câu trả lời xuất sắc", "Bài tập làm tốt", "Khác"])
                    delta_val = c_val.select_slider("Số điểm thưởng:", options=[0.25, 0.5, 0.75, 1.0], value=0.5, format_func=lambda x: f"+{x:.2f}")
                    if c_save.button("⭐ Tặng sao"):
                        ws_logs.append_row([
                            f"L{len(df_logs)+1}", stt_hien_thi, str(selected_lop), selected_mon,
                            str(date.today()), "PLUS", float(delta_val), reason, ""
                        ], value_input_option="USER_ENTERED")
                        st.success("Đã cộng điểm thành công!")
                        time.sleep(1)
                        st.cache_resource.clear()
                        st.rerun()

                else:
                    c_err, c_val, c_save = st.columns([2, 1, 1])
                    err_type = c_err.selectbox("Lỗi vi phạm:", ["Không thuộc bài", "Chưa nắm kiến thức cơ bản", "Chưa làm bài tập", "Mất trật tự"])
                    minus_val = c_val.number_input("Điểm trừ:", min_value=-5.0, max_value=-0.25, value=-0.5, step=0.25, format="%.2f")
                    if c_save.button("⚠️ Ghi nhận lỗi"):
                        ws_logs.append_row([
                            f"L{len(df_logs)+1}", stt_hien_thi, str(selected_lop), selected_mon,
                            str(date.today()), "MINUS", float(minus_val), err_type, ""
                        ], value_input_option="USER_ENTERED")
                        st.warning("Đã ghi nhận nhắc nhở!")
                        time.sleep(1)
                        st.cache_resource.clear()
                        st.rerun()

# --- TAB 3: BẢNG XẾP HẠNG TÍCH CỰC ---
with tab_leaderboard:
    st.markdown("### 🏆 Bảng Vàng Tích Cực")
    if not merged_view.empty:
        top_stars = merged_view[merged_view["Diem_Cong"] > 0].sort_values(by="Diem_Cong", ascending=False)
        if not top_stars.empty:
            for idx, row in top_stars.head(5).iterrows():
                st.markdown(f"#### 🥇 **{row.get('ho_va_ten', '')}** (STT {row.get('stt_display', '')}) — ⭐ **+{row['Diem_Cong']:.2f} Điểm**")
        else:
            st.info("Chưa có điểm cộng tích cực nào được ghi nhận.")

# --- TAB 4: XUẤT VNEDU ---
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