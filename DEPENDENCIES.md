# Dependencies

Core parsing, storage, and CLI use Python 3.12 standard library. Live scanning optionally requires Bleak and a working BlueZ service. The dashboard optionally requires FastAPI and Uvicorn. Unit tests use `unittest`; CI installs Ruff. No PostgreSQL, Docker, GNU Radio, or frontend build is needed for this local application.
