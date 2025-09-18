#!/usr/bin/env python3

import sqlite3
import os
from datetime import datetime

def chrome_timestamp_to_datetime(timestamp):
    """Convert Chrome timestamp to human readable datetime"""
    if timestamp == 0:
        return 'Never'
    # Chrome epoch is Jan 1, 1601, Unix epoch is Jan 1, 1970
    # 11644473600 seconds between them
    epoch_start = datetime(1970, 1, 1)
    delta = timestamp / 1000000 - 11644473600
    return datetime.fromtimestamp(delta).strftime('%Y-%m-%d %H:%M:%S')

def check_chrome_history():
    history_path = r'C:\Users\seanv\AppData\Local\CognitiveLattice\chrome_profile\Default\History'
    
    if not os.path.exists(history_path):
        print("❌ History file not found at:", history_path)
        return
    
    print(f"✅ History file found: {os.path.getsize(history_path)} bytes")
    
    try:
        # Use read-only mode to avoid locking issues
        conn = sqlite3.connect(f"file:{history_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Get total URL count
        cursor.execute('SELECT COUNT(*) FROM urls')
        total_urls = cursor.fetchone()[0]
        print(f"📊 Total URLs in history: {total_urls}")
        
        if total_urls > 0:
            # Get recent URLs
            cursor.execute('''
                SELECT url, title, last_visit_time, visit_count 
                FROM urls 
                ORDER BY last_visit_time DESC 
                LIMIT 10
            ''')
            results = cursor.fetchall()
            
            print('\n🕒 RECENT BROWSING HISTORY:')
            print('=' * 80)
            for url, title, last_visit, count in results:
                time_str = chrome_timestamp_to_datetime(last_visit)
                title_short = (title[:60] + '...') if title and len(title) > 60 else (title or 'No title')
                print(f'{time_str} - Visits: {count}')
                print(f'   {title_short}')
                print(f'   {url}')
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error reading history: {e}")

if __name__ == "__main__":
    check_chrome_history()
