import os, sqlite3, argparse
from datetime import datetime

import db as db_utils

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Moon Reader notes into highlights database')
    parser.add_argument('--backup-dir', default='com.flyersoft.moonreaderp', help='Path to Moon Reader backup directory (default: com.flyersoft.moonreaderp)')
    args = parser.parse_args()
    
    backup_dir = args.backup_dir
    
    # Find main db (mrbooks.db) file path
    print(f"Looking for Moon Reader database in {backup_dir}...")
    with open(os.path.join(backup_dir, '_names.list'), 'r') as file:
        line_number = next((i+1 for i, line in enumerate(file) if line.endswith('mrbooks.db\n')), None)
    
    if line_number is None:
        print('Error: mrbooks.db not found in _names.list')
        exit(1)
        
    input_db_path = os.path.join(backup_dir, f'{line_number}.tag')
    print(f'Found mrbooks.db at {input_db_path}')
    
    # Get notes from db
    with sqlite3.connect(input_db_path) as db:
        cursor = db.cursor()
        cursor.execute('SELECT _id, book, highlightColor, time, original FROM notes WHERE original != "";')
        notes = cursor.fetchall()
    
    print(f'Found {len(notes)} notes')
    
    if input(f'About to import to {db_utils.DATABASE}. Proceed? (y/n): ') != 'y': exit(1)
    
    books = set()
    added, errors = 0, 0
    
    for (_id, book, highlight_color, time, original) in notes:
        # Convert color integer to hex format
        hex_color = f'#{int(highlight_color) & 0xFFFFFF:06X}'
        
        # Convert timestamp from milliseconds to readable format
        timestamp = datetime.fromtimestamp(time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare data for import
        data = {
            'original_book_title': book,
            'book_title': book,
            'original_text': original,
            'highlight_text': original,
            'color': hex_color,
            'timestamp': timestamp
        }
        
        try:
            # Check if this passage already exists (if function exists)
            if hasattr(db_utils, 'passage_exists') and db_utils.passage_exists(original):
                print(f'Skipping duplicate note from {book}: {original[:20]}...')
                continue
                
            db_utils.add_highlight(data)
            added += 1
            print(f'Added note {_id} from {book}: {original[:20]}...')
            books.add(book)
        except Exception as e:
            print(f'Error adding {_id} from {book} ({e}): {original[:20]}...')
            errors += 1
    
    print("\nImport summary:")
    print(f"Books imported: {len(books)}")
    print(f"Notes added: {added}")
    print(f"Errors: {errors}")