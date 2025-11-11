"""Database module for iTrend - manages SQLite database with FTS support."""
import sqlite3
import os
from typing import Optional, List, Dict, Any


class TrendDB:
    """SQLite database manager for trends and articles with full-text search."""
    
    def __init__(self, db_path: str = "data/trends.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # check_same_thread=False allows Streamlit to use the connection
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema with FTS support."""
        cursor = self.conn.cursor()
        
        # Create articles table with transcript column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                description TEXT,
                published_date TEXT,
                source TEXT,
                tags TEXT,
                transcript TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create FTS virtual table including transcript
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title,
                description,
                transcript,
                content=articles,
                content_rowid=id
            )
        """)
        
        # Create triggers to keep FTS index in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, description, transcript)
                VALUES (new.id, new.title, new.description, new.transcript);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                DELETE FROM articles_fts WHERE rowid = old.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                UPDATE articles_fts 
                SET title = new.title,
                    description = new.description,
                    transcript = new.transcript
                WHERE rowid = new.id;
            END
        """)
        
        self.conn.commit()
    
    def upsert_article(self, title: str, url: str, description: Optional[str] = None,
                      published_date: Optional[str] = None, source: Optional[str] = None,
                      tags: Optional[str] = None, transcript: Optional[str] = None,
                      metadata: Optional[str] = None) -> int:
        """Insert or update an article.
        
        If an article with the same URL exists:
        - Update transcript if newly provided (not None)
        - Update other fields if provided
        
        Args:
            title: Article title
            url: Article URL (unique identifier)
            description: Article description
            published_date: Publication date
            source: Source name
            tags: Comma-separated tags
            transcript: Audio transcript text
            metadata: JSON metadata string
            
        Returns:
            Article ID
        """
        cursor = self.conn.cursor()
        
        # Check if article exists
        cursor.execute("SELECT id, transcript FROM articles WHERE url = ?", (url,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing article
            article_id = existing['id']
            existing_transcript = existing['transcript']
            
            # Build update query dynamically based on provided fields
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if published_date is not None:
                updates.append("published_date = ?")
                params.append(published_date)
            if source is not None:
                updates.append("source = ?")
                params.append(source)
            if tags is not None:
                updates.append("tags = ?")
                params.append(tags)
            # Update transcript if newly provided
            if transcript is not None:
                updates.append("transcript = ?")
                params.append(transcript)
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(metadata)
            
            if updates:
                params.append(article_id)
                query = f"UPDATE articles SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                self.conn.commit()
        else:
            # Insert new article
            cursor.execute("""
                INSERT INTO articles (title, url, description, published_date, source, tags, transcript, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, url, description, published_date, source, tags, transcript, metadata))
            article_id = cursor.lastrowid
            self.conn.commit()
        
        return article_id
    
    def search_articles(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search articles.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching articles
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.* 
            FROM articles a
            JOIN articles_fts fts ON a.id = fts.rowid
            WHERE articles_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_articles(self, tag: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get articles, optionally filtered by tag.
        
        Args:
            tag: Filter by tag (optional)
            limit: Maximum number of results
            
        Returns:
            List of articles
        """
        cursor = self.conn.cursor()
        
        if tag:
            cursor.execute("""
                SELECT * FROM articles 
                WHERE tags LIKE ?
                ORDER BY published_date DESC
                LIMIT ?
            """, (f'%{tag}%', limit))
        else:
            cursor.execute("""
                SELECT * FROM articles 
                ORDER BY published_date DESC
                LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags from articles.
        
        Returns:
            List of unique tags
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL")
        
        all_tags = set()
        for row in cursor.fetchall():
            if row['tags']:
                tags = [t.strip() for t in row['tags'].split(',')]
                all_tags.update(tags)
        
        return sorted(list(all_tags))
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
