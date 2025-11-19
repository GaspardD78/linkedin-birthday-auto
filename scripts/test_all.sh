#!/bin/bash
# Script de test complet pour LinkedIn Birthday Auto
#
# USAGE: Ce script est conçu pour être exécuté via GitHub Actions uniquement
# Workflow: .github/workflows/test.yml
#
# Pour exécuter les tests:
# 1. GitHub → Actions → "Test Suite - Phase 1" → Run workflow
# 2. Ou automatiquement sur chaque push/PR vers main/master

set -e

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Compteurs
TESTS_PASSED=0
TESTS_FAILED=0

# Fonction pour afficher un test réussi
pass_test() {
    echo -e "${GREEN}✓${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

# Fonction pour afficher un test échoué
fail_test() {
    echo -e "${RED}✗${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

# Fonction pour exécuter un test
run_test() {
    local test_name=$1
    local test_command=$2

    if eval "$test_command" > /dev/null 2>&1; then
        pass_test "$test_name"
        return 0
    else
        fail_test "$test_name"
        return 1
    fi
}

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   LinkedIn Birthday Auto - Test Suite                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}[1/6] Tests Environnement${NC}"
echo "────────────────────────────────────────"

run_test "Python installé" "command -v python"
run_test "Pip installé" "command -v pip"
run_test "Git installé" "command -v git"

echo ""
echo -e "${BLUE}[2/6] Tests Dépendances${NC}"
echo "────────────────────────────────────────"

run_test "Module playwright" "python -c 'import playwright'"
run_test "Module flask" "python -c 'import flask'"
run_test "Module pytz" "python -c 'import pytz'"
run_test "Module sqlite3" "python -c 'import sqlite3'"

echo ""
echo -e "${BLUE}[3/6] Tests Base de Données${NC}"
echo "────────────────────────────────────────"

# Créer une BDD de test temporaire
TEST_DB="test_deployment_$(date +%s).db"

if python -c "
from database import Database
import os
db = Database('$TEST_DB')
assert os.path.exists('$TEST_DB')
# Test d'écriture
contact_id = db.add_contact('Test User', 'https://linkedin.com/in/test')
assert contact_id == 1
# Test de lecture
contact = db.get_contact_by_name('Test User')
assert contact is not None
assert contact['name'] == 'Test User'
# Test de statistiques
stats = db.get_statistics(30)
assert 'messages' in stats
assert 'profile_visits' in stats
print('OK')
" 2>&1 | grep -q "OK"; then
    pass_test "Création base de données"
    pass_test "Opérations CRUD"
    pass_test "Statistiques"

    # Vérifier le mode WAL et la version du schéma avec Python
    if python -c "
import sqlite3
conn = sqlite3.connect('$TEST_DB')
# Vérifier le mode WAL
cursor = conn.cursor()
cursor.execute('PRAGMA journal_mode')
journal_mode = cursor.fetchone()[0]
assert journal_mode.lower() == 'wal', f'Expected WAL mode, got {journal_mode}'
# Vérifier la version du schéma
cursor.execute('SELECT version FROM schema_version')
version = cursor.fetchone()[0]
assert version == '2.1.0', f'Expected version 2.1.0, got {version}'
conn.close()
print('OK')
" 2>&1 | grep -q "OK"; then
        pass_test "Mode WAL activé"
        pass_test "Version schéma correcte"
    else
        fail_test "Mode WAL activé"
        fail_test "Version schéma correcte"
    fi
else
    fail_test "Création base de données"
    fail_test "Opérations CRUD"
    fail_test "Statistiques"
    fail_test "Mode WAL activé"
    fail_test "Version schéma correcte"
fi

# Nettoyer
rm -f "$TEST_DB" "$TEST_DB-shm" "$TEST_DB-wal"

echo ""
echo -e "${BLUE}[4/6] Tests Modules${NC}"
echo "────────────────────────────────────────"

run_test "Import database.py" "python -c 'from database import get_database'"
run_test "Import selector_validator.py" "python -c 'from selector_validator import SelectorValidator'"
run_test "Import dashboard_app.py" "python -c 'from dashboard_app import app'"

# Test du singleton thread-safe
if python -c "
from database import get_database
import threading

results = []

def create_db():
    db = get_database()
    results.append(id(db))

threads = [threading.Thread(target=create_db) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# Tous les threads doivent avoir la même instance
assert len(set(results)) == 1, 'Singleton not thread-safe'
print('OK')
" 2>&1 | grep -q "OK"; then
    pass_test "Singleton thread-safe"
else
    fail_test "Singleton thread-safe"
fi

echo ""
echo -e "${BLUE}[5/6] Tests Fichiers Configuration${NC}"
echo "────────────────────────────────────────"

# Vérifier que les fichiers nécessaires existent
[ -f "messages.txt" ] && pass_test "messages.txt existe" || fail_test "messages.txt existe"
[ -f "late_messages.txt" ] && pass_test "late_messages.txt existe" || fail_test "late_messages.txt existe"
[ -f "config.json" ] && pass_test "config.json existe" || fail_test "config.json existe"
[ -f ".gitignore" ] && pass_test ".gitignore existe" || fail_test ".gitignore existe"

# Vérifier que .gitignore contient *.db
if grep -q "*.db" .gitignore; then
    pass_test ".gitignore contient *.db"
else
    fail_test ".gitignore contient *.db"
fi

echo ""
echo -e "${BLUE}[6/6] Tests Dashboard${NC}"
echo "────────────────────────────────────────"

# Test que le dashboard peut démarrer (sans le lancer vraiment)
if python -c "
from dashboard_app import app
import os
# Test du contexte de l'application
with app.app_context():
    pass
print('OK')
" 2>&1 | grep -q "OK"; then
    pass_test "Dashboard peut démarrer"
else
    fail_test "Dashboard peut démarrer"
fi

# Test de la route / uniquement si les templates existent
if [ -d "templates" ] && [ -f "templates/index.html" ]; then
    if python -c "
from dashboard_app import app
with app.test_client() as client:
    response = client.get('/')
    assert response.status_code == 200
print('OK')
" 2>&1 | grep -q "OK"; then
        pass_test "Route / accessible"
    else
        fail_test "Route / accessible"
    fi
else
    # Templates manquants - on skip le test de route
    echo -e "${YELLOW}⊘${NC} Route / accessible (templates manquants - skip)"
fi

# Test des API endpoints
if python -c "
from dashboard_app import app
with app.test_client() as client:
    response = client.get('/api/stats/30')
    assert response.status_code == 200
    response = client.get('/api/weekly-count')
    assert response.status_code == 200
print('OK')
" 2>&1 | grep -q "OK"; then
    pass_test "API endpoints fonctionnels"
else
    fail_test "API endpoints fonctionnels"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}Résumé${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$(( TESTS_PASSED * 100 / TOTAL_TESTS ))

echo -e "Total: ${BLUE}${TOTAL_TESTS}${NC} tests"
echo -e "Réussis: ${GREEN}${TESTS_PASSED}${NC} tests"
echo -e "Échoués: ${RED}${TESTS_FAILED}${NC} tests"
echo -e "Taux de réussite: ${BLUE}${PASS_RATE}%${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 Tous les tests sont passés avec succès !${NC}"
    echo ""
    echo -e "Vous pouvez maintenant:"
    echo -e "  1. Lancer le dashboard: ${BLUE}./scripts/start_dashboard.sh${NC}"
    echo -e "  2. Tester en DRY_RUN: ${BLUE}DRY_RUN=true python linkedin_birthday_wisher.py${NC}"
    echo -e "  3. Consulter la doc: ${BLUE}cat DEPLOYMENT.md${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  ${TESTS_FAILED} test(s) ont échoué.${NC}"
    echo ""
    echo -e "Consultez la documentation:"
    echo -e "  ${BLUE}cat DEPLOYMENT.md${NC} - Guide de déploiement"
    echo -e "  ${BLUE}cat BUGFIXES.md${NC} - Corrections appliquées"
    echo ""
    exit 1
fi
