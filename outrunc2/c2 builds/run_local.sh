#!/usr/bin/env bash
# Run the Flask app locally for development (without Docker).
set -e
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Launch the app using Flask's built-in server for dev
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=8080