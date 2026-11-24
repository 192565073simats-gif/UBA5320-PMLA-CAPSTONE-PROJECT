"""
Single-click launcher for Academic Performance Analyzer.
Just press 'Run' / F5 in VS Code or execute: python run.py
"""

import sys
import webbrowser
import threading
import time
import uvicorn
from pathlib import Path

# Ensure workspace root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def open_browser():
    """Wait 1.5s for the server to start, then open the browser automatically."""
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    print("=" * 65)
    print("  Student Academic Performance Analyzer — Capstone Project")
    print("  Server starting at: http://localhost:8000")
    print("  Login: admin / admin123")
    print("=" * 65)

    # Automatically launch default browser
    threading.Thread(target=open_browser, daemon=True).start()

    # Start Uvicorn server
    uvicorn.run(
        "academic_analyzer.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
