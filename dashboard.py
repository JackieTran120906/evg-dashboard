"""
EVG Journey Engine - PowerBI Clone Dashboard (Streamlit)
"""
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="EVG PowerBI Dashboard", layout="wide")

DB_PATH = Path("evg_data.db")
if not DB_PATH.exists():
    DB_PATH = Path("output/evg_data.db")

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "evg2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>BẢO MẬT HỆ THỐNG DỮ LIỆU</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Vui lòng nhập mật khẩu cấp độ Quản lý để truy cập Dashboard.</p>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Nhập Mật Khẩu (Password: evg2026)", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center;'>BẢO MẬT HỆ THỐNG DỮ LIỆU</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Nhập Mật Khẩu (Password: evg2026)", type="password", on_change=password_entered, key="password")
            st.error("Mật khẩu không chính xác. Đã ghi nhận cảnh báo truy cập.")
        return False
    return True

@st.cache_data
def load_data(query: str):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)

def format_vnd(val):
    if pd.isna(val): return "0"
    if val >= 1e9: return f"{val/1e9:,.2f} tỷ"
    if val >= 1e6: return f"{val/1e6:,.2f} triệu"
    return f"{val:,.0f}"

def format_pct(val):
    if pd.isna(val): return "0%"
    return f"{val * 100:,.2f}%"

def main():
    if not check_password():
        return

    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🛫 EVG Journey Engine - Executive Dashboard</h1>", unsafe_allow_html=True)
    
    if not DB_PATH.exists():
        st.error("Database không tồn tại. Vui lòng đảm bảo file evg_data.db đã được upload!")
        st.stop()

    df_raw = load_data("""
        SELECT 
            j.journey_id, j.sales_month, j.travel_month, j.selling_price as rev, j.margin as profit, 
            j.pax_count as pax, j.segments, j.rev_2025, j.rev_lm, j.kpi_target,
            j.market_type, s.channel_type as cus_type, s.region as mien, s.province,
            j.supplier_id, sup.type as sup_type, sup.is_airline, s.name as agency_name,
            j.route, j.flight_type, j.origin_continent, j.dest_continent, j.booker_name
        FROM fact_journey j
        LEFT JOIN dim_sales_unit s ON j.sales_unit_id = s.sales_unit_id
        LEFT JOIN dim_supplier sup ON j.supplier_id = sup.supplier_id
    """)

    # SIDEBAR - FILTERS
    st.sidebar.header("BỘ LỌC (FILTERS)")
    
    months = sorted(df_raw['sales_month'].dropna().unique())
    selected_months = st.sidebar.multiselect("Sales_Month", options=months, default=months)
    
    miens = sorted(df_raw['mien'].dropna().unique())
    selected_mien = st.sidebar.multiselect("MIỀN", options=miens, default=miens)
    
    nd_qt = st.sidebar.multiselect("NĐ/QT (Market)", options=["DOM_VN", "INT_INT", "FROM_VN", "TO_VN", "OUTSIDE_VN"], default=["DOM_VN", "FROM_VN", "TO_VN", "OUTSIDE_VN", "INT_INT"])
    
    cus_types = sorted(df_raw['cus_type'].dropna().unique())
    selected_cus = st.sidebar.multiselect("Cus Type (Đại lý/DN)", options=cus_types, default=cus_types)

    df_filtered = df_raw.copy()
    if selected_months: df_filtered = df_filtered[df_filtered['sales_month'].isin(selected_months)]
    if selected_mien: df_filtered = df_filtered[df_filtered['mien'].isin(selected_mien)]
    if nd_qt: df_filtered = df_filtered[df_filtered['market_type'].isin(nd_qt)]
    if selected_cus: df_filtered = df_filtered[df_filtered['cus_type'].isin(selected_cus)]

    # 10 TABS
    tabs = st.tabs([
        "1. Tổng Quan KPI", "2. Xu Hướng", "3. Hiệu Quả Đại Lý", "4. Airlines & Tuyến Bay",
        "5. Châu Lục", "6. Cấu trúc chuyến", "7. Tỉnh/TP", "8. Booker", "9. Nhóm KPI", "10. Non-Air"
    ])

    with tabs[0]: render_overview(df_filtered, df_raw)
    with tabs[1]: render_trends(df_filtered)
    with tabs[2]: render_agencies(df_filtered)
    with tabs[3]: render_airlines(df_filtered)
    with tabs[4]: render_continents(df_filtered)
    with tabs[5]: render_routes(df_filtered)
    with tabs[6]: render_provinces(df_filtered)
    with tabs[7]: render_bookers(df_filtered)
    with tabs[8]: render_kpi(df_filtered)
    with tabs[9]: render_non_air(df_filtered)

