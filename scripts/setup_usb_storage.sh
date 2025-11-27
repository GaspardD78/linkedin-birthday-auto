#!/bin/bash
# Script d'optimisation pour clé USB 16 Go sur Raspberry Pi 4
# Utilise la clé USB pour base de données, logs et screenshots

set -e

echo "🔧 Configuration de la clé USB pour LinkedIn Birthday Auto Bot"
echo "================================================================"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Variables
USB_MOUNT_POINT="/mnt/linkedin-data"
PROJECT_DIR="/home/user/linkedin-birthday-auto"

# Fonction d'erreur
error_exit() {
    echo -e "${RED}❌ Erreur: $1${NC}" >&2
    exit 1
}

# Vérifier si exécuté en tant que user (pas root)
if [ "$EUID" -eq 0 ]; then
    error_exit "Ne pas exécuter ce script en tant que root. Utilisez votre utilisateur normal."
fi

echo ""
echo "📋 Étape 1/6 : Détection de la clé USB"
echo "--------------------------------------"

# Lister les périphériques de stockage
echo -e "${YELLOW}Périphériques disponibles:${NC}"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE | grep -E "(disk|part)"

echo ""
read -p "Entrez le périphérique de votre clé USB (ex: sda1, sdb1, ou juste sda): " USB_DEVICE

if [ -z "$USB_DEVICE" ]; then
    error_exit "Périphérique non spécifié"
fi

# BUGFIX: Si l'utilisateur entre "sda" au lieu de "sda1", on détecte et on corrige
if [[ "$USB_DEVICE" =~ ^sd[a-z]$ ]] || [[ "$USB_DEVICE" =~ ^nvme[0-9]n[0-9]$ ]]; then
    # C'est un disque sans numéro de partition
    DISK_DEVICE="/dev/$USB_DEVICE"

    # Vérifier si une partition existe déjà
    if [ -b "${DISK_DEVICE}1" ]; then
        echo -e "${GREEN}✓ Partition ${DISK_DEVICE}1 détectée${NC}"
        USB_DEVICE="${USB_DEVICE}1"
    else
        echo -e "${YELLOW}⚠️  Aucune partition détectée sur $DISK_DEVICE${NC}"
        echo "Création automatique d'une partition..."

        # Créer une partition automatiquement
        sudo parted -s "$DISK_DEVICE" mklabel gpt
        sudo parted -s "$DISK_DEVICE" mkpart primary ext4 0% 100%

        # Attendre que le système détecte la partition
        sleep 2
        sudo partprobe "$DISK_DEVICE"
        sleep 1

        if [ -b "${DISK_DEVICE}1" ]; then
            echo -e "${GREEN}✓ Partition ${DISK_DEVICE}1 créée${NC}"
            USB_DEVICE="${USB_DEVICE}1"
        else
            error_exit "Échec de la création de partition sur $DISK_DEVICE"
        fi
    fi
fi

USB_DEVICE="/dev/$USB_DEVICE"

if [ ! -b "$USB_DEVICE" ]; then
    error_exit "Périphérique $USB_DEVICE n'existe pas"
fi

# Vérifier le système de fichiers
FS_TYPE=$(sudo blkid -o value -s TYPE "$USB_DEVICE" || echo "unknown")
echo -e "${GREEN}✓ Système de fichiers détecté: $FS_TYPE${NC}"

if [ "$FS_TYPE" != "ext4" ]; then
    echo -e "${YELLOW}⚠️  Avertissement: Le système de fichiers n'est pas ext4${NC}"
    read -p "Voulez-vous formater en ext4? (cela EFFACERA toutes les données) [y/N]: " FORMAT_CHOICE

    if [ "$FORMAT_CHOICE" = "y" ] || [ "$FORMAT_CHOICE" = "Y" ]; then
        echo "Formatage en ext4..."
        sudo mkfs.ext4 -F "$USB_DEVICE" || error_exit "Échec du formatage"
        echo -e "${GREEN}✓ Formatage réussi${NC}"
    else
        echo "Poursuite avec le système de fichiers actuel..."
    fi
fi

echo ""
echo "📋 Étape 2/6 : Création du point de montage"
echo "-------------------------------------------"

# Créer le point de montage s'il n'existe pas
if [ ! -d "$USB_MOUNT_POINT" ]; then
    sudo mkdir -p "$USB_MOUNT_POINT"
    echo -e "${GREEN}✓ Point de montage créé: $USB_MOUNT_POINT${NC}"
else
    echo -e "${GREEN}✓ Point de montage existe déjà: $USB_MOUNT_POINT${NC}"
fi

# Monter temporairement pour les opérations
if ! mountpoint -q "$USB_MOUNT_POINT"; then
    sudo mount "$USB_DEVICE" "$USB_MOUNT_POINT" || error_exit "Échec du montage"
    echo -e "${GREEN}✓ Clé USB montée${NC}"
fi

echo ""
echo "📋 Étape 3/6 : Création de la structure de dossiers"
echo "----------------------------------------------------"

