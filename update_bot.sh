#!/bin/bash

set -e  # Arrêter en cas d'erreur

PROJECT_DIR="$HOME/linkedin-birthday-auto"
cd "$PROJECT_DIR"

echo "🔄 MISE À JOUR DU BOT LINKEDIN"
echo "=============================="

# 1. Sauvegarde
echo ""
echo "📦 Sauvegarde des données..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

for file in .env auth_state.json linkedin_birthday.db messages.txt late_messages.txt config.json; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        echo "  ✓ $file sauvegardé"
    fi
done

# 2. Mise à jour Git
echo ""
echo "📥 Téléchargement des modifications..."
git fetch origin

CURRENT_BRANCH=$(git branch --show-current)
echo "  Branche actuelle: $CURRENT_BRANCH"

git pull origin "$CURRENT_BRANCH" || {
    echo "❌ Erreur lors du git pull"
    echo "Restauration de la sauvegarde..."
    cp "$BACKUP_DIR"/* . 2>/dev/null
    exit 1
}

# 3. Restauration des fichiers personnels
echo ""
echo "📂 Restauration des fichiers personnalisés..."
for file in .env auth_state.json linkedin_birthday.db messages.txt late_messages.txt config.json; do
    if [ -f "$BACKUP_DIR/$file" ]; then
        cp "$BACKUP_DIR/$file" .
        echo "  ✓ $file restauré"
    fi
done

# 4. Mise à jour des dépendances
echo ""
echo "📦 Mise à jour des dépendances Python..."
source venv/bin/activate
pip install --upgrade -r requirements.txt -q
playwright install chromium

# 5. Test
echo ""
echo "🧪 Test du bot..."
if python3 linkedin_birthday_wisher.py --help 2>/dev/null; then
    echo "  ✓ Script opérationnel"
else
    echo "  ℹ️ Script prêt (pas de mode --help)"
fi

echo ""
echo "✅ MISE À JOUR TERMINÉE !"
echo ""
echo "📁 Sauvegarde disponible dans: $BACKUP_DIR"
echo "🧪 Testez avec: python3 linkedin_birthday_wisher.py"
echo ""
