# 🤖 LinkedIn Birthday Bot - Guide Raspberry Pi 4

Bienvenue ! Ce guide est conçu spécifiquement pour installer le bot sur un **Raspberry Pi 4**. Il est simplifié pour les débutants et utilise un script d'installation automatique.

## 📋 Prérequis

*   **Matériel** :
    *   Raspberry Pi 4 (2GB RAM minimum, 4GB+ recommandé).
    *   Carte MicroSD de **32 Go minimum** (Classe 10 recommandée pour la vitesse).
*   **Logiciel** :
    *   **Raspberry Pi OS Lite (64-bit)**.
        *   ⚠️ **Impératif** : N'utilisez pas la version 32-bit ni la version "Desktop" avec interface graphique.
    *   Une connexion SSH active vers votre Raspberry Pi (ou un clavier/écran branché dessus).

---

## Choisissez votre situation

*   **Cas 1 : Je commence de zéro** (Carte SD vierge ou fraîchement flashée)
    👉 [Aller à la Section 1 : Installation Automatique](#1-installation-automatique-de-zéro)

*   **Cas 2 : J'ai déjà essayé mais ça ne marche pas** (Erreurs, plantages, ou installation précédente ratée)
    👉 [Aller à la Section 2 : Réparation](#2-réparation-et-réinstallation-propre)

---

## 1. Installation Automatique (De Zéro)

Suivez ces étapes une par une.

### Étape A : Préparation de la carte SD (Sur votre ordinateur)
1.  Téléchargez et installez [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2.  **OS** : Choisissez `Raspberry Pi OS (other)` -> `Raspberry Pi OS Lite (64-bit)`.
3.  **Stockage** : Sélectionnez votre carte SD.
4.  **Configuration (Roue crantée ⚙️)** :
    *   Cochez "Enable SSH" -> "Use password authentication".
    *   Définissez un nom d'utilisateur (ex: `pi`) et un mot de passe.
    *   Configurez votre WiFi si vous n'utilisez pas de câble Ethernet.
5.  Cliquez sur **WRITE**. Une fois fini, insérez la carte dans le RPI4 et allumez-le.

### Étape B : Récupération du projet (Sur le Raspberry Pi)
Connectez-vous en SSH à votre RPI4, puis lancez ces commandes :

```bash
# 1. Mettre à jour la liste des paquets système
sudo apt update

# 2. Installer Git
sudo apt install -y git

# 3. Configurer Git pour sauvegarder votre mot de passe (PAT)
# Cette commande vous évitera de devoir retaper votre clé secrète à chaque mise à jour.
git config --global credential.helper store

# 4. Télécharger le projet
# La première fois, on vous demandera votre "Username" et votre "Password" (votre PAT GitHub).
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git

# 5. Entrer dans le dossier du projet
cd linkedin-birthday-auto
```

### Étape C : Lancement de l'installation
Nous avons un script "tout-en-un" qui va installer Docker, configurer vos accès et lancer le bot.

```bash
./setup.sh
```

**Laissez-vous guider par les questions à l'écran.** Le script va :
1.  Installer Docker et les outils nécessaires (répondez 'y' si demandé).
2.  Vous aider à configurer vos cookies LinkedIn (`auth_state.json`) et vos réglages (`.env`).
    *   *Astuce : Préparez vos cookies LinkedIn (exportés via l'extension Cookie-Editor) avant de lancer le script.*
3.  Construire et lancer l'application (cela prend 15-20 minutes).
4.  Configurer le démarrage automatique au boot (Systemd).

### Étape D : Finalisation
Une fois le script terminé avec le message "INSTALLATION RÉUSSIE", redémarrez votre Pi pour finaliser les permissions :

```bash
sudo reboot
```

---

## 2. Réparation et Réinstallation Propre

Si votre installation est "cassée", que des conteneurs ne démarrent plus, ou que vous voulez repartir sur une base saine.

### Étape A : Nettoyage complet
Exécutez ce script de nettoyage. Il va tout supprimer (conteneurs, images) sauf vos configurations.

```bash
cd ~/linkedin-birthday-auto
./scripts/full_cleanup_deployment.sh
```
*Tapez "y" et Entrée si une confirmation est demandée.*

### Étape B : Relancer l'installation
Une fois propre, relancez simplement le script d'installation :

```bash
./setup.sh
```

---

## 🛠️ Installation Manuelle (Experts)

Si vous préférez contrôler chaque étape du déploiement (sans utiliser le script tout-en-un), une procédure manuelle détaillée est disponible.

👉 **[Voir le guide de déploiement manuel (AUTOMATION_DEPLOYMENT_PI4.md)](docs/AUTOMATION_DEPLOYMENT_PI4.md)**

---

## 🌐 Accès et Utilisation

Une fois l'installation terminée, attendez 2-3 minutes après le démarrage du Raspberry Pi.

*   **Dashboard (Tableau de bord)** :
    Ouvrez votre navigateur web et allez sur : `http://<IP_DE_VOTRE_RPI>:3000`
    *(Exemple : http://192.168.1.50:3000)*

*   **Mises à jour** :
    Pour mettre à jour le bot plus tard :
    ```bash
    cd ~/linkedin-birthday-auto
    git pull
    ./setup.sh
    ```
