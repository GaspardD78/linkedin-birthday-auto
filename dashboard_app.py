"""
Application Flask - Dashboard pour LinkedIn Birthday Auto
Permet de visualiser les statistiques, l'historique, gérer la configuration et contrôler les scripts
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_database
import os
import time
import json
import subprocess
import psutil
import signal
from datetime import datetime, timedelta
import logging

# Get the absolute path to the templates folder
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, 'templates')

# Configure logging for dashboard
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'linkedin_automation.db')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', 'admin')  # Change in production!
app.config['AUTH_FILE'] = 'dashboard_auth.json'

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return User('admin')
    return None

# ==================== AUTHENTICATION ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form['password']
        authenticated = False

        # Check for auth file first
        if os.path.exists(app.config['AUTH_FILE']):
            try:
                with open(app.config['AUTH_FILE'], 'r') as f:
                    auth_data = json.load(f)
                    if 'password_hash' in auth_data:
                        if check_password_hash(auth_data['password_hash'], password):
                            authenticated = True
            except Exception as e:
                print(f"Error reading auth file: {e}")

        # Fallback to env/config password if no auth file or auth failed (and file didn't exist)
        if not authenticated and not os.path.exists(app.config['AUTH_FILE']):
            if password == app.config['ADMIN_PASSWORD']:
                authenticated = True

        if authenticated:
            user = User('admin')
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Mot de passe incorrect')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==================== MAIN ROUTES ====================

@app.route('/')
@login_required
def index():
    """Page d'accueil du dashboard"""
    db = get_database()

    # Statistiques générales (30 derniers jours)
    stats_30d = db.get_statistics(30)

    # Statistiques hebdomadaires
    stats_7d = db.get_statistics(7)

    # Activité quotidienne (14 derniers jours)
    daily_activity = db.get_daily_activity(14)

    # Top contacts
    top_contacts = db.get_top_contacts(5)

    # Erreurs récentes (10 dernières)
    recent_errors = db.get_recent_errors(10)

    # Nombre de messages envoyés cette semaine
    weekly_count = db.get_weekly_message_count()

    return render_template(
        'index.html',
        stats_30d=stats_30d,
        stats_7d=stats_7d,
        daily_activity=daily_activity,
        top_contacts=top_contacts,
        recent_errors=recent_errors,
        weekly_count=weekly_count,
        weekly_limit=80  # WEEKLY_MESSAGE_LIMIT
    )

@app.route('/messages')
@login_required
def messages():
    """Page listant tous les messages d'anniversaire envoyés"""
    db = get_database()

    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Compter le total
        cursor.execute("SELECT COUNT(*) as total FROM birthday_messages")
        row = cursor.fetchone()
        total = row['total'] if row else 0

        # Récupérer la page actuelle
        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT * FROM birthday_messages
            ORDER BY sent_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        messages_list = [dict(row) for row in cursor.fetchall()]

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'messages.html',
        messages=messages_list,
        page=page,
        total_pages=total_pages,
        total=total
    )

@app.route('/visits')
@login_required
def visits():
    """Page listant toutes les visites de profils"""
    db = get_database()

    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Compter le total
        cursor.execute("SELECT COUNT(*) as total FROM profile_visits")
        row = cursor.fetchone()
        total = row['total'] if row else 0

        # Récupérer la page actuelle
        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT * FROM profile_visits
            ORDER BY visited_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        visits_list = [dict(row) for row in cursor.fetchall()]

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'visits.html',
        visits=visits_list,
        page=page,
        total_pages=total_pages,
        total=total
    )

@app.route('/errors')
@login_required
def errors():
    """Page listant toutes les erreurs"""
    db = get_database()
    errors_list = db.get_recent_errors(100)

    return render_template('errors.html', errors=errors_list)

