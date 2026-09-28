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
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🛫 EVG Journey Engine - Executive Dashboard</h1>", unsafe_allow_html=True)
    
    # Lấy dữ liệu cơ sở cho bộ lọc
    df_raw = load_data("""
        SELECT 
            j.journey_id, j.sales_month, j.selling_price as rev, j.margin as profit, 
            j.pax_count as pax, j.segments, j.rev_2025, j.rev_lm, j.kpi_target,
            j.market_type, s.channel_type as cus_type, s.region as mien,
            j.supplier_id, sup.type as sup_type, sup.is_airline, s.name as agency_name,
            j.route, j.flight_type
        FROM fact_journey j
        LEFT JOIN dim_sales_unit s ON j.sales_unit_id = s.sales_unit_id
        LEFT JOIN dim_supplier sup ON j.supplier_id = sup.supplier_id
    """)

    # SIDEBAR - BỘ LỌC TỔNG THỂ (Global Filters)
    st.sidebar.header("BỘ LỌC (FILTERS)")
    
    months = sorted(df_raw['sales_month'].dropna().unique())
    selected_months = st.sidebar.multiselect("Sales_Month", options=months, default=months)
    
    miens = sorted(df_raw['mien'].dropna().unique())
    selected_mien = st.sidebar.multiselect("MIỀN", options=miens, default=miens)
    
    nd_qt = st.sidebar.multiselect("NĐ/QT (Market)", options=["DOM_VN", "INT_INT", "FROM_VN", "TO_VN", "OUTSIDE_VN"], default=["DOM_VN", "FROM_VN", "TO_VN"])
    
    cus_types = sorted(df_raw['cus_type'].dropna().unique())
    selected_cus = st.sidebar.multiselect("Cus Type (Đại lý/DN)", options=cus_types, default=cus_types)

    # Lọc dữ liệu
    df_filtered = df_raw.copy()
    if selected_months: df_filtered = df_filtered[df_filtered['sales_month'].isin(selected_months)]
    if selected_mien: df_filtered = df_filtered[df_filtered['mien'].isin(selected_mien)]
    if nd_qt: df_filtered = df_filtered[df_filtered['market_type'].isin(nd_qt)]
    if selected_cus: df_filtered = df_filtered[df_filtered['cus_type'].isin(selected_cus)]

    # TABS CHÍNH
    tab1, tab2, tab3, tab4 = st.tabs(["1. Tổng Quan KPI", "2. Xu Hướng Doanh Thu", "3. Hiệu Quả Đại Lý", "4. Airlines & Tuyến Bay"])

    with tab1:
        render_overview(df_filtered, df_raw)
    with tab2:
        render_trends(df_filtered)
    with tab3:
        render_agencies(df_filtered)
    with tab4:
        render_airlines(df_filtered)


def render_overview(df, df_all):
    # Tính toán các chỉ số tổng
    rev = df['rev'].sum()
    rev_2025 = df['rev_2025'].sum()
    rev_lm = df['rev_lm'].sum()
    kpi = df['kpi_target'].sum()
    profit = df['profit'].sum()
    pax = df['pax'].sum()
    trans = df['journey_id'].nunique()
    segs = df['segments'].sum()

    # Tính tỷ lệ
    pct_tang_giam = (rev - rev_2025) / rev_2025 if rev_2025 else 0
    pct_kpi = rev / kpi if kpi else 0
    
    # Tính Company total (để tính % Công ty)
    rev_company = df_all['rev'].sum()
    pct_cong_ty = rev / rev_company if rev_company else 0

    st.markdown("### 🏆 KPI TỔNG DOANH SỐ & LỢI NHUẬN")
    
    # Hàng 1: Tổng Doanh Số
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"**TỔNG DOANH SỐ**: {format_vnd(rev)} | Cùng kỳ: {format_vnd(rev_2025)} ({format_pct(pct_tang_giam)}) | KPI: {format_vnd(kpi)} ({format_pct(pct_kpi)}) | % Công ty: {format_pct(pct_cong_ty)}")
    with col2:
        st.success(f"**TỔNG LỢI NHUẬN**: {format_vnd(profit)} | Tỷ suất: {format_pct(profit/rev if rev else 0)}")

    # Hàng 2: Các chỉ số khối lượng
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng Số Khách", f"{pax:,.0f} khách", f"{(pax - df['pax'].mean() * len(df['sales_month'].unique())):,.0f} vs Tháng trước")
    c2.metric("Tổng Giao Dịch", f"{trans:,.0f} giao dịch")
    c3.metric("Tổng Segment", f"{segs:,.0f} segs")

    st.markdown("---")
    st.markdown("### 📊 PHÂN BỔ CẤU TRÚC DOANH THU")
    
    r1c1, r1c2, r1c3 = st.columns(3)
    
    # Nội địa vs Quốc tế
    rev_nd = df[df['market_type'] == 'DOM_VN']['rev'].sum()
    rev_qt = df[df['market_type'] != 'DOM_VN']['rev'].sum()
    
    with r1c1:
        st.markdown(f"**Nội Địa**: {format_vnd(rev_nd)} ({format_pct(rev_nd/rev if rev else 0)})")
        st.markdown(f"**Quốc Tế**: {format_vnd(rev_qt)} ({format_pct(rev_qt/rev if rev else 0)})")
        
    # Đại lý vs Doanh nghiệp
    rev_dl = df[df['cus_type'] == 'AGENCY']['rev'].sum()
    rev_dn = df[df['cus_type'] == 'CORPORATE']['rev'].sum()
    
    with r1c2:
        st.markdown(f"**Đại lý (F2/Agency)**: {format_vnd(rev_dl)} ({format_pct(rev_dl/rev if rev else 0)})")
        st.markdown(f"**Doanh nghiệp (CA)**: {format_vnd(rev_dn)} ({format_pct(rev_dn/rev if rev else 0)})")
        
    # Flight vs Non-Air
    rev_flight = df[df['is_airline'] == 1]['rev'].sum()
    rev_nonair = df[df['sup_type'] == 'NON_AIR']['rev'].sum()
    
    with r1c3:
        st.markdown(f"**Vé Máy Bay (Flight)**: {format_vnd(rev_flight)} ({format_pct(rev_flight/rev if rev else 0)})")
        st.markdown(f"**Dịch vụ ngoài (Non Air)**: {format_vnd(rev_nonair)} ({format_pct(rev_nonair/rev if rev else 0)})")

