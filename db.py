# db.py
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

DATABASE = 'main.db'

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_highlight_by_id(id):
    """Get highlight by ID"""
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM highlights WHERE id = ?",
            (id,)
        ).fetchone()

def get_highlights_for_review():
    """Get highlights due for review today"""
    with get_db() as conn:
        return conn.execute("SELECT * FROM highlights WHERE review_today = 1").fetchall()

def get_all_highlights(book_filter=None, favorites_only=False, limit=None, shuffle=False):
    """Get all non-deleted highlights with optional filtering"""
    with get_db() as conn:
        query = "SELECT * FROM highlights WHERE deleted = 0"
        params = []  
        if book_filter:
            query += " AND book_title = ?"
            params.append(book_filter)   
        if favorites_only:
            query += " AND favorite = 1"
        
        query += " ORDER BY " + ("RANDOM()" if shuffle else "timestamp DESC")
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        return conn.execute(query, params).fetchall()


def get_all_books():
    """Get list of all books with highlights"""
    with get_db() as conn:
        return conn.execute("""
            SELECT DISTINCT book_title 
            FROM highlights 
            WHERE deleted = 0 
            ORDER BY book_title
        """).fetchall()

def exists_highlight(text):
    """Check if a passage already exists in the database using original_text"""
    with get_db() as conn:
        result = conn.execute("SELECT id FROM highlights WHERE original_text = ? LIMIT 1", (text,)).fetchone()
        return result is not None

def update_highlight(highlight_id, field, value):
    """Update a single field of a highlight"""

    assert field in ['highlight_text', 'note', 'favorite', 'deleted']
    if field in ['favorite', 'deleted']: assert value in [True, False] 
    
    with get_db() as conn:
        conn.execute(
            "UPDATE highlights SET {} = ? WHERE id = ?".format(field),
            (value, highlight_id)
        )
        conn.commit()

def add_highlight(data):
    """Add a new highlight. `data` is dict with column names and values"""

    assert 'highlight_text' in data and len(data['highlight_text']) > 5

    # Check if already exists
    assert not exists_highlight(data['highlight_text']), 'Highlight already exists.'

    # Book title should be the current one (in case it was renamed)
    data['book_title'] = book_current_name(data['book_title'])

    # Deal with 'original' columns
    data['original_book_title'] = data.get('book_title', 'Unknown')
    data['original_text'] = data['highlight_text']

    with get_db() as conn:
        conn.execute("""
            INSERT INTO highlights ({}) VALUES ({})
        """.format(
            ', '.join(data.keys()),
            ', '.join(['?'] * len(data))
        ), list(data.values()))
        conn.commit()

def rename_book(old_book_str, new_book_str):
    """Rename a book title in the database"""
    old_book_str = book_current_name(old_book_str)
    with get_db() as conn:
        conn.execute("""
            UPDATE highlights SET book_title = ? WHERE book_title = ?
        """, (new_book_str, old_book_str))
        conn.commit()

def delete_book(book_str):
    """Delete a book and all its highlights from the database"""
    book_str = book_current_name(book_str)
    print('deleting book')
    print(book_str)
    with get_db() as conn:
        conn.execute("""
            UPDATE highlights SET deleted = 1 WHERE book_title = ?
        """, (book_str,))
        conn.commit()

def book_current_name(book_str):
    """Returns the current book_title of a potentially orginial_book_title"""
    with get_db() as conn:
        # Check if it exists as an original title and return the current one
        result = conn.execute(
            "SELECT book_title FROM highlights WHERE original_book_title = ? LIMIT 1",
            (book_str,)
        ).fetchone()

        return result['book_title'] if result else book_str
        
def get_highlight_stats():
    """Get various statistics about highlights collection"""
    with get_db() as conn:
        stats = {}
        
        # Total counts
        basic_counts = conn.execute("""
        SELECT
            COUNT(*) as total_highlights,
            SUM(CASE WHEN deleted = 0 THEN 1 ELSE 0 END) as active_highlights,
            SUM(CASE WHEN favorite = 1 AND deleted = 0 THEN 1 ELSE 0 END) as favorite_highlights,
            COUNT(DISTINCT book_title) as total_books,
            COUNT(DISTINCT CASE WHEN deleted = 0 THEN book_title ELSE NULL END) as active_books
        FROM highlights
        """).fetchone()
        stats.update(dict(basic_counts))
        
        # Review stats
        review_stats = conn.execute("""
        SELECT
            COUNT(*) as total_reviewed,
            AVG(review_count) as avg_reviews_per_highlight,
            MAX(review_count) as max_reviews
        FROM highlights
        """).fetchone()
        stats.update(dict(review_stats))
        
        # Recently highlighted books (last 5)
        stats['recent_books'] = conn.execute("""
        SELECT
            book_title,
            MAX(author) as author,
            MAX(timestamp) as last_highlight_date
        FROM highlights
        WHERE deleted = 0
        GROUP BY book_title
        ORDER BY last_highlight_date DESC
        LIMIT 5
        """).fetchall()
        
        # Monthly activity
        stats['monthly_activity'] = conn.execute("""
        SELECT
            strftime('%Y-%m', timestamp) as month,
            COUNT(*) as new_highlights
        FROM highlights
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
        """).fetchall()
        
        # Highlight length distribution
        stats['length_distribution'] = conn.execute("""
        SELECT
            CASE
                WHEN LENGTH(highlight_text) < 100 THEN 'Short (<100 chars)'
                WHEN LENGTH(highlight_text) < 300 THEN 'Medium (100-300 chars)'
                ELSE 'Long (>300 chars)'
            END as length_category,
            COUNT(*) as count
        FROM highlights
        WHERE deleted = 0
        GROUP BY length_category
        """).fetchall()
        
        # Color distribution
        stats['color_distribution'] = conn.execute("""
        SELECT color, COUNT(*) as count
        FROM highlights
        WHERE deleted = 0
        GROUP BY color
        ORDER BY count DESC
        """).fetchall()
        
        return stats