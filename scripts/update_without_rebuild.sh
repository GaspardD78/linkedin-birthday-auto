#!/bin/bash
# Script pour mettre à jour les conteneurs sans reconstruire
# Usage: ./scripts/update_without_rebuild.sh [dev|prod]

set -e

MODE=${1:-prod}
COMPOSE_FILE="docker-compose.pi4-standalone.yml"

echo "🔄 Mise à jour du LinkedIn Birthday Bot"
echo "Mode: $MODE"
echo ""

case $MODE in
  dev)
    echo "📦 Mode Développement - Montage du code source"
    echo ""
    echo "Les modifications du code seront immédiatement prises en compte."
    echo "Pour l'API, le hot-reload est activé."
    echo "Pour le worker, vous devez redémarrer le conteneur après modification."
    echo ""

    # Utiliser le fichier override pour le dev
    docker compose -f $COMPOSE_FILE -f docker-compose.dev.yml up -d api bot-worker

    echo ""
    echo "✅ Conteneurs redémarrés en mode développement"
    echo ""
    echo "Commandes utiles:"
    echo "  - Redémarrer le worker: docker restart bot-worker"
    echo "  - Voir les logs API: docker logs -f bot-api"
    echo "  - Voir les logs Worker: docker logs -f bot-worker"
    ;;

  prod)
    echo "📥 Mode Production - Téléchargement des nouvelles images"
    echo ""

    # Vérifier si on peut accéder à GHCR
    if ! docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-bot:latest &>/dev/null; then
      echo "⚠️  Impossible de télécharger les images depuis GHCR"
      echo "Les images ont-elles été construites et poussées ?"
      echo ""
      echo "Pour construire et pousser les images:"
      echo "  1. Pousser le code sur GitHub"
      echo "  2. Attendre la fin du workflow GitHub Actions"
      echo "  3. Relancer ce script"
      exit 1
    fi

    # Pull les nouvelles images
    echo "Téléchargement des images..."
    docker compose -f $COMPOSE_FILE pull api bot-worker

    # Redémarrer les services
    echo ""
    echo "Redémarrage des conteneurs..."
    docker compose -f $COMPOSE_FILE up -d api bot-worker

    echo ""
    echo "✅ Conteneurs mis à jour et redémarrés"
    echo ""
    echo "Vérification du déploiement:"
    docker compose -f $COMPOSE_FILE ps api bot-worker
    ;;

  *)
    echo "❌ Mode invalide: $MODE"
    echo "Usage: $0 [dev|prod]"
    echo ""
    echo "  dev  - Monte le code source pour développement local"
    echo "  prod - Télécharge les nouvelles images depuis GHCR"
    exit 1
    ;;
esac

echo ""
echo "📊 Pour voir les logs en temps réel:"
echo "  docker logs -f bot-worker"