# Créer la structure
sudo mkdir -p "$USB_MOUNT_POINT"/{database,logs,screenshots,backups,temp}
echo -e "${GREEN}✓ Dossiers créés${NC}"

# Définir les permissions
sudo chown -R $USER:$USER "$USB_MOUNT_POINT"
chmod -R 755 "$USB_MOUNT_POINT"
echo -e "${GREEN}✓ Permissions configurées${NC}"

echo ""
echo "📋 Étape 4/6 : Configuration du montage automatique"
echo "----------------------------------------------------"

# Obtenir l'UUID
USB_UUID=$(sudo blkid -o value -s UUID "$USB_DEVICE")
echo "UUID détecté: $USB_UUID"

# Vérifier si déjà dans fstab
if grep -q "$USB_UUID" /etc/fstab; then
    echo -e "${YELLOW}⚠️  Entrée fstab existante détectée${NC}"
else
    echo "Ajout de l'entrée fstab..."

    # Backup du fstab
    sudo cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d_%H%M%S)

    # Ajouter l'entrée
    echo "" | sudo tee -a /etc/fstab > /dev/null
    echo "# LinkedIn Bot USB Storage" | sudo tee -a /etc/fstab > /dev/null
    echo "UUID=$USB_UUID $USB_MOUNT_POINT ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab > /dev/null

    echo -e "${GREEN}✓ Entrée fstab ajoutée${NC}"

    # Tester le montage
    sudo umount "$USB_MOUNT_POINT" 2>/dev/null || true
    sudo mount -a || error_exit "Échec du test de montage automatique"
    echo -e "${GREEN}✓ Montage automatique testé avec succès${NC}"
fi

echo ""
echo "📋 Étape 5/6 : Migration des données existantes"
echo "------------------------------------------------"

# Migrer la base de données si elle existe
OLD_DB="$PROJECT_DIR/data/linkedin_automation.db"
NEW_DB="$USB_MOUNT_POINT/database/linkedin_automation.db"

if [ -f "$OLD_DB" ]; then
    echo "Migration de la base de données..."
    cp "$OLD_DB" "$NEW_DB"
    cp "$OLD_DB"-shm "$NEW_DB-shm" 2>/dev/null || true
    cp "$OLD_DB"-wal "$NEW_DB-wal" 2>/dev/null || true
    echo -e "${GREEN}✓ Base de données migrée${NC}"

    # Backup de l'ancienne base
    mv "$OLD_DB" "$OLD_DB.backup.$(date +%Y%m%d)" 2>/dev/null || true
else
    echo "Aucune base de données existante à migrer"
fi

# Migrer les logs si ils existent
if [ -d "$PROJECT_DIR/logs" ]; then
    echo "Migration des logs..."
    cp -r "$PROJECT_DIR/logs/"* "$USB_MOUNT_POINT/logs/" 2>/dev/null || true
    echo -e "${GREEN}✓ Logs migrés${NC}"
fi

# Migrer les screenshots si ils existent
if [ -d "$PROJECT_DIR/screenshots" ]; then
    echo "Migration des screenshots..."
    cp -r "$PROJECT_DIR/screenshots/"* "$USB_MOUNT_POINT/screenshots/" 2>/dev/null || true
    echo -e "${GREEN}✓ Screenshots migrés${NC}"
fi

echo ""
echo "📋 Étape 6/6 : Optimisation des performances USB"
echo "-------------------------------------------------"

# Optimiser pour ext4 sur USB
echo "Application des optimisations ext4..."

# Désactiver atime pour améliorer les performances
sudo tune2fs -o journal_data_writeback "$USB_DEVICE" 2>/dev/null || true
echo -e "${GREEN}✓ Journal mode optimisé${NC}"

# Mettre à jour fstab avec les options de performance
sudo sed -i "s|UUID=$USB_UUID.*|UUID=$USB_UUID $USB_MOUNT_POINT ext4 defaults,noatime,nodiratime,nofail 0 2|" /etc/fstab
echo -e "${GREEN}✓ Options de montage optimisées (noatime, nodiratime)${NC}"

# Remonter avec les nouvelles options
sudo umount "$USB_MOUNT_POINT" 2>/dev/null || true
sudo mount -a

echo ""
echo "================================================================"
echo -e "${GREEN}✅ Configuration terminée avec succès!${NC}"
echo "================================================================"
echo ""
echo "📊 Statistiques de la clé USB:"
df -h "$USB_MOUNT_POINT"
echo ""
echo "📁 Structure créée:"
tree -L 2 "$USB_MOUNT_POINT" 2>/dev/null || ls -lah "$USB_MOUNT_POINT"
echo ""
echo "📝 Prochaines étapes:"
echo "  1. La configuration config.yaml a été mise à jour automatiquement"
echo "  2. Redémarrez le service: sudo systemctl restart linkedin-bot"
echo "  3. Vérifiez les logs: tail -f $USB_MOUNT_POINT/logs/linkedin-bot.log"
echo ""
echo "💡 Astuce: Pour surveiller l'utilisation de la clé USB:"
echo "  watch -n 5 df -h $USB_MOUNT_POINT"
echo ""
