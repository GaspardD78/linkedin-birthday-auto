#!/bin/bash
set -euo pipefail

# Script: migrate_compose_references.sh
# Description: Recursively replaces "docker-compose.pi4-standalone.yml" with "docker-compose.yml"
# Usage: ./migrate_compose_references.sh [--dry-run]

# --- Colors for logging ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Variables ---
SEARCH_TERM="docker-compose.pi4-standalone.yml"
REPLACE_TERM="docker-compose.yml"
DRY_RUN=false
COUNT_MODIFIED=0
COUNT_FOUND=0
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- Helper Functions ---
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Argument Parsing ---
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            log_warn "MODE DRY-RUN ACTIVÉ : Aucune modification ne sera appliquée."
            ;;
        *)
            log_error "Argument inconnu : $arg"
            exit 1
            ;;
    esac
done

# --- Main Logic ---
log_info "Démarrage de la migration..."
log_info "Recherche de '${SEARCH_TERM}' pour remplacement par '${REPLACE_TERM}'"
log_info "Racine du projet : ${PROJECT_ROOT}"

# Find files: .sh, .md, .yml
# Exclude: node_modules, .git, .next
# Using process substitution to handle filenames with spaces correctly
while IFS= read -r file; do
    # Skip if file is this script itself (to avoid self-modification issues if renamed later or generic match)
    if [[ "$file" == *"/migrate_compose_references.sh" ]]; then
        continue
    fi

    # Check if the file actually contains the search term
    # grep returns 0 if found, 1 if not. With set -e, checking directly in 'if' prevents exit on 1.
    if grep -qF "$SEARCH_TERM" "$file"; then
        ((COUNT_FOUND++))

        if [ "$DRY_RUN" = true ]; then
            log_info "Found in: $file"
        else
            # Backup
            if ! cp -p "$file" "${file}.bak"; then
                log_error "Échec de la création du backup pour $file"
                continue
            fi

            # Replace
            # Use a different delimiter for sed just in case
            if ! sed -i "s|${SEARCH_TERM}|${REPLACE_TERM}|g" "$file"; then
                log_error "Échec de la modification de $file"
                # Restore backup on failure
                mv "${file}.bak" "$file" || log_error "CRITIQUE: Impossible de restaurer le backup pour $file"
            else
                log_success "Modifié : $file (Backup: ${file}.bak)"
                ((COUNT_MODIFIED++))
            fi
        fi
    fi
done < <(find "${PROJECT_ROOT}" -type f \( -name "*.sh" -o -name "*.md" -o -name "*.yml" \) \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/.next/*" \
    -not -name "*.bak")

# --- Summary ---
echo "------------------------------------------------"
log_info "Résumé de la migration"
echo "------------------------------------------------"
echo "Fichiers trouvés avec le terme    : $COUNT_FOUND"
if [ "$DRY_RUN" = true ]; then
    echo "Fichiers qui seraient modifiés    : $COUNT_FOUND"
    log_warn "Ceci était une simulation. Lancez sans --dry-run pour appliquer."
else
    echo "Fichiers modifiés avec succès     : $COUNT_MODIFIED"
    log_success "Migration terminée."
fi
