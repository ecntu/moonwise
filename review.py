import os
from datetime import datetime
from db import get_db, DEFAULT_QUOTE_BOOK_TITLE

if __name__ == "__main__":
    N_REVIEW_PASSAGES = int(os.environ.get("N_REVIEW_PASSAGES", 5))
    N_FAVORITES_IN_REVIEW = int(os.environ.get("N_FAVORITES_IN_REVIEW", 1))

    print(f"[{datetime.now()}] Running daily review update...")

    """Select highlights for review, prioritizing less-reviewed and older ones."""
    with get_db() as conn:
        # Reset all review_today flags
        conn.execute("""UPDATE highlights SET review_today = 0""")
        conn.commit()

        # Always pull one quote if available
        quote_row = conn.execute(
            """
            SELECT id FROM highlights
            WHERE deleted = 0 AND book_title = ?
            ORDER BY review_count ASC, last_review ASC, RANDOM()
            LIMIT 1
            """,
            (DEFAULT_QUOTE_BOOK_TITLE,),
        ).fetchone()

        selected_quote = False
        if quote_row:
            selected_quote = True
            conn.execute(
                """
                UPDATE highlights
                SET review_today = 1, review_count = review_count + 1, last_review = date('now')
                WHERE id = ?
                """,
                (quote_row["id"],),
            )
            conn.commit()

        remaining_slots = max(N_REVIEW_PASSAGES - (1 if selected_quote else 0), 0)
        favorite_limit = min(N_FAVORITES_IN_REVIEW, remaining_slots)
        general_limit = max(remaining_slots - favorite_limit, 0)

        # Select favorite highlights for review
        if favorite_limit:
            conn.execute(
                """
                UPDATE highlights
                SET review_today = 1, review_count = review_count + 1, last_review = date('now')
                WHERE id IN (
                    SELECT id FROM highlights
                    WHERE deleted = 0 AND favorite = 1 AND review_today = 0 AND book_title != ?
                    ORDER BY review_count ASC, last_review ASC, RANDOM()
                    LIMIT ?
                )
            """,
                (DEFAULT_QUOTE_BOOK_TITLE, favorite_limit),
            )
            conn.commit()

        # Select general highlights for review
        if general_limit:
            conn.execute(
                """
                UPDATE highlights
                SET review_today = 1, review_count = review_count + 1, last_review = date('now')
                WHERE id IN (
                    SELECT id FROM highlights
                    WHERE deleted = 0 AND review_today = 0 AND book_title != ?
                    ORDER BY review_count ASC, last_review ASC, RANDOM()
                    LIMIT ?
                )
            """,
                (DEFAULT_QUOTE_BOOK_TITLE, general_limit),
            )
            conn.commit()

    print(f"[{datetime.now()}] Review schedule updated.")
