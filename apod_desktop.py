import os
import sys
import requests
import sqlite3
from datetime import date, datetime
from hashlib import sha256
import image_lib
import apod_api  # Assuming apod_api is the module where the API functions are defined

# Define paths
script_dir = os.path.dirname(os.path.abspath(__file__))
image_cache_dir = os.path.join(script_dir, 'images')
image_cache_db = os.path.join(image_cache_dir, 'image_cache.db')

def main():
    apod_date = get_apod_date()
    init_apod_cache()
    apod_id = add_apod_to_cache(apod_date)
    apod_info = get_apod_info(apod_id)
    if apod_info:
        print(f"Setting desktop background to APOD from {apod_date.isoformat()}...success")
        image_lib.set_desktop_background_image(apod_info['file_path'])
    else:
        print("Failed to retrieve APOD information.")

def get_apod_date():
    """Retrieve APOD date from command line argument or default to today."""
    if len(sys.argv) > 1:
        try:
            apod_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        except ValueError as e:
            print(f"Error: {e}")
            print("Script execution aborted.")
            sys.exit(1)
    else:
        apod_date = date.today()
    
    if apod_date > date.today():
        print("Error: APOD date cannot be in the future.")
        print("Script execution aborted.")
        sys.exit(1)
    
    print(f"APOD date: {apod_date.isoformat()}")
    return apod_date

def init_apod_cache():
    """Initialize the image cache directory and database."""
    if not os.path.exists(image_cache_dir):
        os.makedirs(image_cache_dir)
        print(f"Image cache directory created at {image_cache_dir}.")
    else:
        print("Image cache directory already exists.")
        
    conn = sqlite3.connect(image_cache_db)
    conn.execute('''CREATE TABLE IF NOT EXISTS apod 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     title TEXT, 
                     explanation TEXT, 
                     file_path TEXT, 
                     sha256 TEXT UNIQUE)''')
    conn.close()
    print(f"Image cache DB ready at {image_cache_db}.")

def add_apod_to_cache(apod_date):
    """Fetch APOD information and cache the image if not already cached."""
    print(f"Getting {apod_date.isoformat()} APOD information from NASA...", end="")
    apod_info = apod_api.get_apod_info(apod_date)
    if not apod_info:
        print("failed")
        return 0
    print("success")
    print(f"APOD title: {apod_info['title']}")
    print(f"APOD URL: {apod_info['url']}")
    
    print(f"Downloading image from {apod_info['url']}...", end="")
    image_data = image_lib.download_image(apod_info['url'])
    if not image_data:
        print("failed")
        return 0
    print("success")
    
    image_hash = sha256(image_data).hexdigest()
    print(f"APOD SHA-256: {image_hash}")
    
    if get_apod_id_from_db(image_hash) == 0:
        print("APOD image is not already in cache.")
        file_path = determine_apod_file_path(apod_info['title'], apod_info['url'])
        print(f"APOD file path: {file_path}")
        
        print(f"Saving image file as {file_path}...", end="")
        if image_lib.save_image_file(image_data, file_path):
            print("success")
            return add_apod_to_db(apod_info['title'], apod_info['explanation'], file_path, image_hash)
        else:
            print("failed")
            return 0
    else:
        print("APOD image is already in cache.")
        return get_apod_id_from_db(image_hash)

def get_apod_id_from_db(image_sha256):
    """Retrieve APOD ID from the database using SHA-256 hash."""
    conn = sqlite3.connect(image_cache_db)
    cursor = conn.execute("SELECT id FROM apod WHERE sha256=?", (image_sha256,))
    apod_id = cursor.fetchone()
    conn.close()
    return apod_id[0] if apod_id else 0

def determine_apod_file_path(image_title, image_url):
    """Generate a file path for storing the image based on title and URL."""
    sanitized_title = "".join([c if c.isalnum() else "_" for c in image_title.strip()])
    filename = sanitized_title + os.path.splitext(image_url)[-1]
    return os.path.join(image_cache_dir, filename)

def add_apod_to_db(title, explanation, file_path, sha256):
    """Add APOD information to the database."""
    conn = sqlite3.connect(image_cache_db)
    cursor = conn.execute("INSERT INTO apod (title, explanation, file_path, sha256) VALUES (?, ?, ?, ?)", 
                 (title, explanation, file_path, sha256))
    conn.commit()
    apod_id = cursor.lastrowid
    conn.close()
    print("Adding APOD to image cache DB...success")
    return apod_id

def get_apod_info(apod_id):
    """Retrieve APOD information from the database by ID."""
    conn = sqlite3.connect(image_cache_db)
    cursor = conn.execute("SELECT title, explanation, file_path FROM apod WHERE id=?", (apod_id,))
    apod_info = cursor.fetchone()
    conn.close()
    if apod_info:
        return {'title': apod_info[0], 'explanation': apod_info[1], 'file_path': apod_info[2]}
    else:
        return None

if __name__ == '__main__':
    main()