#!/usr/bin/env python3

import asyncio
import requests

async def check_current_chrome():
    # Check if Chrome is accessible
    try:
        response = requests.get('http://localhost:9222/json/list')
        if response.status_code == 200:
            pages = response.json()
            print(f'Chrome has {len(pages)} pages:')
            for i, page in enumerate(pages):
                title = page.get('title', 'No title')
                url = page.get('url', 'No URL')
                print(f'  Page {i+1}: {title} - {url}')
        else:
            print('Chrome not accessible')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_current_chrome())
