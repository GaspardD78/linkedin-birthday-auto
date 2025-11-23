#!/bin/bash

# =========================================================================
# Script de migration MySQL (Synology) vers SQLite (Pi4 Standalone)
# =========================================================================
#
# Ce script permet de migrer les données depuis une base MySQL Synology
# vers une base SQLite locale pour le déploiement standalone sur Pi4.
#
# Utilisation:
#   ./scripts/migrate_mysql_to_sqlite.sh
#
# Prérequis:
# - Accès à la base MySQL Synology (IP, port, user, password)
# - mysql-client installé: sudo apt install -y mysql-client
# - sqlite3 installé: sudo apt install -y sqlite3
# =========================================================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Emojis
CHECKMARK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}${CHECKMARK} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

# =========================================================================
# Vérifications préalables
# =========================================================================

print_header "Migration MySQL → SQLite"

# Vérifier mysql-client
if ! command -v mysql &> /dev/null; then
    print_error "mysql-client n'est pas installé"
    print_info "Installez-le avec: sudo apt install -y mysql-client"
    exit 1
fi
print_success "mysql-client installé"

# Vérifier sqlite3
if ! command -v sqlite3 &> /dev/null; then
    print_error "sqlite3 n'est pas installé"
    print_info "Installez-le avec: sudo apt install -y sqlite3"
    exit 1
fi
print_success "sqlite3 installé"

# =========================================================================
# Configuration MySQL source
# =========================================================================

print_header "Configuration MySQL (Synology)"

read -p "IP du Synology (ex: 192.168.1.10): " MYSQL_HOST
read -p "Port MySQL (défaut: 3306): " MYSQL_PORT
MYSQL_PORT=${MYSQL_PORT:-3306}
read -p "Nom de la base (défaut: linkedin_bot): " MYSQL_DB
MYSQL_DB=${MYSQL_DB:-linkedin_bot}
read -p "Utilisateur MySQL (défaut: linkedin_user): " MYSQL_USER
MYSQL_USER=${MYSQL_USER:-linkedin_user}
read -sp "Mot de passe MySQL: " MYSQL_PASS
echo ""

# =========================================================================
# Test de connexion MySQL
# =========================================================================

print_header "Test de connexion MySQL"

if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "USE $MYSQL_DB;" 2>/dev/null; then
    print_success "Connexion MySQL réussie"
else
    print_error "Impossible de se connecter à MySQL"
    exit 1
fi

# =========================================================================
# Configuration SQLite destination
# =========================================================================

print_header "Configuration SQLite"

SQLITE_DB="./data/linkedin.db"

# Créer le répertoire data si nécessaire
mkdir -p ./data

# Sauvegarder l'ancienne base si elle existe
if [ -f "$SQLITE_DB" ]; then
    BACKUP_FILE="$SQLITE_DB.backup.$(date +%Y%m%d_%H%M%S)"
    print_warning "Une base SQLite existe déjà"
    print_info "Sauvegarde dans: $BACKUP_FILE"
    cp "$SQLITE_DB" "$BACKUP_FILE"
    print_success "Sauvegarde créée"
    rm "$SQLITE_DB"
fi

# =========================================================================
# Récupération de la structure des tables
# =========================================================================

print_header "Récupération des tables MySQL"

TABLES=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -D "$MYSQL_DB" -N -e "SHOW TABLES;")

if [ -z "$TABLES" ]; then
    print_warning "Aucune table trouvée dans la base MySQL"
    print_info "La base est vide ou n'existe pas"
    exit 1
fi

print_success "Tables trouvées:"
echo "$TABLES" | while read -r table; do
    echo "  - $table"
done

# =========================================================================
# Migration des données
# =========================================================================

print_header "Migration des données"

TEMP_SQL="/tmp/mysql_dump_$$.sql"

# Dumper les données MySQL
print_info "Export des données MySQL..."
mysqldump \
    -h "$MYSQL_HOST" \
    -P "$MYSQL_PORT" \
    -u "$MYSQL_USER" \
    -p"$MYSQL_PASS" \
    --compatible=sqlite \
    --skip-extended-insert \
    --compact \
    "$MYSQL_DB" > "$TEMP_SQL"

if [ $? -eq 0 ]; then
    print_success "Export MySQL réussi"
else
    print_error "Échec de l'export MySQL"
    exit 1
fi

# Adapter le dump pour SQLite
print_info "Adaptation du dump pour SQLite..."

# Supprimer les backticks MySQL
sed -i "s/\`//g" "$TEMP_SQL"

