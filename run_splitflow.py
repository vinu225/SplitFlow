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
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    is_prod = os.environ.get("RENDER") is not None or os.environ.get("NODE_ENV") == "production"

    print("\n" + "=" * 65)
    print("🚀 Starting SplitFlow AI (PayPal Invoicing & Payout Mesh v3.3)")
    print("=" * 65)
    print(f"👉 Server URL:     http://{host}:{port}")
    print(f"👉 Dashboard URL:  http://{host}:{port}/dashboard")
    print(f"👉 API Docs:       http://{host}:{port}/docs")
    print(f"👉 Health Check:   http://{host}:{port}/health")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=not is_prod)

