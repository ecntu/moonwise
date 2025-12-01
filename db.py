# db.py
import sqlite3
from contextlib import contextmanager

DATABASE = "main.db"
DEFAULT_QUOTE_BOOK_TITLE = "Quotes"


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
        return conn.execute("SELECT * FROM highlights WHERE id = ?", (id,)).fetchone()


def get_highlights_for_review():
    """Get highlights due for review today"""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM highlights
            WHERE review_today = 1
            ORDER BY CASE WHEN book_title = ? THEN 0 ELSE 1 END,
                     review_count ASC,
                     last_review ASC,
                     timestamp DESC
            """,
            (DEFAULT_QUOTE_BOOK_TITLE,),
        ).fetchall()


def get_all_highlights(
    book_filter=None, favorites_only=False, limit=None, shuffle=False, search_query=None
):
    """Get all non-deleted highlights with optional filtering and search"""
    if search_query:
        return search_highlights(
            search_query, book_filter, favorites_only, limit, shuffle
        )

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


def search_highlights(
    search_query, book_filter=None, favorites_only=False, limit=None, shuffle=False
):
    """Search highlights using FTS"""
    with get_db() as conn:
        query = """
            SELECT h.* FROM highlights h
            JOIN highlights_fts fts ON h.id = fts.rowid
            WHERE highlights_fts MATCH ? AND h.deleted = 0
        """
        params = [search_query]

        if book_filter:
            query += " AND h.book_title = ?"
            params.append(book_filter)
        if favorites_only:
            query += " AND h.favorite = 1"

        query += " ORDER BY " + ("RANDOM()" if shuffle else "fts.rank")
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
    """Check if a passage already exists in the database (non-deleted) using original_text"""
    with get_db() as conn:
        result = conn.execute(
            "SELECT id FROM highlights WHERE original_text = ? AND deleted = 0 LIMIT 1",
            (text,),
        ).fetchone()
        return result is not None


def find_highlight_by_text(text):
    """Return highlight (even if deleted) matching original_text"""
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM highlights WHERE original_text = ? LIMIT 1", (text,)
        ).fetchone()


def update_highlight(highlight_id, field, value):
    """Update a single field of a highlight"""

    assert field in ["highlight_text", "note", "favorite", "deleted"]
    if field in ["favorite", "deleted"]:
        assert value in [True, False]

    with get_db() as conn:
        conn.execute(
            "UPDATE highlights SET {} = ? WHERE id = ?".format(field),
            (value, highlight_id),
        )
        conn.commit()


def add_highlight(data):
    """Add a new highlight. `data` is dict with column names and values"""

    assert "highlight_text" in data and len(data["highlight_text"]) > 5

    highlight_text = data["highlight_text"]
    book_title = (data.get("book_title") or "").strip() or "Unknown"

    # Book title should be the current one (in case it was renamed)
    current_book_title = book_current_name(book_title)

    existing_highlight = find_highlight_by_text(highlight_text)
    if existing_highlight:
        if existing_highlight["deleted"]:
            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE highlights
                    SET deleted = 0,
                        book_title = ?,
                        author = ?,
                        note = ?,
                        favorite = ?,
                        highlight_text = ?,
                        original_text = ?,
                        timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        current_book_title,
                        data.get("author"),
                        data.get("note"),
                        bool(data.get("favorite")),
                        highlight_text,
                        highlight_text,
                        existing_highlight["id"],
                    ),
                )
                conn.commit()
            return

        # Already exists and active
        raise AssertionError("Highlight already exists.")

    # Deal with 'original' columns
    data["book_title"] = current_book_title
    data["original_book_title"] = data.get("original_book_title") or data["book_title"]
    data["original_text"] = highlight_text

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO highlights ({}) VALUES ({})
        """.format(", ".join(data.keys()), ", ".join(["?"] * len(data))),
            list(data.values()),
        )
        conn.commit()


def rename_book(old_book_str, new_book_str):
    """Rename a book title in the database"""
    old_book_str = book_current_name(old_book_str)
    with get_db() as conn:
        conn.execute(
            """
            UPDATE highlights SET book_title = ? WHERE book_title = ?
        """,
            (new_book_str, old_book_str),
        )
        conn.commit()


def update_book_author(book_str, new_author):
    """Update the author for all highlights in the given book"""
    book_str = book_current_name(book_str)
    with get_db() as conn:
        conn.execute(
            """
            UPDATE highlights SET author = ? WHERE book_title = ?
        """,
            (new_author, book_str),
        )
        conn.commit()


def delete_book(book_str):
    """Delete a book and all its highlights from the database"""
    book_str = book_current_name(book_str)
    print("deleting book")
    print(book_str)
    with get_db() as conn:
        conn.execute(
            """
            UPDATE highlights SET deleted = 1 WHERE book_title = ?
        """,
            (book_str,),
        )
        conn.commit()


def book_current_name(book_str):
    """Returns the current book_title of a potentially orginial_book_title"""
    with get_db() as conn:
        # Check if it exists as an original title and return the current one
        result = conn.execute(
            "SELECT book_title FROM highlights WHERE original_book_title = ? LIMIT 1",
            (book_str,),
        ).fetchone()

        return result["book_title"] if result else book_str


def get_highlight_stats(n_recent_books=5, n_recent_books_detailed=50, n_top_books=10):
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
        stats["recent_books"] = conn.execute(f"""
        SELECT
            book_title,
            MAX(author) as author,
            MAX(timestamp) as last_highlight_date
        FROM highlights
        WHERE deleted = 0
        GROUP BY book_title
        ORDER BY last_highlight_date DESC
        LIMIT {n_recent_books}
        """).fetchall()

        # Detailed recent books for recommender export
        stats["recent_books_detailed"] = conn.execute(
            """
        SELECT
            book_title,
            MAX(author) as author,
            COUNT(*) as total_highlights,
            SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END) as favorite_highlights,
            MAX(timestamp) as last_highlight_date
        FROM highlights
        WHERE deleted = 0
        GROUP BY book_title
        ORDER BY last_highlight_date DESC
        LIMIT ?
        """,
            (n_recent_books_detailed,),
        ).fetchall()

        # Top books by highlight volume
        stats["top_books_by_highlights"] = conn.execute(
            """
        SELECT
            book_title,
            MAX(author) as author,
            COUNT(*) as total_highlights,
            SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END) as favorite_highlights,
            MAX(timestamp) as last_highlight_date
        FROM highlights
        WHERE deleted = 0
        GROUP BY book_title
        ORDER BY total_highlights DESC, last_highlight_date DESC
        LIMIT ?
        """,
            (n_top_books,),
        ).fetchall()

        # Top books by favorite highlights
        stats["top_books_by_favorites"] = conn.execute(
            """
        SELECT
            book_title,
            MAX(author) as author,
            COUNT(*) as total_highlights,
            SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END) as favorite_highlights,
            MAX(timestamp) as last_highlight_date
        FROM highlights
        WHERE deleted = 0
        GROUP BY book_title
        ORDER BY favorite_highlights DESC, total_highlights DESC, last_highlight_date DESC
        LIMIT ?
        """,
            (n_top_books,),
        ).fetchall()

        # Monthly activity
        stats["monthly_activity"] = conn.execute("""
        SELECT
            strftime('%Y-%m', timestamp) as month,
            COUNT(*) as new_highlights
        FROM highlights
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
        """).fetchall()
        return stats
