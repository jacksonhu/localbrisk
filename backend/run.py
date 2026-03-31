#!/usr/bin/env python3
"""
LocalBrisk Backend launch entry.
Main entry file for PyInstaller packaging.
"""

import os
import sys

# Ensure app module can be found
if getattr(sys, 'frozen', False):
    # Path after PyInstaller packaging
    application_path = os.path.dirname(sys.executable)
else:
    # Development environment path
    application_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, application_path)

import uvicorn
from main import app


def main():
    """Start FastAPI service."""
    # Configuration parameters
    host = os.environ.get("LOCALBRISK_HOST", "127.0.0.1")
    port = int(os.environ.get("LOCALBRISK_PORT", "8765"))
    
    print(f"LocalBrisk Backend starting...")
    print(f"Service address: http://{host}:{port}")
    
    # Start service
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
