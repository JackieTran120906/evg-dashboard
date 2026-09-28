"""
EVG Journey Engine - Dashboard UI (Streamlit)
"""
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="EVG Dashboard", layout="wide")

# Đường dẫn tới DB
DB_PATH = Path("evg_data.db")

@st.cache_data
def load_data(query: str):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)

def check_db():
    if not DB_PATH.exists():
        st.error("Database không tồn tại. Vui lòng đảm bảo file evg_data.db đã được upload!")
        st.stop()

def main():
    st.title("🛫 EVG Journey Engine - Dashboard")
    check_db()

    page = st.sidebar.radio("Điều hướng", ["Tổng quan", "Phân tích Kênh Bán", "Phân tích NCC", "Hành khách & KH"])

    if page == "Tổng quan":
        show_overview()
    elif page == "Phân tích Kênh Bán":
        show_sales()
    elif page == "Phân tích NCC":
        show_suppliers()
    elif page == "Hành khách & KH":
        show_customers()

def show_overview():
    st.header("Tổng quan chung")
    df_kpi = load_data("SELECT COUNT(*) as tickets, SUM(selling_price) as revenue, SUM(margin) as total_margin FROM fact_journey")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng Số Vé", f"{df_kpi['tickets'][0]:,.0f}")
    c2.metric("Tổng Doanh Thu", f"{df_kpi['revenue'][0]:,.0f} VND")
    c3.metric("Tổng Lợi Nhuận", f"{df_kpi['total_margin'][0]:,.0f} VND")
    
    st.markdown("---")
    df_market = load_data("SELECT market_type, flight_type, COUNT(*) as count FROM fact_journey GROUP BY market_type, flight_type")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Phân bổ theo Thị trường")
        fig1 = px.pie(df_market, values='count', names='market_type', hole=0.4)
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Phân bổ theo Loại chặng bay")
        fig2 = px.pie(df_market, values='count', names='flight_type', hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

def show_sales():
    st.header("Phân tích Kênh Bán (Sales Units)")
    df_sales = load_data("SELECT s.channel_type, COUNT(j.journey_id) as tickets, SUM(j.selling_price) as revenue FROM fact_journey j JOIN dim_sales_unit s ON j.sales_unit_id = s.sales_unit_id GROUP BY s.channel_type")
    
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(df_sales, x='channel_type', y='revenue', color='channel_type', title="Doanh thu theo Kênh")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.pie(df_sales, values='tickets', names='channel_type', title="Số vé theo Kênh")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Đơn vị bán (Đại lý / Doanh nghiệp)")
    df_top = load_data("SELECT s.name, s.channel_type, COUNT(j.journey_id) as tickets, SUM(j.selling_price) as revenue FROM fact_journey j JOIN dim_sales_unit s ON j.sales_unit_id = s.sales_unit_id GROUP BY s.name, s.channel_type ORDER BY revenue DESC LIMIT 10")
    st.dataframe(df_top, use_container_width=True)

def show_suppliers():
    st.header("Phân tích Nhà Cung Cấp (Suppliers)")
    df_sup = load_data("SELECT s.type as supplier_type, COUNT(j.journey_id) as tickets FROM fact_journey j JOIN dim_supplier s ON j.supplier_id = s.supplier_id GROUP BY s.type")
    fig = px.bar(df_sup, x='supplier_type', y='tickets', color='supplier_type', title="Số lượng vé theo Loại NCC")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Top 10 Nền tảng / Nhà cung cấp")
    df_top = load_data("SELECT s.supplier_id, s.type, COUNT(j.journey_id) as tickets, SUM(j.selling_price) as revenue FROM fact_journey j JOIN dim_supplier s ON j.supplier_id = s.supplier_id GROUP BY s.supplier_id, s.type ORDER BY tickets DESC LIMIT 10")
    st.dataframe(df_top, use_container_width=True)

def show_customers():
    st.header("Hành khách & Khách hàng")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top 10 Khách VIP")
        df_vip = load_data("SELECT name, tier, total_trips, total_spend FROM dim_customer ORDER BY total_trips DESC LIMIT 10")
        st.dataframe(df_vip, use_container_width=True)
    with c2:
        st.subheader("Khách Premium (First/Business)")
        df_prem = load_data("SELECT name, premium_trips, total_spend FROM dim_customer WHERE premium_trips > 0 ORDER BY premium_trips DESC LIMIT 10")
        st.dataframe(df_prem, use_container_width=True)

if __name__ == "__main__":
    main()