def render_overview(df, df_all):
    rev = df['rev'].sum()
    rev_2025 = df['rev_2025'].sum()
    rev_lm = df['rev_lm'].sum()
    kpi = df['kpi_target'].sum()
    profit = df['profit'].sum()
    pax = df['pax'].sum()
    trans = df['journey_id'].nunique()
    segs = df['segments'].sum()

    pct_tang_giam = (rev - rev_2025) / rev_2025 if rev_2025 else 0
    pct_kpi = rev / kpi if kpi else 0
    rev_company = df_all['rev'].sum()
    pct_cong_ty = rev / rev_company if rev_company else 0

    st.markdown("### 🏆 KPI TỔNG DOANH SỐ & LỢI NHUẬN")
    col1, col2 = st.columns([3, 1])
    with col1: st.info(f"**TỔNG DOANH SỐ**: {format_vnd(rev)} | Cùng kỳ: {format_vnd(rev_2025)} ({format_pct(pct_tang_giam)}) | KPI: {format_vnd(kpi)} ({format_pct(pct_kpi)}) | % Công ty: {format_pct(pct_cong_ty)}")
    with col2: st.success(f"**TỔNG LỢI NHUẬN**: {format_vnd(profit)} | Tỷ suất: {format_pct(profit/rev if rev else 0)}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng Số Khách", f"{pax:,.0f} khách", f"{(pax - df['pax'].mean() * len(df['sales_month'].unique())):,.0f} vs Tháng trước")
    c2.metric("Tổng Giao Dịch", f"{trans:,.0f} giao dịch")
    c3.metric("Tổng Segment", f"{segs:,.0f} segs")

def render_trends(df):
    st.markdown("### 📈 XU HƯỚNG THEO THÁNG (Sales_Month)")
    df_trend = df.groupby('sales_month').agg(Rev=('rev', 'sum'), Rev_2025=('rev_2025', 'sum'), Rev_LM=('rev_lm', 'sum'), Profit=('profit', 'sum'), Pax=('pax', 'sum')).reset_index()
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Rev_LM'], name='Rev_LM'))
    fig1.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Rev'], name='Rev'))
    fig1.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Rev_2025'], name='Rev_2025'))
    fig1.add_trace(go.Scatter(x=df_trend['sales_month'], y=df_trend['Profit'], name='Profit', yaxis='y2'))
    fig1.update_layout(barmode='group', yaxis2=dict(overlaying='y', side='right'))
    st.plotly_chart(fig1, use_container_width=True)

def render_agencies(df):
    st.markdown("### 🏢 HIỆU QUẢ ĐẠI LÝ")
    df_ag = df.groupby('agency_name').agg(Rev=('rev', 'sum'), Rev_2025=('rev_2025', 'sum'), Profit=('profit', 'sum'), Pax=('pax', 'sum')).reset_index()
    df_ag['%Tăng/Giảm'] = (df_ag['Rev'] - df_ag['Rev_2025']) / df_ag['Rev_2025'] * 100
    df_ag = df_ag.sort_values(by='Rev', ascending=False).head(50)
    st.dataframe(df_ag.style.format({'Rev': '{:,.0f}', 'Rev_2025': '{:,.0f}', 'Profit': '{:,.0f}', '%Tăng/Giảm': '{:.2f}%'}), use_container_width=True)

