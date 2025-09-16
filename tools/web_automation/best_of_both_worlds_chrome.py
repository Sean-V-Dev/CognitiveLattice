#!/usr/bin/env python3
"""
Enhanced Chrome startup with persistent profile AND working bot detection bypass.
This combines the benefits of persistent data with the security flags that work.
"""

import subprocess
import os
import time
from pathlib import Path

def start_chrome_with_persistent_profile_and_working_flags():
    """
    Start Chrome with:
    1. Persistent profile (saves history, cookies, etc.)
    2. ALL the working bot detection bypass flags
    """
    
    # Use persistent profile directory (not temp)
    profile_dir = Path.home() / "AppData/Local/CognitiveLattice/chrome_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    chrome_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
        "chrome.exe"
    ]
    
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break
    
    if chrome_exe is None:
        print("❌ Chrome executable not found")
        return False
    
    # COMBINE: Persistent profile + ALL working security flags
    chrome_args = [
        chrome_exe,
        f"--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",  # ✅ Persistent profile
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-backgrounding-occluded-windows",  # ✅ Working flag
        "--disable-renderer-backgrounding",          # ✅ Working flag
        "--disable-features=TranslateUI",            # ✅ Working flag
        "--disable-background-timer-throttling",     # ✅ Working flag
        "--disable-web-security",                    # ✅ Working flag
        "--disable-features=VizDisplayCompositor",   # ✅ Working flag
        "--disable-blink-features=AutomationControlled",  # ✅ Working flag
        "--start-maximized"
    ]
    
    print("🎯 BEST OF BOTH WORLDS CHROME SETUP")
    print("=" * 50)
    print(f"✅ Persistent profile: {profile_dir}")
    print("✅ ALL working bot detection bypass flags")
    print("✅ History, cookies, and preferences will be saved")
    print("✅ Chipotle compatibility maintained")
    
    try:
        process = subprocess.Popen(chrome_args, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        if process.poll() is None:
            print(f"🎉 Chrome started successfully with PID {process.pid}")
            print(f"🌐 Debug port: http://localhost:9222")
            return True
        else:
            print(f"❌ Chrome failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Error starting Chrome: {e}")
        return False

if __name__ == "__main__":
    success = start_chrome_with_persistent_profile_and_working_flags()
    if success:
        print("\n💡 This setup should:")
        print("  ✅ Save browsing history permanently")
        print("  ✅ Bypass Chipotle bot detection") 
        print("  ✅ Allow account creation and ordering")
        print("  ✅ Maintain all cookies and preferences")
        
        try:
            input("\nPress Enter to continue...")
        except KeyboardInterrupt:
            print("\n👋 Chrome is still running. Close manually when done.")
    else:
        print("\n❌ Setup failed")
