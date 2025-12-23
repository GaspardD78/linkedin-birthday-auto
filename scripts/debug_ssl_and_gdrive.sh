#!/bin/bash
# scripts/debug_ssl_and_gdrive.sh
# Diagnostic pour SSL (SnakeOil vs Let's Encrypt) et Google Drive (Backup)

DOMAIN="gaspardanoukolivier.freeboxos.fr"
CERT_PATH="certbot/conf/live/$DOMAIN/fullchain.pem"
NGINX_CONF="deployment/nginx/linkedin-bot.conf"

echo "==================================================="
echo "🔎 DIAGNOSTIC SSL: $DOMAIN"
echo "==================================================="

if [ -f "$CERT_PATH" ]; then
    echo "✅ Fichier certificat trouvé: $CERT_PATH"
    echo "📜 Émetteur (Issuer):"
    openssl x509 -in "$CERT_PATH" -noout -issuer
else
    echo "❌ Fichier certificat NON trouvé à: $CERT_PATH"
    echo "⚠️ Contenu de certbot/conf/live/:"
    ls -R certbot/conf/live/ 2>/dev/null
fi

echo ""
echo "==================================================="
echo "🔎 DIAGNOSTIC CONFIG NGINX"
echo "==================================================="

if [ -f "$NGINX_CONF" ]; then
    echo "✅ Fichier config trouvé: $NGINX_CONF"
    echo "📜 Lignes SSL:"
    grep "ssl_certificate" "$NGINX_CONF"
else
    echo "❌ Fichier config NON trouvé: $NGINX_CONF"
    echo "⚠️ Note: Si ce fichier manque, Nginx utilise peut-être une config par défaut ou un montage vide."
fi

echo ""
echo "==================================================="
echo "🔎 DIAGNOSTIC LOGS (Drive/Error)"
echo "==================================================="

echo "📂 Recherche 'Drive' ou 'Error' dans logs/ (Dernières 50 lignes)..."
grep -E "Drive|Error" logs/*.log | tail -n 50 || echo "Aucune erreur trouvée."

echo ""
echo "==================================================="
echo "🛠 ACTION SUGGÉRÉE (RECREATION NGINX)"
echo "==================================================="
echo "docker compose -f docker-compose.yml up -d --force-recreate nginx"