def render_trends(df):
    st.markdown("### 📈 XU HƯỚNG THEO THÁNG (Sales_Month)")
    
    # Nhóm theo tháng
    df_trend = df.groupby('sales_month').agg(
        Rev=('rev', 'sum'),
        Rev_2025=('rev_2025', 'sum'),
        Rev_LM=('rev_lm', 'sum'),
        Profit=('profit', 'sum'),
        Pax=('pax', 'sum')
    ).reset_index()
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Rev_LM'], name='Rev_LM', marker_color='#1f77b4'))
    fig1.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Rev'], name='Rev', marker_color='#00008B'))
    fig1.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Rev_2025'], name='Rev_2025', marker_color='#ff7f0e'))
    fig1.add_trace(go.Scatter(x=df_trend['sales_month'], y=df_trend['Profit'], name='Profit', mode='lines+markers', yaxis='y2', line=dict(color='purple', width=3)))
    
    fig1.update_layout(
        title="Rev, Rev_LM, Rev_2025 và Profit theo Sales_Month",
        barmode='group',
        yaxis=dict(title='Doanh thu (VND)'),
        yaxis2=dict(title='Lợi nhuận (VND)', overlaying='y', side='right'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # GTTB_PAX và Pax
    df_trend['GTTB_PAX'] = df_trend['Rev'] / df_trend['Pax']
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df_trend['sales_month'], y=df_trend['Pax'], name='Pax', marker_color='#00bfff'))
    fig2.add_trace(go.Scatter(x=df_trend['sales_month'], y=df_trend['GTTB_PAX'], name='GTTB_PAX', mode='lines+markers', yaxis='y2', line=dict(color='red', width=3)))
    fig2.update_layout(
        title="GTTB_PAX và Pax theo Sales_Month",
        yaxis=dict(title='Số Pax'),
        yaxis2=dict(title='GTTB_PAX (Giá trị TB/Pax)', overlaying='y', side='right')
    )
    st.plotly_chart(fig2, use_container_width=True)

def render_agencies(df):
    st.markdown("### 🏢 HIỆU QUẢ ĐẠI LÝ (AGENCY PERFORMANCE)")
    
    df_ag = df.groupby('agency_name').agg(
        Rev=('rev', 'sum'),
        Rev_2025_Context=('rev_2025', 'sum'),
        Profit=('profit', 'sum'),
        Pax=('pax', 'sum')
    ).reset_index()
    
    df_ag['Up/Down_Rev'] = df_ag['Rev'] - df_ag['Rev_2025_Context']
    df_ag['%Tăng/Giảm'] = df_ag['Up/Down_Rev'] / df_ag['Rev_2025_Context'] * 100
    df_ag['%Profit_Rate'] = df_ag['Profit'] / df_ag['Rev'] * 100
    
    df_ag = df_ag.sort_values(by='Rev', ascending=False)
    
    # Định dạng
    df_ag_display = df_ag.copy()
    df_ag_display['Rev'] = df_ag_display['Rev'].apply(lambda x: f"{x:,.0f}")
    df_ag_display['Rev_2025_Context'] = df_ag_display['Rev_2025_Context'].apply(lambda x: f"{x:,.0f}")
    df_ag_display['Up/Down_Rev'] = df_ag_display['Up/Down_Rev'].apply(lambda x: f"{x:,.0f}")
    df_ag_display['Profit'] = df_ag_display['Profit'].apply(lambda x: f"{x:,.0f}")
    df_ag_display['%Tăng/Giảm'] = df_ag_display['%Tăng/Giảm'].apply(lambda x: f"{x:,.2f}%")
    df_ag_display['%Profit_Rate'] = df_ag_display['%Profit_Rate'].apply(lambda x: f"{x:,.2f}%")
    
    st.dataframe(df_ag_display, use_container_width=True, height=500)

def render_airlines(df):
    st.markdown("### ✈️ NHÓM AIRLINES & TUYẾN BAY")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Nhóm Airlines (BSP / Hãng VN / LCC)")
        df_al = df.groupby('supplier_id').agg(
            Rev=('rev', 'sum'),
            Profit=('profit', 'sum'),
            Pax=('pax', 'sum')
        ).reset_index().sort_values(by='Rev', ascending=False).head(10)
        
        fig = px.bar(df_al, x='supplier_id', y='Rev', color='Profit', text_auto='.2s', title="Top 10 Airlines theo Doanh Thu")
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Lưu lượng Tuyến Bay (O&D Flow)")
        df_route = df.groupby('route').agg(Rev=('rev', 'sum')).reset_index().sort_values(by='Rev', ascending=False).head(10)
        fig2 = px.bar(df_route, y='route', x='Rev', orientation='h', title="Top 10 Tuyến Bay (O&D) có Doanh Thu Cao Nhất")
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

if __name__ == "__main__":
    main()
