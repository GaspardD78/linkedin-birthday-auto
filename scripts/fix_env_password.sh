#!/bin/bash

###############################################################################
# Script de Correction - Hash Bcrypt dans .env
#
# Ce script corrige le problème où Docker Compose interprète les caractères $
# du hash bcrypt comme des variables d'environnement.
#
# Usage: ./scripts/fix_env_password.sh
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_header "🔧 CORRECTION DU HASH BCRYPT DANS .env"

cat << 'EOF'
Ce script corrige le problème où Docker Compose interprète les $ du hash bcrypt
comme des variables d'environnement.

📋 CE QUI VA ÊTRE FAIT :
   1. Vérifier si le fichier .env existe
   2. Détecter si DASHBOARD_PASSWORD contient un hash bcrypt
   3. Ajouter des quotes simples autour du hash si nécessaire
   4. Créer un backup avant modification

EOF

# Vérifier si .env existe
if [ ! -f ".env" ]; then
    print_error "Fichier .env introuvable !"
    echo ""
    print_info "Si vous n'avez pas encore de .env, créez-le à partir de l'exemple :"
    print_info "  cp .env.pi4.example .env"
    exit 1
fi

print_success "Fichier .env trouvé"

# Extraire la ligne DASHBOARD_PASSWORD
if ! grep -q "^DASHBOARD_PASSWORD=" .env; then
    print_error "Variable DASHBOARD_PASSWORD introuvable dans .env"
    exit 1
fi

PASSWORD_LINE=$(grep "^DASHBOARD_PASSWORD=" .env)
print_info "Ligne actuelle : ${PASSWORD_LINE:0:40}..."

# Extraire la valeur du mot de passe
PASSWORD_VALUE=$(echo "$PASSWORD_LINE" | cut -d '=' -f2-)

# Vérifier si c'est un hash bcrypt (commence par $2a$, $2b$, ou $2y$)
if [[ ! "$PASSWORD_VALUE" =~ ^\$2[aby]\$ ]] && [[ ! "$PASSWORD_VALUE" =~ ^[\'\"]\$2[aby]\$ ]]; then
    print_error "Le mot de passe ne semble pas être un hash bcrypt"
    print_info "Hash bcrypt attendu : \$2a\$12\$... ou \$2b\$10\$... ou \$2y\$12\$..."
    exit 1
fi

# Vérifier si le hash est déjà échappé ($$ au lieu de $)
if [[ "$PASSWORD_VALUE" =~ \$\$2[aby]\$\$ ]]; then
    print_success "Le hash bcrypt est déjà correctement échappé ($$)"
    echo ""
    print_info "Pas de modification nécessaire !"
    exit 0
fi

print_info "Le hash bcrypt doit être échappé ($ -> $$) pour Docker Compose"
echo ""

# Créer un backup
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp .env "$BACKUP_FILE"
print_success "Backup créé : $BACKUP_FILE"

# Nettoyer le hash (enlever les quotes existantes pour repartir proprement)
CLEAN_HASH=$(echo "$PASSWORD_VALUE" | sed "s/^['\"]//;s/['\"]$//")

# Échapper les $ ($ -> $$)
ESCAPED_HASH="${CLEAN_HASH//$/\$\$}"

# Remplacer dans le fichier
# On utilise sed avec @ comme délimiteur
sed -i "s@^DASHBOARD_PASSWORD=.*@DASHBOARD_PASSWORD='$ESCAPED_HASH'@" .env

print_success "Hash bcrypt corrigé et échappé !"

# Vérifier le résultat
NEW_LINE=$(grep "^DASHBOARD_PASSWORD=" .env)
echo ""
print_info "Nouvelle ligne : ${NEW_LINE:0:50}..."

# Afficher un exemple de ce qui a été changé
echo ""
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 MODIFICATION EFFECTUÉE :

Avant :
   DASHBOARD_PASSWORD='$2a$12$...'

Après :
   DASHBOARD_PASSWORD='$$2a$$12$$...'
                       ↑↑   ↑↑
                   Dollars doublés

Les doubles dollars ($$) sont nécessaires pour que Docker Compose
interprète correctement le caractère $ comme un littéral.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 PROCHAINES ÉTAPES :

1. Redémarrez le dashboard :
   docker compose restart dashboard

2. Vérifiez qu'il n'y a plus de warnings :
   docker compose logs dashboard | grep -i warn

3. Testez la connexion au dashboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

print_success "✓ Correction terminée avec succès !"
echo ""
