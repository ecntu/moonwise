import os
from datetime import datetime
from db import get_db

if __name__ == '__main__':

    N_REVIEW_PASSAGES = int(os.environ.get('N_REVIEW_PASSAGES', 5))
    N_FAVORITES_IN_REVIEW = int(os.environ.get('N_FAVORITES_IN_REVIEW', 1))

    print(f'[{datetime.now()}] Running daily review update...')

    '''Select highlights for review, prioritizing less-reviewed and older ones.'''
    with get_db() as conn:
        # Reset all review_today flags
        conn.execute('''UPDATE highlights SET review_today = 0''')
        conn.commit()

        # Select favorite highlights for review
        conn.execute('''
            UPDATE highlights
            SET review_today = 1, review_count = review_count + 1, last_review = date('now')
            WHERE id IN (
                SELECT id FROM highlights
                WHERE deleted = 0 AND favorite = 1
                ORDER BY review_count ASC, last_review ASC, RANDOM()
                LIMIT ?
            )
        ''', (N_FAVORITES_IN_REVIEW,))
        conn.commit()

        # Select general highlights for review
        conn.execute('''
            UPDATE highlights
            SET review_today = 1, review_count = review_count + 1, last_review = date('now')
            WHERE id IN (
                SELECT id FROM highlights
                WHERE deleted = 0 AND review_today = 0
                ORDER BY review_count ASC, last_review ASC, RANDOM()
                LIMIT ?
            )
        ''', (N_REVIEW_PASSAGES - N_FAVORITES_IN_REVIEW,))
        conn.commit()
    
    print(f'[{datetime.now()}] Review schedule updated.')