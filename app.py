import streamlit as st
import time
import config
import base64
from pathlib import Path
from Exporter import news_need_update, update_news_async
import asyncio
import models
import re



def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded


def img_to_html(img_path):
    img_html = "<img src='data:image/png;base64,{}' class='img-fluid'>".format(
      img_to_bytes(img_path))
    return img_html

def img_to_data_uri(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return f"url('data:image/png;base64,{encoded}')"


# Function to load and display news in 3 columns
def display_news(news_data, filter_sources=None):
    # Apply source filter
    if filter_sources:
        news_data = [post for post in news_data if post.source in filter_sources]

    # Group news by source
    news_by_source = {}
    for post in news_data:
        if post.source not in news_by_source:
            news_by_source[post.source] = []
        news_by_source[post.source].append(post)

    # Create 3 columns for the news sources
    columns = st.columns(3)  # Create three columns
    col_idx = 0  # To track which column we are in

    # Iterate through each source and display its news in columns
    for source, posts in news_by_source.items():
        latest_news = posts[:1]  # Get the most recent post
        other_news_count = len(posts) - 1

        margin_bottom = "0px" if other_news_count > 0 else "10px"

        # Define the content to be displayed for this source
        headline = latest_news[0].headline
        source = latest_news[0].source
        image_path = f"LOGOS/{source}.png"
        publication_time_ago = latest_news[0].publication_time_ago
        publication_time = latest_news[0].publication_time
        link = latest_news[0].link


        news_content = f"""
        <div style="border: 1px solid #3498db; padding: 16px; margin-bottom: {margin_bottom}; border-radius: 8px; background-color: #ffffff; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);">
            <div style="flex: 1;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="width: {config.source_width.get(source,120)}px; ">{img_to_html(image_path)}</span>
                    <span style="font-size: 12px; color: #7f8c8d;">⏰ {publication_time_ago}, {publication_time}</span>
                </div>
                <a href="{link}" target="_blank" style="text-decoration: none;">
                    <h5 style="color: #3498db; font-size: 16px; font-weight: bold; margin: 0px;">{headline}</h5>
                </a>
            </div>
        </div>
        """

        # Add the content to the appropriate column
        with columns[col_idx]:

            #st.image(image_path, width=config.source_width[source], use_container_width=False)
            #st.markdown(f'''<div style='text-align: center; width: {config.source_width[source]}px; margin-left: auto; margin-right: auto;'>
                    #{img_to_html(image_path)}
                    #</div>''', unsafe_allow_html=True)
            #st.image(image_path, width= config.source_width[source])

            st.markdown(news_content, unsafe_allow_html=True)


            # Toggle Button to show/hide all news for this source
            toggle_key = f"toggle_{source}"
            if toggle_key not in st.session_state:
                st.session_state[toggle_key] = False  # Initially collapsed

            # Show the toggle button inside the same box as the headline, but only if there's more than one news item
            if other_news_count > 0:
                if st.session_state[toggle_key]:
                    # Button to collapse news
                    if st.button(f"Close {other_news_count} News", key=f"close_{source}", use_container_width=True):
                        st.session_state[toggle_key] = False

                    # Show additional news items (compact)
                    symbols = ['&#9716;', '&#9717;', '&#9718;', '&#9719;']
                    news_html = ''.join([f"""
                        <div style="display: flex; gap: 5px; margin-bottom: 2px; font-size: 16px;">
                            <span style="font-size: 18px; color: #3498db; margin-right: 5px; vertical-align: top;">
                                {symbols[posts.index(post) % len(symbols)]}
                            </span>
                            <div style="display: inline; font-size: 16px;">
                            <a href="{post.link}" target="_blank" style="text-decoration: none; color: #3498db; font-weight: bold; font-family: courier;">
                                {post.headline}
                            </a>
                            <span style="font-size: 15px; color: #7f8c8d;"> {post.publication_time_ago}, {post.publication_time}</span>
                            </div>
                        </div>
                    """ for post in posts[1:]])  # Start from the second post

                    # Display the additional news content
                    st.markdown(f"""
                        <div style="border: 1px solid #3498db; padding: 10px 12px; margin: 0px; border-radius: 10px; background-color: #f4f4f4;">
                            {news_html}
                        </div>
                    """, unsafe_allow_html=True)

                else:
                    # Show button to expand news (when the news are collapsed)
                    if st.button(f"{other_news_count} news from {source}", key=f"expand_{source}", use_container_width=True):
                        st.session_state[toggle_key] = True

        # Move to the next column for the next news source
        col_idx += 1
        if col_idx == 3:  # Reset to the first column if we reach the end of the row
            col_idx = 0


def display_news_need_update(news_need_update_dict):

    if not news_need_update_dict:
        st.markdown("""
            <p style="font-size: 20px; text-align: center; color: #2ecc71;">🎉 All sources updated successfully! 🎉</p>
        """, unsafe_allow_html=True)
        return

    else:
        st.markdown(f"""
        <h3 style="color: #fce4e4; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8); text-align: center; margin: 10px 0; font-size: 16px;">
            <span>⚠️</span>
            <span style="display: inline-block; width: 50px;"></span>
            <span>DANGER ZONE</span>
            <span style="display: inline-block; width: 50px;"></span>
            <span>⚠️</span>
        </h3>
        <h4 style="color: #fce4e4; text-align: center; margin: 10px 0;text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);font-size: 14px;">{f'There is 1 source that needs to be updated' if len(news_need_update_dict) == 1 else f'There are {len(news_need_update_dict)} sources that need to be updated'} </h4>
    """, unsafe_allow_html=True)

        for source, exception in news_need_update_dict.items():
            image_path = f"LOGOS/{source}.png"
            st.markdown(f"""
            <div style="display: flex; align-items: center; padding: 10px; border: 1px solid #e74c3c; border-radius: 8px; background-color: #fce4e4; margin-bottom: 10px;">
                <div style="flex: 0 0 auto; margin-right: 10px;">
                    <img src="data:image/png;base64,{img_to_bytes(image_path)}" alt="{source}" style="width: {config.source_width.get(source,120) - 60}px;">
                </div>
                <div style="flex: 1;">
                    <p style="font-size: 14px; color: #7f8c8d; margin: 5px 0;">{exception}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)


# Streamlit app layout
st.set_page_config(page_title="Latest News", layout="wide", initial_sidebar_state="collapsed")  # Set wide layout and collapsed sidebar for more focus

st.sidebar.title("News search")

#back imag
@st.cache_data
def get_img():
    page_element="""
    <style>
    [data-testid="stAppViewContainer"]{
    background-image: url("https://dwg31ai31okv0.cloudfront.net/image-handler/ts/20241013092313/ri/1350/src/images/Article_Images/ImageForArticle_549_17288689857007544.jpg");
    background-size: cover;
    }
    [data-testid="stHeader"]{
    background-color: rgba(0,0,0,0);
    }
    </style>
    """
    return page_element

st.markdown(get_img(), unsafe_allow_html=True)

# Header and tagline (compact)
st.markdown("""
    <h2 style="font-size: 30px; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8); text-align: center; margin: 10px 0;">Breaking News</h2>
    <h4 style="font-size: 18px; color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8); text-align: center; margin: 5px 0;">Stay updated with all the headlines from the last five days. Last updated at 07:40, 04-02-25, again.</h4>
""", unsafe_allow_html=True)

# Use custom font family for the app (compact version)
st.markdown("""
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f7f7f7;
            color: #34495e;
        }
        h2, h4 {
            font-family: 'Arial', sans-serif;
        }

        .news-item:hover {
            transform: scale(1.03);
            transition: all 0.3s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }
    </style>
""", unsafe_allow_html=True)


#initialize sesson state
if 'news_data' not in st.session_state:
    #news_data = asyncio.run(update_news_async())
    #st.session_state.news_data =  news_data # Fetch news data once and store in session_state
    st.session_state.news_data = models.load_news_data()
    if news_need_update:
        st.session_state.news_need_update = news_need_update

if 'last_run' not in st.session_state:
    st.session_state.last_run = time.time()  # Track when the news was last fetched

if 'refresh_flag' not in st.session_state:
    st.session_state.refresh_flag = False  # A flag to track when to refresh

# Sidebar filter for source (multiple selection)
filter_sources = st.sidebar.multiselect("Filter by Source", ["All"] + config.sources, default="All")

# Sidebar filter for keywords (comma-separated)
keywords_input = st.sidebar.text_input("Filter by Keywords", value="", help="Enter keywords separated by commas")
keywords = [keyword.strip().lower() for keyword in keywords_input.split(",") if keyword.strip()]

# Display the filtered news
filtered_sources = filter_sources if filter_sources != ["All"] else None

# Function to filter news by keywords
# def filter_by_keywords(news_data, keywords):
#     if not keywords:
#         return news_data
#     return [post for post in news_data if any(keyword in post.headline.lower() or keyword in post.source.lower() for keyword in keywords)]

def filter_exact_keywords(news_data, keywords):
    if not keywords:
        return news_data  # If no keywords are entered, return all data

    filtered_data = []
    for post in news_data:
        # Check if any of the keywords match exactly in the post's headline or content
        headline = post.headline.lower()
        content = post.content.lower() if hasattr(post, 'content') else ""  # If 'content' attribute exists in Post

        # Create a regex pattern to match whole words (using \b for word boundaries)
        matches = any(re.search(rf'\b{re.escape(keyword)}\b', headline) or re.search(rf'\b{re.escape(keyword)}\b', content) for keyword in keywords)

        if matches:
            filtered_data.append(post)

    return filtered_data


# Apply keyword filtering
filtered_news_data = filter_exact_keywords(st.session_state.news_data, keywords)

# Apply source filtering
if filtered_sources:
    filtered_news_data = [post for post in filtered_news_data if post.source in filtered_sources]

# Display the news
display_news(filtered_news_data)

# # Check if it's time to refresh news (every 5 minutes)
# if time.time() - st.session_state.last_run > 60 * 30:  # 5 minutes
#     st.session_state.refresh_flag = True  # Set the flag to refresh the news

# Add this section below the news display
st.markdown("---")  # Separator for visual clarity

if 'news_need_update' in st.session_state:
# Display the "news_need_update" section
    display_news_need_update(st.session_state.news_need_update)

# Add a button to manually refresh news
if st.button("Refresh News",  key="refresh_news") or st.session_state.refresh_flag:
    print('✅ Time to refresh news')
    st.session_state.news_data = asyncio.run(update_news_async())  # Fetch updated news
    st.session_state.news_need_update = news_need_update
    st.session_state.last_run = time.time()  # Update the last run time
    st.session_state.refresh_flag = False  # Reset the refresh flag