def render_airlines(df):
    st.markdown("### ✈️ NHÓM AIRLINES & TUYẾN BAY")
    df_al = df.groupby('supplier_id').agg(Rev=('rev', 'sum')).reset_index().sort_values(by='Rev', ascending=False).head(10)
    st.plotly_chart(px.bar(df_al, x='supplier_id', y='Rev', text_auto='.2s', title="Top 10 Airlines"), use_container_width=True)

def render_continents(df):
    st.markdown("### 🌍 PHÂN TÍCH CHÂU LỤC (ORIGIN/DESTINATION CONTINENT)")
    df_cont = df.groupby(['origin_continent', 'dest_continent']).agg(Rev=('rev', 'sum'), Pax=('pax', 'sum')).reset_index()
    df_cont = df_cont[df_cont['origin_continent'] != ""]
    st.dataframe(df_cont.style.format({'Rev': '{:,.0f}', 'Pax': '{:,.0f}'}), use_container_width=True)

def render_routes(df):
    st.markdown("### 🔄 PHÂN TÍCH CHUYẾN BAY (CẤU TRÚC)")
    df_flight = df.groupby('flight_type').agg(Rev=('rev', 'sum'), Segs=('segments', 'sum')).reset_index()
    st.plotly_chart(px.pie(df_flight, names='flight_type', values='Rev', title="Doanh thu theo Loại Chặng (Khứ hồi/Một chiều)"), use_container_width=True)

def render_provinces(df):
    st.markdown("### 📍 PHÂN TÍCH TỈNH/THÀNH PHỐ")
    df_prov = df.groupby(['mien', 'province']).agg(Rev=('rev', 'sum'), Rev_2025=('rev_2025', 'sum')).reset_index()
    df_prov = df_prov.sort_values(by='Rev', ascending=False).head(20)
    st.dataframe(df_prov.style.format({'Rev': '{:,.0f}', 'Rev_2025': '{:,.0f}'}), use_container_width=True)

def render_bookers(df):
    st.markdown("### 👨‍💻 PHÂN TÍCH BOOKER (NGƯỜI ĐẶT VÉ)")
    df_b = df.groupby('booker_name').agg(Trans_Count=('journey_id', 'nunique'), Pax=('pax', 'sum'), Rev=('rev', 'sum'), Profit=('profit', 'sum')).reset_index()
    df_b = df_b[df_b['booker_name'] != ""]
    df_b = df_b.sort_values(by='Rev', ascending=False).head(20)
    st.dataframe(df_b.style.format({'Rev': '{:,.0f}', 'Profit': '{:,.0f}'}), use_container_width=True)

def render_kpi(df):
    st.markdown("### 🎯 NHÓM KPI (VNA vs HÃNG KHÁC)")
    df['kpi_group'] = df['supplier_id'].apply(lambda x: "VNA" if x == 'VN' else "Hãng Khác")
    df_k = df.groupby(['sales_month', 'kpi_group']).agg(Rev=('rev', 'sum'), KPI=('kpi_target', 'sum')).reset_index()
    df_k['%Hoàn thành'] = df_k['Rev'] / df_k['KPI'] * 100
    st.dataframe(df_k.style.format({'Rev': '{:,.0f}', 'KPI': '{:,.0f}', '%Hoàn thành': '{:.2f}%'}), use_container_width=True)

def render_non_air(df):
    st.markdown("### 🏨 DỊCH VỤ NGOÀI (NON-AIR)")
    df_n = df[df['sup_type'] == 'NON_AIR'].groupby('supplier_id').agg(Rev=('rev', 'sum'), Profit=('profit', 'sum')).reset_index()
    if df_n.empty:
        st.warning("Không có dữ liệu Non-Air thỏa mãn bộ lọc hiện tại.")
    else:
        st.dataframe(df_n.style.format({'Rev': '{:,.0f}', 'Profit': '{:,.0f}'}), use_container_width=True)

if __name__ == "__main__":
    main()
