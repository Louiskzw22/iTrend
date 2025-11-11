"""Streamlit UI for browsing iTrend articles and transcripts."""
import os
import sys
import streamlit as st
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.db import TrendDB


# Page configuration
st.set_page_config(
    page_title="iTrend - Emerging Trends Tracker",
    page_icon="📊",
    layout="wide"
)


@st.cache_resource
def get_database():
    """Get cached database connection."""
    db_path = os.environ.get('DB_PATH', 'data/trends.db')
    return TrendDB(db_path)


def main():
    """Main Streamlit application."""
    st.title("📊 iTrend - Emerging Trends Tracker")
    st.markdown("Browse and search articles, podcasts, and transcripts")
    
    # Initialize database
    db = get_database()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Get all tags
    all_tags = db.get_all_tags()
    
    # Tag filter
    selected_tag = st.sidebar.selectbox(
        "Filter by Tag",
        options=["All"] + all_tags,
        index=0
    )
    
    # Search box
    st.sidebar.header("Search")
    search_query = st.sidebar.text_input(
        "Full-text search",
        placeholder="Search articles, descriptions, transcripts..."
    )
    
    # Results limit
    limit = st.sidebar.slider("Number of results", 10, 200, 50)
    
    # Main content area
    if search_query:
        st.subheader(f"🔍 Search Results for: {search_query}")
        articles = db.search_articles(search_query, limit=limit)
    else:
        tag_filter = None if selected_tag == "All" else selected_tag
        if tag_filter:
            st.subheader(f"📑 Articles tagged: {tag_filter}")
        else:
            st.subheader("📑 Recent Articles")
        articles = db.get_articles(tag=tag_filter, limit=limit)
    
    # Display results count
    st.markdown(f"*Found {len(articles)} article(s)*")
    
    # Display articles
    if not articles:
        st.info("No articles found. Run the ingestion script to populate the database.")
    else:
        for idx, article in enumerate(articles, 1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Title and link
                    title = article.get('title', 'Untitled')
                    url = article.get('url', '#')
                    st.markdown(f"### {idx}. [{title}]({url})")
                
                with col2:
                    # Metadata
                    source = article.get('source', 'Unknown')
                    published = article.get('published_date', 'Unknown date')
                    st.caption(f"**Source:** {source}")
                    st.caption(f"**Date:** {published}")
                
                # Tags
                tags = article.get('tags', '')
                if tags:
                    tag_list = [t.strip() for t in tags.split(',')]
                    tag_badges = ' '.join([f"`{tag}`" for tag in tag_list])
                    st.markdown(f"**Tags:** {tag_badges}")
                
                # Description
                description = article.get('description', '')
                if description:
                    with st.expander("📄 Description", expanded=False):
                        st.write(description)
                
                # Transcript
                transcript = article.get('transcript', '')
                if transcript:
                    with st.expander("🎙️ Transcript", expanded=False):
                        st.markdown(transcript)
                else:
                    st.caption("*No transcript available*")
                
                st.divider()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "iTrend tracks emerging trends from podcasts and articles. "
        "Use the search and filters to explore content."
    )


if __name__ == "__main__":
    main()
