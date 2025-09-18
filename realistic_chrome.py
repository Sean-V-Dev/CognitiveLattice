#!/usr/bin/env python3
"""
Enhanced Chrome manager that mimics real user scenarios as closely as possible.
Priority order:
1. Connect to existing user's Chrome (most realistic)
2. Start Chrome with user's default profile 
3. Fallback to our custom profile
"""

import subprocess
import os
import time
import json
import requests
from pathlib import Path

def find_existing_chrome_debug_port():
    """Check if Chrome is already running with debug port"""
    try:
        response = requests.get("http://localhost:9222/json/version", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def get_user_chrome_profile_path():
    """Get the user's default Chrome profile path"""
    profile_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        os.path.expandvars(r"%APPDATA%\Google\Chrome\User Data"),
    ]
    
    for path in profile_paths:
        if os.path.exists(path):
            return path
    return None

def start_chrome_with_user_profile():
    """Start Chrome with user's default profile + debugging"""
    user_profile = get_user_chrome_profile_path()
    if not user_profile:
        print("⚠️  Could not find user's Chrome profile, using custom profile")
        return start_chrome_with_custom_profile()
    
    print(f"🔗 Starting Chrome with user's default profile: {user_profile}")
    
    chrome_args = [
        "chrome.exe",
        f"--user-data-dir={user_profile}",
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--disable-default-apps"
    ]
    
    try:
        subprocess.Popen(chrome_args, shell=True)
        time.sleep(3)
        print("✅ Chrome started with user's default profile")
        return True
    except Exception as e:
        print(f"❌ Failed to start Chrome with user profile: {e}")
        return start_chrome_with_custom_profile()

def start_chrome_with_custom_profile():
    """Fallback: Start Chrome with our custom profile"""
    profile_dir = Path.home() / "AppData/Local/CognitiveLattice/chrome_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔗 Starting Chrome with custom profile: {profile_dir}")
    
    chrome_args = [
        "chrome.exe",
        f"--user-data-dir={profile_dir}",
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--disable-default-apps"
    ]
    
    try:
        subprocess.Popen(chrome_args, shell=True)
        time.sleep(3)
        print("✅ Chrome started with custom profile")
        return True
    except Exception as e:
        print(f"❌ Failed to start Chrome: {e}")
        return False

def get_realistic_chrome_connection():
    """
    Get Chrome connection in most realistic way possible:
    1. Try existing Chrome instance
    2. Start with user's profile  
    3. Fallback to custom profile
    """
    
    print("🎯 CONNECTING TO CHROME (Production-like mode)")
    print("=" * 50)
    
    # Method 1: Check for existing Chrome with debug port
    if find_existing_chrome_debug_port():
        print("✅ Found existing Chrome with debug port - MOST REALISTIC!")
        return True
    
    # Method 2: Try to start Chrome with user's default profile
    print("🔄 No existing debug Chrome found, starting new instance...")
    if start_chrome_with_user_profile():
        return True
    
    # Method 3: Fallback to custom profile
    print("🔄 Fallback to custom profile...")
    return start_chrome_with_custom_profile()

def analyze_chrome_realism():
    """Analyze how realistic our Chrome setup is"""
    try:
        response = requests.get("http://localhost:9222/json/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"\n🔍 CHROME REALISM ANALYSIS:")
            print("=" * 40)
            print(f"✅ Browser: {version_info.get('Browser', 'Unknown')}")
            print(f"✅ User-Agent: {version_info.get('User-Agent', 'Unknown')}")
            print(f"✅ WebKit Version: {version_info.get('WebKit-Version', 'Unknown')}")
            
            # Check for debugging footprints
            ua = version_info.get('User-Agent', '')
            if 'HeadlessChrome' in ua:
                print("⚠️  WARNING: Headless Chrome detected!")
            else:
                print("✅ Normal Chrome (not headless)")
            
            return True
    except Exception as e:
        print(f"❌ Could not analyze Chrome: {e}")
        return False

if __name__ == "__main__":
    success = get_realistic_chrome_connection()
    if success:
        analyze_chrome_realism()
        print("\n🎉 Chrome is ready for realistic automation!")
    else:
        print("\n❌ Failed to establish Chrome connection")
