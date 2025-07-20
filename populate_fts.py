import db

with db.get_db() as conn:
    conn.execute("""
        INSERT INTO highlights_fts(rowid, highlight_text, note)
        SELECT id, highlight_text, note FROM highlights;
    """)
    conn.commit()