# Remplacer AUTO_INCREMENT par AUTOINCREMENT
sed -i "s/AUTO_INCREMENT/AUTOINCREMENT/gi" "$TEMP_SQL"

# Remplacer les types MySQL par SQLite
sed -i "s/int([0-9]*)/INTEGER/gi" "$TEMP_SQL"
sed -i "s/varchar([0-9]*)/TEXT/gi" "$TEMP_SQL"
sed -i "s/text/TEXT/gi" "$TEMP_SQL"
sed -i "s/datetime/TEXT/gi" "$TEMP_SQL"
sed -i "s/timestamp/TEXT/gi" "$TEMP_SQL"
sed -i "s/tinyint(1)/INTEGER/gi" "$TEMP_SQL"
sed -i "s/ENGINE=InnoDB.*;//g" "$TEMP_SQL"
sed -i "s/DEFAULT CURRENT_TIMESTAMP//gi" "$TEMP_SQL"

# Supprimer les lignes vides
sed -i '/^$/d' "$TEMP_SQL"

print_success "Dump adapté pour SQLite"

# Importer dans SQLite
print_info "Import dans SQLite..."
sqlite3 "$SQLITE_DB" < "$TEMP_SQL"

if [ $? -eq 0 ]; then
    print_success "Import SQLite réussi"
else
    print_error "Échec de l'import SQLite"
    rm "$TEMP_SQL"
    exit 1
fi

# Nettoyer le fichier temporaire
rm "$TEMP_SQL"

# =========================================================================
# Vérification de la migration
# =========================================================================

print_header "Vérification de la migration"

# Compter les tables dans SQLite
SQLITE_TABLES=$(sqlite3 "$SQLITE_DB" ".tables" | wc -w)
MYSQL_TABLES=$(echo "$TABLES" | wc -l)

print_info "Tables MySQL: $MYSQL_TABLES"
print_info "Tables SQLite: $SQLITE_TABLES"

if [ "$SQLITE_TABLES" -eq "$MYSQL_TABLES" ]; then
    print_success "Nombre de tables OK"
else
    print_warning "Nombre de tables différent (MySQL: $MYSQL_TABLES, SQLite: $SQLITE_TABLES)"
fi

# Afficher les tables SQLite
print_info "Tables dans SQLite:"
sqlite3 "$SQLITE_DB" ".tables" | tr ' ' '\n' | while read -r table; do
    if [ -n "$table" ]; then
        COUNT=$(sqlite3 "$SQLITE_DB" "SELECT COUNT(*) FROM $table;")
        echo "  - $table: $COUNT lignes"
    fi
done

# =========================================================================
# Test de lecture SQLite
# =========================================================================

print_info "Test de lecture SQLite..."
TEST_QUERY="SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;"
TEST_RESULT=$(sqlite3 "$SQLITE_DB" "$TEST_QUERY" 2>&1)

if [ $? -eq 0 ]; then
    print_success "Base SQLite fonctionnelle"
else
    print_error "Problème avec la base SQLite"
    print_error "$TEST_RESULT"
    exit 1
fi

# =========================================================================
# Résumé
# =========================================================================

print_header "Migration terminée ${CHECKMARK}"

echo ""
print_success "Base de données migrée avec succès !"
echo ""
print_info "Fichier SQLite: $SQLITE_DB"
print_info "Taille: $(du -h "$SQLITE_DB" | cut -f1)"
echo ""
print_warning "Prochaines étapes:"
echo "  1. Vérifiez les données dans SQLite"
echo "  2. Testez le bot avec la nouvelle base"
echo "  3. Si tout fonctionne, vous pouvez désactiver MySQL sur le Synology"
echo ""
print_info "Pour vérifier les données:"
echo "  sqlite3 $SQLITE_DB"
echo "  sqlite> .tables"
echo "  sqlite> SELECT * FROM <table_name> LIMIT 10;"
echo "  sqlite> .quit"
echo ""
print_info "Pour utiliser la nouvelle base, assurez-vous que DATABASE_URL est configuré:"
echo "  DATABASE_URL=sqlite:///app/data/linkedin.db"
echo ""

# =========================================================================
# Sauvegarde recommandée
# =========================================================================

print_warning "💾 Pensez à sauvegarder régulièrement votre base SQLite !"
echo ""
print_info "Commande de sauvegarde automatique (cron):"
echo "  0 3 * * * cp $SQLITE_DB ${SQLITE_DB}.backup.\$(date +\\%Y\\%m\\%d)"
echo ""
