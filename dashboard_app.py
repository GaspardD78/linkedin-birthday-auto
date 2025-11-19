"""
Application Flask - Dashboard pour LinkedIn Birthday Auto
Permet de visualiser les statistiques, l'historique et gérer la configuration
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from database import get_database
import os
from datetime import datetime, timedelta
import json

# Get the absolute path to the templates folder
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'linkedin_automation.db')


@app.route('/')
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
def messages():
    """Page listant tous les messages d'anniversaire envoyés"""
    db = get_database()

    # Paramètres de pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Récupérer tous les messages (simplif ication - pas de pagination dans la base)
    # On devrait ajouter une fonction get_messages_paginated à database.py pour de vraies applis
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Compter le total
        cursor.execute("SELECT COUNT(*) as total FROM birthday_messages")
        total = cursor.fetchone()['total']

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
        total = cursor.fetchone()['total']

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
def errors():
    """Page listant toutes les erreurs"""
    db = get_database()
    errors_list = db.get_recent_errors(100)

    return render_template('errors.html', errors=errors_list)


@app.route('/contacts')
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
def selectors():
    """Page listant et gérant les sélecteurs LinkedIn"""
    db = get_database()
    selectors_list = db.get_all_selectors()

    return render_template('selectors.html', selectors=selectors_list)


@app.route('/stats')
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


@app.route('/favicon.ico')
def favicon():
    """Route pour éviter les erreurs 404 du favicon"""
    from flask import make_response
    response = make_response('', 204)
    response.headers['Content-Type'] = 'image/x-icon'
    return response


# ==================== API ENDPOINTS ====================

@app.route('/api/stats/<int:days>')
def api_stats(days):
    """API endpoint pour récupérer les statistiques"""
    db = get_database()
    stats = db.get_statistics(days)
    return jsonify(stats)


@app.route('/api/daily-activity/<int:days>')
def api_daily_activity(days):
    """API endpoint pour récupérer l'activité quotidienne"""
    db = get_database()
    activity = db.get_daily_activity(days)
    return jsonify(activity)


@app.route('/api/messages/recent/<int:limit>')
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
def api_recent_errors(limit):
    """API endpoint pour récupérer les erreurs récentes"""
    db = get_database()
    errors = db.get_recent_errors(limit)
    return jsonify(errors)


@app.route('/api/top-contacts/<int:limit>')
def api_top_contacts(limit):
    """API endpoint pour récupérer les top contacts"""
    db = get_database()
    contacts = db.get_top_contacts(limit)
    return jsonify(contacts)


@app.route('/api/weekly-count')
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
                    'data': [item['messages_count'] - item['late_messages'] for item in daily_activity],
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
                    'data': [item['visits_count'] for item in daily_activity],
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

@app.route('/api/cleanup', methods=['POST'])
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
