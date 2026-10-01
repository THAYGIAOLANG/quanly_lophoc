# 3. Thanh bên điều hướng (Sidebar)
st.sidebar.title("⚙️ QUẢN TRỊ LỚP HỌC")
st.sidebar.markdown("---")

# ==================== ĐƯA LÊN TRÊN: BỘ LỌC MÔN VÀ LỚP ====================
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

st.sidebar.markdown("---")

# ==================== ĐƯA XUỐNG DƯỚI: KHỐI ĐĂNG NHẬP / XÁC THỰC ====================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "qr_session_id" not in st.session_state:
    st.session_state["qr_session_id"] = f"SES_{random.randint(1000, 9999)}_{int(time.time())}"

if not st.session_state["authenticated"]:
    st.sidebar.subheader("📲 Đăng nhập bằng mã QR")
    st.sidebar.caption("Dùng Zalo / Camera quét mã để mở quyền quản trị:")
    
    current_session = st.session_state["qr_session_id"]
    auth_url = f"https://lophocthayhoanghienhau.streamlit.app/?auth_token={current_session}"
    
    qr = qrcode.QRCode(box_size=5, border=2)  # Thu nhỏ nhẹ để vừa vặn khung hình
    qr.add_data(auth_url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img_qr.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), caption="Mã QR phiên làm việc", use_container_width=True)
    
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