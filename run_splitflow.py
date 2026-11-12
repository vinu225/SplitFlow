"""
SplitFlow AI — Quick Start Launch Script.
Run this script to start the backend server and web dashboard:
    python run_splitflow.py
"""
import uvicorn
import os
import sys

# Ensure backend directory is in python module search path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.environ["PYTHONPATH"] = backend_dir

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("🚀 Starting SplitFlow AI (PayPal Invoicing & Payout Mesh v3.3)")
    print("=" * 65)
    print("👉 Dashboard URL:  http://127.0.0.1:8000")
    print("👉 API Docs:       http://127.0.0.1:8000/docs")
    print("👉 Health Check:   http://127.0.0.1:8000/health")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

