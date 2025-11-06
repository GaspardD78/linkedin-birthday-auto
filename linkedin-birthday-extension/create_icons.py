#!/usr/bin/env python3
"""
Générateur d'icônes pour l'extension Chrome
Crée des icônes simples avec un emoji
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow n'est pas installé")
    print("Installation : pip install Pillow")

import os

def create_icon(size, emoji, filename):
    """Crée une icône avec un emoji"""
    if not PIL_AVAILABLE:
        return False
    
    # Créer une image avec fond bleu LinkedIn
    img = Image.new('RGB', (size, size), color='#0077B5')
    draw = ImageDraw.Draw(img)
    
    # Essayer de charger une police avec support emoji
    try:
        # Sur Windows
        font = ImageFont.truetype("seguiemj.ttf", int(size * 0.6))
    except:
        try:
            # Sur Mac
            font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", int(size * 0.6))
        except:
            try:
                # Sur Linux
                font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", int(size * 0.6))
            except:
                # Fallback: police par défaut
                font = ImageFont.load_default()
    
    # Calculer la position pour centrer l'emoji
    bbox = draw.textbbox((0, 0), emoji, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Dessiner l'emoji
    draw.text((x, y), emoji, font=font, fill='white')
    
    # Sauvegarder
    img.save(filename)
    print(f"✅ {filename} créé ({size}x{size})")
    return True

def create_simple_icons():
    """Crée des icônes simples sans Pillow"""
    print("📦 Création d'icônes de base...")
    
    # Créer le dossier icons s'il n'existe pas
    icons_dir = "icons"
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
    
    # Créer des images PNG de couleur unie (placeholder)
    # En pratique, utilisez un outil en ligne comme favicon.io
    print("\n💡 Pour créer de vraies icônes :")
    print("1. Allez sur : https://favicon.io/favicon-generator/")
    print("2. Texte : 🎉 ou LB (LinkedIn Birthday)")
    print("3. Background : #0077B5")
    print("4. Téléchargez et extrayez dans le dossier 'icons'")
    print("5. Renommez les fichiers :")
    print("   - favicon-16x16.png → icon16.png")
    print("   - favicon-48x48.png → icon48.png")
    print("   - android-chrome-192x192.png → icon128.png")

def main():
    print("=" * 60)
    print("🎨 GÉNÉRATEUR D'ICÔNES - LinkedIn Birthday Bot")
    print("=" * 60)
    
    # Créer le dossier icons
    icons_dir = "icons"
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
        print(f"✅ Dossier '{icons_dir}' créé")
    
    if PIL_AVAILABLE:
        print("\n🎨 Création des icônes avec Pillow...")
        emoji = "🎂"  # Ou 🎉, 🎈, 🎁
        
        success = True
        success &= create_icon(16, emoji, os.path.join(icons_dir, "icon16.png"))
        success &= create_icon(48, emoji, os.path.join(icons_dir, "icon48.png"))
        success &= create_icon(128, emoji, os.path.join(icons_dir, "icon128.png"))
        
        if success:
            print("\n✅ Toutes les icônes ont été créées !")
        else:
            print("\n⚠️  Certaines icônes n'ont pas pu être créées")
    else:
        create_simple_icons()
    
    print("\n" + "=" * 60)
    print("📁 Emplacement : " + os.path.abspath(icons_dir))
    print("=" * 60)

if __name__ == "__main__":
    main()