@app.route('/contacts')
@login_required
def contacts():
    """Page listant tous les contacts"""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM contacts
            ORDER BY message_count DESC, last_message_date DESC
        """)
        contacts_list = [dict(row) for row in cursor.fetchall()]

    return render_template('contacts.html', contacts=contacts_list)

@app.route('/selectors')
@login_required
def selectors():
    """Page listant et gérant les sélecteurs LinkedIn"""
    db = get_database()
    selectors_list = db.get_all_selectors()

    return render_template('selectors.html', selectors=selectors_list)

@app.route('/stats')
@login_required
def stats():
    """Page de statistiques détaillées"""
    db = get_database()

    # Statistiques par période
    stats_7d = db.get_statistics(7)
    stats_30d = db.get_statistics(30)
    stats_90d = db.get_statistics(90)

    # Activité quotidienne sur 30 jours
    daily_activity = db.get_daily_activity(30)

    return render_template(
        'stats.html',
        stats_7d=stats_7d,
        stats_30d=stats_30d,
        stats_90d=stats_90d,
        daily_activity=daily_activity
    )

# ==================== CONFIGURATION & CONTROL ====================

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        flash('Tous les champs sont requis', 'danger')
        return redirect(url_for('config'))

    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas', 'danger')
        return redirect(url_for('config'))

    # Verify current password
    authenticated = False
    if os.path.exists(app.config['AUTH_FILE']):
        try:
            with open(app.config['AUTH_FILE'], 'r') as f:
                auth_data = json.load(f)
                if 'password_hash' in auth_data:
                    if check_password_hash(auth_data['password_hash'], current_password):
                        authenticated = True
        except Exception:
            pass
    else:
        # Fallback check
        if current_password == app.config['ADMIN_PASSWORD']:
            authenticated = True

    if not authenticated:
        flash('Mot de passe actuel incorrect', 'danger')
        return redirect(url_for('config'))

    # Save new password
    try:
        password_hash = generate_password_hash(new_password)
        with open(app.config['AUTH_FILE'], 'w') as f:
            json.dump({'password_hash': password_hash}, f)
        flash('Mot de passe modifié avec succès', 'success')
    except Exception as e:
        flash(f'Erreur lors de la sauvegarde du mot de passe: {str(e)}', 'danger')

    return redirect(url_for('config'))


@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    """Page de configuration"""
    config_path = 'config.json'
    messages_path = 'messages.txt'
    late_messages_path = 'late_messages.txt'

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_config':
            try:
                new_config = request.form.get('config_json')
                # Verify JSON validity
                json.loads(new_config)
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(new_config)
                flash('Configuration mise à jour avec succès', 'success')
            except json.JSONDecodeError:
                flash('Erreur: JSON invalide', 'danger')
            except Exception as e:
                flash(f'Erreur lors de la sauvegarde: {str(e)}', 'danger')

        elif action == 'update_messages':
            try:
                new_messages = request.form.get('messages_content')
                with open(messages_path, 'w', encoding='utf-8') as f:
                    f.write(new_messages)
                flash('Messages mis à jour avec succès', 'success')
            except Exception as e:
                flash(f'Erreur lors de la sauvegarde: {str(e)}', 'danger')

        elif action == 'update_late_messages':
            try:
                new_messages = request.form.get('late_messages_content')
                with open(late_messages_path, 'w', encoding='utf-8') as f:
                    f.write(new_messages)
                flash('Messages de retard mis à jour avec succès', 'success')
            except Exception as e:
                flash(f'Erreur lors de la sauvegarde: {str(e)}', 'danger')

        return redirect(url_for('config'))

    # Read current files
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
    except:
        config_content = "{}"

    try:
        with open(messages_path, 'r', encoding='utf-8') as f:
            messages_content = f.read()
    except:
        messages_content = ""

    try:
        with open(late_messages_path, 'r', encoding='utf-8') as f:
            late_messages_content = f.read()
    except:
        late_messages_content = ""

    return render_template(
        'config.html',
        config_content=config_content,
        messages_content=messages_content,
        late_messages_content=late_messages_content
    )

@app.route('/logs')
@login_required
def logs():
    """Page de visualisation des logs"""
    log_files = []
    selected_log = request.args.get('file', 'birthday_wisher.log')
    log_content = ""

    # List available log files
    log_dir = 'logs'
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]

    # Read selected log
    if selected_log and os.path.exists(os.path.join(log_dir, selected_log)):
        try:
            with open(os.path.join(log_dir, selected_log), 'r', encoding='utf-8') as f:
                # Read last 1000 lines efficiently
                lines = f.readlines()
                log_content = "".join(lines[-1000:])
        except Exception as e:
            log_content = f"Error reading log file: {str(e)}"

    return render_template('logs.html', log_files=log_files, selected_log=selected_log, log_content=log_content)

@app.route('/control')
@login_required
def control():
    """Page de contrôle des processus"""
    processes = []

    # Check for running python scripts
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'python' in cmdline[0]:
                script_name = None
                for arg in cmdline:
                    if 'linkedin_birthday_wisher.py' in arg:
                        script_name = 'linkedin_birthday_wisher.py'
                    elif 'visit_profiles.py' in arg:
                        script_name = 'visit_profiles.py'

                if script_name:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': script_name,
                        'started': datetime.fromtimestamp(proc.info['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
                        'status': proc.status()
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return render_template('control.html', processes=processes)

@app.route('/api/control/<action>', methods=['POST'])
@login_required
def api_control(action):
    """API pour démarrer/arrêter les scripts"""
    script = request.json.get('script')

    if action == 'start':
        if script not in ['linkedin_birthday_wisher.py', 'visit_profiles.py']:
            return jsonify({'success': False, 'message': 'Script inconnu'})

        try:
            # Run in background, redirecting output to log file handled by script itself
            # But we also redirect stdout/stderr here to capture crash dumps
            # Set cwd to script directory to ensure auth files are found
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = ['python', script]
            subprocess.Popen(cmd, close_fds=True, cwd=script_dir)
            return jsonify({'success': True, 'message': f'Script {script} démarré'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    elif action == 'stop':
        pid = request.json.get('pid')
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            # Wait a bit and kill if still alive
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return jsonify({'success': True, 'message': 'Processus arrêté'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    return jsonify({'success': False, 'message': 'Action inconnue'})

@app.route('/favicon.ico')
def favicon():
    """Route pour éviter les erreurs 404 du favicon"""
    from flask import make_response
    response = make_response('', 204)
    response.headers['Content-Type'] = 'image/x-icon'
    return response


# ==================== API ENDPOINTS ====================

@app.route('/api/stats/<int:days>')
@login_required
def api_stats(days):
    """API endpoint pour récupérer les statistiques"""
    db = get_database()
    stats = db.get_statistics(days)
    return jsonify(stats)


@app.route('/api/daily-activity/<int:days>')
@login_required
def api_daily_activity(days):
    """API endpoint pour récupérer l'activité quotidienne"""
    db = get_database()
    activity = db.get_daily_activity(days)
    return jsonify(activity)


