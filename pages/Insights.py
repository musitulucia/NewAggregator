#back imag
import streamlit as st
import app
import asyncio
import Exporter
from Exporter import insight_need_update
import time
import models



st.markdown("""
    <h2 style="font-size: 30px; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8); text-align: center; margin: 10px 0;">Industry Insights</h2>
""", unsafe_allow_html=True)


st.markdown(app.get_img(), unsafe_allow_html=True)

if 'insight_data' not in st.session_state:
    st.session_state.insight_data =  models.load_news_data(news = False) # Fetch news data once and store in session_state
    if insight_need_update:
        st.session_state.insight_need_update = insight_need_update

if 'last_run_in' not in st.session_state:
    st.session_state.last_run_in = time.time()  # Track when the news was last fetched

if 'refresh_flag_in' not in st.session_state:
    st.session_state.refresh_flag_in = False  # A flag to track when to refresh

# Display the news
app.display_news(st.session_state.insight_data)

# # Check if it's time to refresh news (every 5 minutes)
# if time.time() - st.session_state.last_run_in > 60 * 30:  # 5 minutes
#     st.session_state.refresh_flag_in = True  # Set the flag to refresh the news

# Add this section below the news display
st.markdown("---")  # Separator for visual clarity

if 'insight_need_update' in st.session_state:
# Display the "news_need_update" section
    app.display_news_need_update(st.session_state.insight_need_update)

# # Add a button to manually refresh news
# if st.button("Refresh Insights",  key="refresh_insights") or st.session_state.refresh_flag_in:
#     print('✅ Time to refresh insights')
#     st.session_state.insight_data = asyncio.run(Exporter.update_insights_async())  # Fetch updated news
#     st.session_state.insight_need_update = insight_need_update
#     st.session_state.last_run_in = time.time()  # Update the last run time
#     st.session_state.refresh_flag_in = False  # Reset the refresh flag
