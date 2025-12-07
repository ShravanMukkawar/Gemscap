"""
Main entry point for Trading Analytics Platform
Launches FastAPI backend and Streamlit frontend
"""
import subprocess
import sys
import time
import os
from pathlib import Path
import threading

# Create necessary directories
Path("data").mkdir(exist_ok=True)
Path("data/logs").mkdir(exist_ok=True)

def stream_output(process, prefix):
    """Stream process output to console"""
    for line in iter(process.stdout.readline, b''):
        if line:
            print(f"[{prefix}] {line.decode().strip()}")

def main():
    """Launch both FastAPI and Streamlit"""
    print("="*60)
    print("[STARTING] Trading Analytics Platform")
    print("="*60)
    
    # Start FastAPI backend
    print("\n[1/2] Starting FastAPI backend on http://localhost:8000")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", 
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1
    )
    
    # Start thread to stream backend output
    backend_thread = threading.Thread(
        target=stream_output, 
        args=(backend_process, "BACKEND"),
        daemon=True
    )
    backend_thread.start()
    
    # Wait for backend to start
    print("   Waiting for backend to initialize...")
    time.sleep(5)
    
    # Start Streamlit frontend
    print("\n[2/2] Starting Streamlit frontend on http://localhost:8501")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/dashboard.py",
         "--server.port", "8501", "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1
    )
    
    # Start thread to stream frontend output
    frontend_thread = threading.Thread(
        target=stream_output, 
        args=(frontend_process, "FRONTEND"),
        daemon=True
    )
    frontend_thread.start()
    
    print("\n" + "="*60)
    print("[OK] Platform running!")
    print("   [*] Dashboard: http://localhost:8501")
    print("   [*] API: http://localhost:8000")
    print("   [*] API Docs: http://localhost:8000/docs")
    print("="*60)
    print("\n[WAIT] Starting services (this may take 10-20 seconds)...")
    print("   Watch for 'Application startup complete' messages above")
    print("\nPress Ctrl+C to stop both services\n")
    
    try:
        # Keep both processes running
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n\n[STOP] Shutting down...")
        backend_process.terminate()
        frontend_process.terminate()
        
        # Wait for graceful shutdown
        try:
            backend_process.wait(timeout=5)
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            frontend_process.kill()
        
        print("[OK] Shutdown complete")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    main()