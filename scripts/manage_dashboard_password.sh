#!/bin/bash
# Wrapper pour gérer le mot de passe via la lib unifiée
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/security.sh"

read -s -r -p "Nouveau mot de passe: " PASSWORD
echo ""
hash_and_store_password "$SCRIPT_DIR/../.env" "$PASSWORD"
