#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - STATE MANAGEMENT LIBRARY (v4.0)
# Persistent state and checkpoint tracking
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === STATE FILE MANAGEMENT ===

readonly SETUP_STATE_FILE=".setup.state"
readonly SETUP_STATE_BACKUP_DIR=".setup_backups"

# === STATE INITIALIZATION ===

setup_state_init() {
    log_info "Initialisation de l'état du setup..."

    # Créer le répertoire de backup s'il n'existe pas
    mkdir -p "$SETUP_STATE_BACKUP_DIR"

    # Si le fichier state existe, le renommer en backup
    if [[ -f "$SETUP_STATE_FILE" ]]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local backup_file="${SETUP_STATE_BACKUP_DIR}/${SETUP_STATE_FILE}-${timestamp}.json"
        mv "$SETUP_STATE_FILE" "$backup_file"
        log_info "Ancien état sauvegardé: $backup_file"
    fi

    # Créer un nouveau fichier state
    cat > "$SETUP_STATE_FILE" <<EOF
{
  "version": "4.0",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "in_progress",
  "checkpoints": {},
  "config": {}
}
EOF

    log_success "✓ État du setup initialisé"
}

# === CHECKPOINT MANAGEMENT ===

setup_state_checkpoint() {
    local phase="$1"
    local status="$2"  # "completed" ou "failed"

    log_info "Checkpoint: $phase -> $status"

    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        log_warn "Fichier state non trouvé, initialisation..."
        setup_state_init
    fi

    # Utiliser des variables d'environnement pour éviter l'injection de code
    # Fixes Issue #15: PYTHON3 -c INJECTION VECTOR
    export STATE_FILE="$SETUP_STATE_FILE"
    export PHASE="$phase"
    export STATUS="$status"

    python3 -c "
import json
import os
import sys
from datetime import datetime

state_file = os.environ['STATE_FILE']
phase = os.environ['PHASE']
status = os.environ['STATUS']

try:
    with open(state_file, 'r') as f:
        state = json.load(f)

    if 'checkpoints' not in state:
        state['checkpoints'] = {}

    state['checkpoints'][phase] = {
        'status': status,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
except Exception as e:
    sys.exit(1)
" 2>/dev/null || {
        log_warn "Erreur checkpoint Python (ou Python3 manquant)"
    }
}

# === CONFIG MANAGEMENT ===

setup_state_set_config() {
    local key="$1"
    local value="$2"

    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        log_warn "Fichier state non trouvé"
        return 0
    fi

    # Utiliser des variables d'environnement pour éviter l'injection
    export STATE_FILE="$SETUP_STATE_FILE"
    export CONFIG_KEY="$key"
    export CONFIG_VALUE="$value"

    python3 -c "
import json
import os
import sys

state_file = os.environ['STATE_FILE']
key = os.environ['CONFIG_KEY']
value = os.environ['CONFIG_VALUE']

try:
    with open(state_file, 'r') as f:
        state = json.load(f)

    if 'config' not in state:
        state['config'] = {}

    state['config'][key] = value

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
except Exception as e:
    sys.exit(1)
" 2>/dev/null || {
        log_warn "Erreur config Python"
    }
}

setup_state_get_config() {
    local key="$1"
    local default="${2:-}"

    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        echo "$default"
        return 0
    fi

    export STATE_FILE="$SETUP_STATE_FILE"
    export CONFIG_KEY="$key"
    export DEFAULT_VAL="$default"

    python3 -c "
import json
import os

state_file = os.environ['STATE_FILE']
key = os.environ['CONFIG_KEY']
default_val = os.environ['DEFAULT_VAL']

try:
    with open(state_file, 'r') as f:
        state = json.load(f)
    print(state.get('config', {}).get(key, default_val))
except:
    print(default_val)
" 2>/dev/null || echo "$default"
}

# === STATE FINALIZATION ===

finalize_setup_state() {
    local final_status="$1"  # "completed" ou "failed"

    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        return 0
    fi

    export STATE_FILE="$SETUP_STATE_FILE"
    export FINAL_STATUS="$final_status"

    python3 -c "
import json
import os
import sys
from datetime import datetime

state_file = os.environ['STATE_FILE']
final_status = os.environ['FINAL_STATUS']

try:
    with open(state_file, 'r') as f:
        state = json.load(f)

    state['status'] = final_status
    state['completed_at'] = datetime.utcnow().isoformat() + 'Z'

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
except Exception as e:
    sys.exit(1)
" 2>/dev/null || {
        log_warn "Impossible de finaliser l'état du setup"
    }
}