@app.route('/api/messages/recent/<int:limit>')
@login_required
def api_recent_messages(limit):
    """API endpoint pour récupérer les messages récents"""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM birthday_messages
            ORDER BY sent_at DESC
            LIMIT ?
        """, (limit,))
        messages = [dict(row) for row in cursor.fetchall()]

    return jsonify(messages)


@app.route('/api/visits/recent/<int:limit>')
@login_required
def api_recent_visits(limit):
    """API endpoint pour récupérer les visites récentes"""
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM profile_visits
            ORDER BY visited_at DESC
            LIMIT ?
        """, (limit,))
        visits = [dict(row) for row in cursor.fetchall()]

    return jsonify(visits)


@app.route('/api/errors/recent/<int:limit>')
@login_required
def api_recent_errors(limit):
    """API endpoint pour récupérer les erreurs récentes"""
    db = get_database()
    errors = db.get_recent_errors(limit)
    return jsonify(errors)


@app.route('/api/top-contacts/<int:limit>')
@login_required
def api_top_contacts(limit):
    """API endpoint pour récupérer les top contacts"""
    db = get_database()
    contacts = db.get_top_contacts(limit)
    return jsonify(contacts)


@app.route('/api/weekly-count')
@login_required
def api_weekly_count():
    """API endpoint pour récupérer le compteur hebdomadaire"""
    db = get_database()
    count = db.get_weekly_message_count()
    return jsonify({
        'count': count,
        'limit': 80,
        'remaining': max(0, 80 - count),
        'percentage': (count / 80 * 100) if count > 0 else 0
    })


