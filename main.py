import os, requests, zipfile, sqlite3, argparse

def webDAV_download(webdav_url, username, password, local_filename = None):
    '''
    Downloads a file from a WebDAV server given file URL, credentials, and local filename.
    '''
    response = requests.get(webdav_url, auth = (username, password), stream = True)
    response.raise_for_status()  # Raise an error for bad status codes

    if local_filename is None: local_filename = webdav_url.split('/')[-1]
    with open(local_filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size = 8192):
            file.write(chunk)

def is_in_note(s, note, _id, time):
    return s in note or f'{_id}-{time}' in note

def keep_highlight(s, highlightColor):
    return 20 < len(s) < 700

if __name__ == '__main__':

    # Parse command line arguments
    parser = argparse.ArgumentParser(description = 'Extract notes from Moon+ Reader backup.')
    parser.add_argument('--webdav_url', type = str, help = 'WebDAV URL of Moon+ Reader backup.')
    parser.add_argument('--username', type = str, help = 'WebDAV username.')
    parser.add_argument('--password', type = str, help = 'WebDAV password.')
    parser.add_argument('--note_path', type = str, help = 'WebDAV password.')
    args = parser.parse_args()

    # Download backup zip file
    local_filename = args.webdav_url.split('/')[-1]
    webDAV_download(args.webdav_url, args.username, args.password, local_filename)
    print(args)
    print(f'Downloaded {args.webdav_url}')

    # Unzip file and delete ZIP file
    with zipfile.ZipFile(local_filename, 'r') as zip_ref:
        zip_ref.extractall()
        backup_dir = zip_ref.namelist()[0].split('/')[0]
    os.remove(local_filename)
    print(f'Unzipped {backup_dir}')

    # Find main db (mrbooks.db) file path
    with open(os.path.join(backup_dir, '_names.list'), 'r') as file:
        line_number = next((i+1 for i, line in enumerate(file) if line.endswith('mrbooks.db\n')), None)
        if line_number is None: 
            print('Error: mrbooks.db not found in _names.list')
            exit(1)
    
    db_path = os.path.join(backup_dir, f'{line_number}.tag')
    print(f'Found mrbooks.db at {db_path}')

    # Get notes from db
    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute('SELECT _id, book, highlightColor, time, original FROM notes WHERE original != "";')
        notes = cursor.fetchall()
        print(f'Found {len(notes)} notes')

    # Get previous note content
    if os.path.exists(args.note_path):
        with open(args.note_path, 'r') as f: prev_content = f.read()[:]
    else:
        with open(args.note_path, 'w+') as f: f.write('')
        prev_content = ''

    # Add new notes
    first = True
    with open(args.note_path, 'a') as f:
        for (_id, book, highlightColor, time, original) in notes:
            if not keep_highlight(original, highlightColor) or is_in_note(original, prev_content, _id, time):
                continue
            if first:
                first = False
                f.write('#flashcards\n')
            f.write(f'%% {_id}-{time} %%\n{original}\n?\n*{book}*\n+++\n')
            print(f'Added note {_id} from {book}: {original}')