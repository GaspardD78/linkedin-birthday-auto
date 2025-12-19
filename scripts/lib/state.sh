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

    # Utiliser Python pour modifier le JSON de manière fiable
    python3 -c "
import json
from datetime import datetime

with open('$SETUP_STATE_FILE', 'r') as f:
    state = json.load(f)

state['checkpoints']['$phase'] = {
    'status': '$status',
    'timestamp': datetime.utcnow().isoformat() + 'Z'
}

with open('$SETUP_STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || {
        log_warn "Python3 non disponible, checkpoint skippé"
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

    # Utiliser Python pour modifier le JSON
    python3 -c "
import json

with open('$SETUP_STATE_FILE', 'r') as f:
    state = json.load(f)

state['config']['$key'] = '$value'

with open('$SETUP_STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || {
        log_warn "Python3 non disponible, config skippé"
    }
}

setup_state_get_config() {
    local key="$1"
    local default="${2:-}"

    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        echo "$default"
        return 0
    fi

    python3 -c "
import json

try:
    with open('$SETUP_STATE_FILE', 'r') as f:
        state = json.load(f)
    print(state.get('config', {}).get('$key', '$default'))
except:
    print('$default')
" 2>/dev/null || echo "$default"
}

# === STATE FINALIZATION ===

finalize_setup_state() {
    local final_status="$1"  # "completed" ou "failed"

    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        return 0
    fi

    python3 -c "
import json
from datetime import datetime

with open('$SETUP_STATE_FILE', 'r') as f:
    state = json.load(f)

state['status'] = '$final_status'
state['completed_at'] = datetime.utcnow().isoformat() + 'Z'

with open('$SETUP_STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || {
        log_warn "Impossible de finaliser l'état du setup"
    }
}
