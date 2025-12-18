#!/bin/bash
# ==============================================================================
# SCRIPT HELPER SSL - CERTBOT WRAPPER
# ==============================================================================
# Usage: ./init-ssl.sh [DOMAIN] [EMAIL]
# Appelé par setup.sh pour transformer les certs Dummy en vrais certs Let's Encrypt
# ==============================================================================

set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
COMPOSE_FILE="${3:-docker-compose.pi4-standalone.yml}" # Fichier compose par défaut
STAGING="${4:-0}" # Mettre à 1 pour utiliser l'environnement de staging LE

if [[ -z "$DOMAIN" ]]; then
    echo "Erreur: Domaine manquant."
    echo "Usage: $0 <domain> [email] [compose_file] [staging]"
    exit 1
fi

CERT_PATH="./certbot/conf/live/$DOMAIN/fullchain.pem"
DOCKER_CMD="docker"

echo ">>> [SSL] Analyse des certificats pour $DOMAIN..."

if [[ ! -f "$CERT_PATH" ]]; then
    echo ">>> [SSL] Aucun certificat trouvé à $CERT_PATH."
    exit 1
fi

# Vérification du type de certificat (Dummy vs Real)
ISSUER=$(openssl x509 -in "$CERT_PATH" -noout -issuer)
echo ">>> [SSL] Émetteur actuel : $ISSUER"

# Si l'émetteur contient "Temporary" ou "localhost" ou "CN=$DOMAIN" (self-signed subject=issuer usually), on lance Certbot
# Note: Dummy cert subject is usually /CN=$DOMAIN/O=Temporary...
if echo "$ISSUER" | grep -qE "Temporary|localhost|O=Temporary Certificate"; then
    echo ">>> [SSL] Certificat Dummy détecté. Lancement de la procédure Let's Encrypt..."

    # CRITIQUE: Suppression des dummy certs pour éviter le dossier 'domain-0001'
    # Nginx a déjà chargé les certificats en mémoire, donc on peut supprimer les fichiers disque
    echo ">>> [SSL] Suppression des certificats temporaires pour permettre l'écrasement..."
    rm -rf "./certbot/conf/live/$DOMAIN"
    rm -rf "./certbot/conf/archive/$DOMAIN"
    rm -rf "./certbot/conf/renewal/$DOMAIN.conf"

    # Construction des arguments Certbot
    CERTBOT_ARGS="certonly --webroot -w /var/www/certbot -d $DOMAIN --agree-tos --no-eff-email --force-renewal"

    if [[ -n "$EMAIL" ]]; then
        CERTBOT_ARGS="$CERTBOT_ARGS --email $EMAIL"
    else
        CERTBOT_ARGS="$CERTBOT_ARGS --register-unsafely-without-email"
    fi

    if [[ "$STAGING" -eq 1 ]]; then
        CERTBOT_ARGS="$CERTBOT_ARGS --staging"
    fi

    echo ">>> [SSL] Exécution de Certbot via Docker..."
    # On utilise un conteneur éphémère qui partage les volumes avec Nginx
    # Nginx doit être UP pour servir le challenge ACME dans /var/www/certbot
    $DOCKER_CMD run --rm --name certbot-init \
        -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
        -v "$(pwd)/certbot/www:/var/www/certbot" \
        certbot/certbot $CERTBOT_ARGS

    if [[ $? -eq 0 ]]; then
        echo ">>> [SSL] Certificat Let's Encrypt généré avec succès !"

        # Correction des permissions pour Nginx (User 1000)
        echo ">>> [SSL] Ajustement des permissions..."
        if sudo -n true 2>/dev/null; then
            sudo chown -R 1000:1000 ./certbot
            sudo chmod -R 755 ./certbot
        else
            chown -R 1000:1000 ./certbot || echo "Warning: Impossible de changer les permissions sans sudo"
        fi

        echo ">>> [SSL] Rechargement de Nginx..."
        $DOCKER_CMD compose -f "$COMPOSE_FILE" exec nginx nginx -s reload
    else
        echo ">>> [SSL] Échec de Certbot. Vérifiez les logs et la configuration réseau (Port 80)."
        exit 1
    fi
else
    echo ">>> [SSL] Certificat valide détecté (pas de dummy). Aucune action requise."
fi
