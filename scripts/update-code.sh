#!/bin/bash
# Script de mise à jour rapide du code sans rebuild complet
# Usage: ./scripts/update-code.sh

set -e

echo "🔄 Mise à jour du code LinkedInBot sans rebuild..."

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "docker-compose.pi4-standalone.yml" ]; then
    echo "❌ Erreur: Exécutez ce script depuis la racine du projet"
    exit 1
fi

# Récupérer les derniers changements
echo "📥 Pull des derniers changements Git..."
git pull

# Option 1: Si les volumes sont montés, simple restart suffit
if docker inspect linkedin-bot-api -f '{{range .Mounts}}{{if eq .Destination "/app/src"}}volume_mounted{{end}}{{end}}' | grep -q "volume_mounted"; then
    echo "✅ Volumes montés détectés - Simple restart..."
    docker-compose -f docker-compose.pi4-standalone.yml restart api bot-worker
else
    # Option 2: Copie directe dans les conteneurs
    echo "📦 Copie du code dans les conteneurs..."
    docker cp src/. linkedin-bot-api:/app/src/
    docker cp src/. linkedin-bot-worker:/app/src/

    echo "♻️  Redémarrage des services..."
    docker restart linkedin-bot-api linkedin-bot-worker
fi

echo ""
echo "✅ Mise à jour terminée !"
echo "📋 Vérification des logs:"
echo "   docker logs -f linkedin-bot-api"
echo "   docker logs -f linkedin-bot-worker"
