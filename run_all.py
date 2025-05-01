#!/usr/bin/env python3
"""
Script to launch multiple components of the RTX 5090 Stock Tracker
"""

import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("Starting RTX 5090 Stock Tracker components...")
    
    # Start Flask app in a separate process
    flask_cmd = [sys.executable, "app.py", "--flask"]
    flask_process = subprocess.Popen(flask_cmd)
    print("Flask app started (PID: {})".format(flask_process.pid))
    
    # Give Flask a moment to start
    time.sleep(2)
    
    # Start Dash app in a separate process
    dash_cmd = [sys.executable, "app.py", "--dash"]
    dash_process = subprocess.Popen(dash_cmd)
    print("Dash app started (PID: {})".format(dash_process.pid))
    
    # Start monitoring in a separate process
    monitor_cmd = [sys.executable, "app.py", "--monitor"]
    monitor_process = subprocess.Popen(monitor_cmd)
    print("Monitoring service started (PID: {})".format(monitor_process.pid))
    
    print("\nAll components started successfully!")
    print("- Flask app is running at: http://localhost:5003/")
    print("- Dash app is running at: http://localhost:8050/dashboard/")
    print("\nPress Ctrl+C to shut down all components.")
    
    try:
        # Keep the script running to maintain the processes
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Gracefully terminate all processes when Ctrl+C is pressed
        print("\nShutting down components...")
        flask_process.terminate()
        dash_process.terminate()
        monitor_process.terminate()
        print("All components have been stopped.")

if __name__ == "__main__":
    main()
