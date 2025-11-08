import streamlit as st
from datetime import datetime
from utils.helpers import (
    retrieve_and_plot_shop_analysis,
    retrieve_and_plot_shop_cleaning,
    retrieve_and_plot_shop_robots_general,
)


def render():
    st.title("📈 Analytics")
    
    # Access the selected shop_id from session state
    selected_shop_id = st.session_state.get('selected_shop_id', None)
    
    # Display current shop selection
    if selected_shop_id:
        st.info(f"📍 Currently viewing data for Shop ID: **{selected_shop_id}**")
        
        # Date range selection
        today = datetime.today().date()
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime(2025, 10, 1),
                max_value=today,  # Cannot select future dates
                key="analytics_start_date"
            )
        with col2:
            end_date = st.date_input(
                "End Date", 
                value=datetime(2025, 10, 31),
                max_value=today,  # Cannot select future dates
                key="analytics_end_date"
            )
        
        st.markdown("---")
        
        # Validate date range
        if start_date > end_date:
            st.error("⚠️ Start date cannot be after end date. Please adjust your selection.")
            return
        
        # Convert dates to datetime
        start_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.max.time())
        
        # Display analytics using the selected shop_id
        try:
            st.subheader("📊 Shop Activity Analysis")
            retrieve_and_plot_shop_analysis(
                start_time=start_time,
                end_time=end_time,
                shop_id=selected_shop_id  # Use the selected shop_id here!
            )
            
            st.subheader("🧹 Cleaning Performance")
            retrieve_and_plot_shop_cleaning(
                start_time=start_time,
                end_time=end_time,
                shop_id=selected_shop_id  # Use the selected shop_id here!
            )
            
            st.subheader("🤖 Robot Statistics")
            retrieve_and_plot_shop_robots_general(
                start_time=start_time,
                end_time=end_time,
                shop_id=selected_shop_id  # Use the selected shop_id here!
            )
            
        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")
            st.info("Please check your API connection and try again.")
        
    else:
        st.warning("⚠️ No shop selected. Please select a shop from the sidebar.")
        st.info("Once you select a shop, analytics data will appear here.")