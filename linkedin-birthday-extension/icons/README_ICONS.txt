# Icônes de l'extension

Pour créer les icônes, vous avez 3 options :

## Option 1 : Générateur en ligne (RECOMMANDÉ)

1. Allez sur : https://favicon.io/favicon-generator/
2. Paramètres :
   - Texte : 🎉 (ou LB ou 🎂)
   - Background : #0077B5 (bleu LinkedIn)
   - Font : Arial Bold
3. Cliquez sur "Download"
4. Extrayez le ZIP
5. Renommez et copiez ici :
   - `favicon-16x16.png` → `icon16.png`
   - `favicon-32x32.png` → `icon48.png` (ou utilisez le 48x48 s'il existe)
   - `android-chrome-192x192.png` → `icon128.png`

## Option 2 : Script Python

Lancez le script (si Pillow est installé) :
```bash
python create_icons.py
```

## Option 3 : Images existantes

Si vous avez déjà des images PNG :
1. Nommez-les : `icon16.png`, `icon48.png`, `icon128.png`
2. Copiez-les dans ce dossier

---

**Dimensions requises :**
- icon16.png : 16x16 pixels
- icon48.png : 48x48 pixels
- icon128.png : 128x128 pixels

**Note :** Sans ces icônes, l'extension fonctionnera quand même, mais n'aura pas d'icône visible.
