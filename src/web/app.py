import os
import subprocess
import signal
import sys
import json
import time
import logging
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.database import get_database

app = Flask(__name__)

# Global variable to store the bot process
BOT_PROCESS = None
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "linkedin_bot.log")

def get_db():
    return get_database("linkedin_automation.db")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/campaigns', methods=['GET', 'POST'])
def campaigns():
    db = get_db()
    if request.method == 'POST':
        data = request.json
        campaign_id = db.create_campaign(
            name=data.get('name', 'Untitled Campaign'),
            search_url=data.get('search_url', ''),
            filters=data.get('filters', {})
        )
        return jsonify({"success": True, "campaign_id": campaign_id})
    else:
        campaigns = db.get_campaigns()
        return jsonify(campaigns)

@app.route('/api/launch', methods=['POST'])
def launch_bot():
    global BOT_PROCESS

    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        return jsonify({"success": False, "message": "Bot is already running"}), 400

    data = request.json
    keywords = data.get('keywords', [])
    location = data.get('location', '')
    limit = data.get('limit', 20)
    dry_run = data.get('dry_run', False)

    # Save campaign configuration
    db = get_db()
    db.create_campaign(
        name=f"Search {keywords} in {location}",
        search_url="", # Constructed by bot
        filters={"keywords": keywords, "location": location, "limit": limit}
    )

    # Construct command
    cmd = [
        sys.executable, "-m", "src.bots.visitor_bot",
        "--keywords"
    ] + keywords + [
        "--location", location,
        "--limit", str(limit)
    ]

    if dry_run:
        cmd.append("--dry-run")

    try:
        # Launch process detached
        # Redirect stdout/stderr to log file or pipe
        # Here we rely on the bot's internal logging to file, but we can also capture stdout

        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        BOT_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
            env=env
        )

        return jsonify({"success": True, "pid": BOT_PROCESS.pid, "message": "Bot started"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        BOT_PROCESS.terminate()
        try:
            BOT_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            BOT_PROCESS.kill()
        BOT_PROCESS = None
        return jsonify({"success": True, "message": "Bot stopped"})
    return jsonify({"success": False, "message": "Bot is not running"})

@app.route('/api/status')
def status():
    global BOT_PROCESS
    is_running = BOT_PROCESS is not None and BOT_PROCESS.poll() is None

    # Get latest stats
    db = get_db()
    stats = db.get_today_statistics()

    return jsonify({
        "running": is_running,
        "pid": BOT_PROCESS.pid if is_running else None,
        "stats": stats
    })

@app.route('/api/logs')
def stream_logs():
    def generate():
        if not os.path.exists(LOG_FILE):
            yield "data: Log file not found\n\n"
            return

        with open(LOG_FILE, "r") as f:
            # Read last 20 lines initially
            lines = f.readlines()[-20:]
            for line in lines:
                yield f"data: {line.strip()}\n\n"

            # Tail the file
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(0.5)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/profiles')
def get_profiles():
    db = get_db()
    profiles = db.get_all_scraped_profiles(limit=100)
    return jsonify(profiles)

@app.route('/api/export')
def export_csv():
    db = get_db()
    path = "scraped_profiles_export.csv"
    full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", path))
    db.export_scraped_data_to_csv(full_path)

    with open(full_path, 'r') as f:
        csv_content = f.read()

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=profiles.csv"}
    )

if __name__ == '__main__':
    # Ensure logs dir exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