@app.route('/api/chart-data/<chart_type>')
@login_required
def api_chart_data(chart_type):
    """
    API endpoint pour récupérer les données de graphiques
    Types: messages_trend, visits_trend, errors_trend
    """
    db = get_database()
    days = request.args.get('days', 30, type=int)

    daily_activity = db.get_daily_activity(days)

    if chart_type == 'messages_trend':
        data = {
            'labels': [item['date'] for item in daily_activity],
            'datasets': [
                {
                    'label': 'Messages à temps',
                    'data': [item['messages'] - item['late_messages'] for item in daily_activity],
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 2
                },
                {
                    'label': 'Messages en retard',
                    'data': [item['late_messages'] for item in daily_activity],
                    'backgroundColor': 'rgba(255, 159, 64, 0.2)',
                    'borderColor': 'rgba(255, 159, 64, 1)',
                    'borderWidth': 2
                }
            ]
        }
    elif chart_type == 'visits_trend':
        data = {
            'labels': [item['date'] for item in daily_activity],
            'datasets': [
                {
                    'label': 'Profils visités',
                    'data': [item['visits'] for item in daily_activity],
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 2
                }
            ]
        }
    else:
        data = {'error': 'Unknown chart type'}

    return jsonify(data)


# ==================== MAINTENANCE ====================

@app.route('/api/system_status')
@login_required
def api_system_status():
    """API endpoint pour l'état du système"""
    # Check scripts status
    scripts_status = {
        'birthday_wisher': False,
        'visit_profiles': False
    }

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'python' in cmdline[0]:
                for arg in cmdline:
                    if 'linkedin_birthday_wisher.py' in arg:
                        scripts_status['birthday_wisher'] = True
                    elif 'visit_profiles.py' in arg:
                        scripts_status['visit_profiles'] = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # System stats
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()

    return jsonify({
        'scripts': scripts_status,
        'system': {
            'cpu': cpu_percent,
            'memory': memory.percent
        }
    })

@app.route('/api/logs/content')
@login_required
def api_logs_content():
    """API endpoint pour récupérer le contenu des logs"""
    lines_count = request.args.get('lines', 50, type=int)
    log_type = request.args.get('type', 'birthday') # birthday, visit, or system

    filename = 'birthday_wisher.log'
    if log_type == 'visit':
        filename = 'visit_profiles.log'
    elif log_type == 'system':
        # Find the dashboard log if it exists, otherwise use default
        filename = 'dashboard.log'

    log_dir = 'logs'
    filepath = os.path.join(log_dir, filename)

    content = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Read all lines and take the last N
                # For very large files, this could be optimized but sufficient for now
                all_lines = f.readlines()
                content = all_lines[-lines_count:]
        except Exception as e:
            content = [f"Error reading log: {str(e)}"]
    else:
        content = [f"Log file not found: {filename}"]

    return jsonify({
        'lines': content,
        'filename': filename
    })

@app.route('/api/cleanup', methods=['POST'])
@login_required
def api_cleanup():
    """API endpoint pour nettoyer les anciennes données"""
    days_to_keep = request.json.get('days_to_keep', 365)

    db = get_database()
    result = db.cleanup_old_data(days_to_keep)

    return jsonify({
        'success': True,
        'deleted': result
    })


@app.route('/api/export', methods=['POST'])
@login_required
def api_export():
    """API endpoint pour exporter la base de données en JSON"""
    output_path = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    db = get_database()
    db.export_to_json(output_path)

    return jsonify({
        'success': True,
        'file': output_path
    })


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


# ==================== TEMPLATE FILTERS ====================

@app.template_filter('datetime_format')
def datetime_format(value, format='%Y-%m-%d %H:%M:%S'):
    """Formate une date ISO en format lisible"""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime(format)
    except:
        return value


@app.template_filter('date_format')
def date_format(value, format='%d/%m/%Y'):
    """Formate une date"""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            dt = value
        return dt.strftime(format)
    except:
        return value


@app.template_filter('time_ago')
def time_ago(value):
    """Affiche le temps écoulé depuis une date"""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        now = datetime.now()
        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"il y a {years} an{'s' if years > 1 else ''}"
        elif diff.days > 30:
            months = diff.days // 30
            return f"il y a {months} mois"
        elif diff.days > 0:
            return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"il y a {hours} heure{'s' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "à l'instant"
    except:
        return value


if __name__ == '__main__':
    # Mode développement
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"""
    ╔═══════════════════════════════════════════════════════╗
    ║   LinkedIn Birthday Auto - Dashboard                  ║
    ║   http://localhost:{port}                                  ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    app.run(host='0.0.0.0', port=port, debug=debug)
