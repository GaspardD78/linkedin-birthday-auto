#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
export FLASK_APP=src/web/app.py
export FLASK_ENV=development

echo "Starting VisitorBot Dashboard on http://localhost:5000"
flask run --host=0.0.0.0 --port=5000
