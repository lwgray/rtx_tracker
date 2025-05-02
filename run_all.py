#!/usr/bin/env python3
"""
Script to launch multiple components of the RTX 5090 Stock Tracker
"""

import os
import sys
import subprocess
import time
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Store processes globally so signal handlers can access them
processes = []

def signal_handler(sig, frame):
    """Handle termination signals to gracefully shut down all processes"""
    print("\nShutting down components...")
    
    # Terminate each process and wait for it to complete
    for process in processes:
        process.terminate()
        # Give the process a moment to terminate gracefully
        time.sleep(0.5)
    
    # If processes are still running after terminate(), use kill()
    for process in processes:
        if process.poll() is None:  # If process is still running
            process.kill()
            process.wait()  # Wait for process to fully exit
    
    print("All components have been stopped.")
    sys.exit(0)

def main():
    print("Starting RTX 5090 Stock Tracker components...")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # termination signal
    
    # Start Flask app in a separate process
    flask_cmd = [sys.executable, "app.py", "--flask", "--port", "5003"]
    flask_process = subprocess.Popen(flask_cmd)
    processes.append(flask_process)
    print("Flask app started (PID: {})".format(flask_process.pid))
    
    # Give Flask a moment to start
    time.sleep(2)
    
    # Start Dash app in a separate process
    dash_cmd = [sys.executable, "app.py", "--dash", "--port", "8050"]
    dash_process = subprocess.Popen(dash_cmd)
    processes.append(dash_process)
    print("Dash app started (PID: {})".format(dash_process.pid))
    
    # Start monitoring in a separate process
    monitor_cmd = [sys.executable, "app.py", "--monitor"]
    monitor_process = subprocess.Popen(monitor_cmd)
    processes.append(monitor_process)
    print("Monitoring service started (PID: {})".format(monitor_process.pid))
    
    print("\nAll components started successfully!")
    print("- Flask app is running at: http://localhost:5003/")
    print("- Dash app is running at: http://localhost:8050/dashboard/")
    print("\nPress Ctrl+C to shut down all components.")
    
    try:
        # Keep the script running to maintain the processes
        while True:
            time.sleep(1)
            
            # Check if any process has exited unexpectedly
            for p in processes[:]:
                if p.poll() is not None:  # Process has terminated
                    print(f"Process {p.pid} has exited with code {p.returncode}")
                    processes.remove(p)
            
            if not processes:  # All processes have exited
                print("All components have stopped. Exiting.")
                break
                
    except KeyboardInterrupt:
        # KeyboardInterrupt will be caught by the signal handler
        pass

if __name__ == "__main__":
    main()