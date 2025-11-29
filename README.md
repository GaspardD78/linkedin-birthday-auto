# 🤖 LinkedIn Birthday Bot - Guide Raspberry Pi 4

Bienvenue ! Ce guide est conçu spécifiquement pour installer le bot sur un **Raspberry Pi 4**. Il est simplifié pour les débutants et couvre l'installation complète ainsi que le dépannage.

## 📋 Prérequis

*   **Matériel** :
    *   Raspberry Pi 4 (2GB RAM minimum, 4GB+ recommandé).
    *   Carte MicroSD de **32 Go minimum** (Classe 10 recommandée pour la vitesse).
*   **Logiciel** :
    *   **Raspberry Pi OS Lite (64-bit)**.
        *   ⚠️ **Impératif** : N'utilisez pas la version 32-bit ni la version "Desktop" avec interface graphique, elles consomment trop de ressources pour ce projet.
    *   Une connexion SSH active vers votre Raspberry Pi (ou un clavier/écran branché dessus).

---

## Choisissez votre situation

*   **Cas 1 : Je commence de zéro** (Carte SD vierge ou fraîchement flashée)
    👉 [Aller à la Section 1 : Installation Complète](#1-installation-complète-de-zéro)

*   **Cas 2 : J'ai déjà essayé mais ça ne marche pas** (Erreurs, plantages, ou installation précédente ratée)
    👉 [Aller à la Section 2 : Réparation](#2-réparation-et-réinstallation-propre)

---

## 1. Installation Complète (De Zéro)

Suivez ces étapes une par une dans l'ordre exact.

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

# 2. Installer Git (nécessaire pour télécharger le code)
sudo apt install -y git

# 3. Configurer Git pour sauvegarder votre mot de passe (PAT)
# Cette commande vous évitera de devoir retaper votre clé secrète à chaque mise à jour.
git config --global credential.helper store

# 4. Télécharger ce projet
# La première fois, on vous demandera votre "Username" et votre "Password" (votre PAT GitHub).
# Grâce à la commande précédente, ils seront mémorisés pour la suite.
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git

# 5. Entrer dans le dossier du projet
cd linkedin-birthday-auto
```

### Étape C : Préparation du Système
Nous allons exécuter un script qui installe Docker et prépare le Raspberry Pi pour qu'il soit robuste.

```bash
sudo ./scripts/install_automation_pi4.sh
```

> ☕ **Pause Café** : Ce script va tout faire automatiquement : installer Docker, augmenter la mémoire d'échange (SWAP) pour éviter les crashs, et configurer le démarrage automatique.
>
> ⚠️ **TRES IMPORTANT :** Si le script vous demande de redémarrer ou finit son travail, **NE REDÉMARREZ PAS TOUT DE SUITE**. Passez directement à l'étape D.

### Étape D : Configuration
Vous devez maintenant configurer vos accès.

1.  Créez le fichier de configuration à partir du modèle :
    ```bash
    cp .env.pi4.example .env
    ```

2.  Ouvrez le fichier pour le modifier :
    ```bash
    nano .env
    ```

3.  Remplissez au minimum la ligne `LINKEDIN_AUTH_STATE` avec vos cookies LinkedIn (format JSON converti en Base64).
    *   *Astuce : Utilisez l'extension navigateur "Cookie-Editor" > Export > JSON, puis convertissez ce texte en Base64 sur un site comme base64encode.org.*

4.  Sauvegardez (`Ctrl+O` puis `Entrée`) et quittez (`Ctrl+X`).

### Étape E : Premier Déploiement (Avant Reboot)
C'est l'étape critique. Nous allons construire l'application maintenant.

```bash
./scripts/deploy_pi4_standalone.sh
```

> **Pourquoi maintenant ?** Si vous redémarrez sans faire cela, le Raspberry Pi essaiera de tout construire au démarrage, ce qui le fera "geler" pendant 20 minutes à cause de la charge processeur.
>
> *Note : Cette étape prend environ 15 à 25 minutes sur un Pi 4.*

### Étape F : Finalisation
Une fois que le script affiche que les services sont "Healthy" (Sains) ou qu'il a terminé avec succès :

```bash
sudo reboot
```

Bravo ! Au redémarrage, tout se lancera automatiquement.

---

## 2. Réparation et Réinstallation Propre

Si votre installation est "cassée", que des conteneurs ne démarrent plus, ou que vous voulez repartir sur une base saine sans reformater la carte SD.

### Étape A : Nettoyage complet
Exécutez ce script de nettoyage. Il va arrêter le bot, supprimer les conteneurs existants et nettoyer les fichiers temporaires, tout en gardant vos configurations (`.env`).

```bash
cd ~/linkedin-birthday-auto
./scripts/full_cleanup_deployment.sh
```
*Tapez "y" et Entrée si une confirmation est demandée.*

### Étape B : Relancer le déploiement
Une fois le nettoyage terminé, relancez simplement l'installation applicative :

```bash
./scripts/deploy_pi4_standalone.sh
```

---

## 🌐 Accès et Utilisation

Une fois l'installation terminée, attendez 2-3 minutes après le démarrage du Raspberry Pi.

*   **Dashboard (Tableau de bord)** :
    Ouvrez votre navigateur web et allez sur : `http://<IP_DE_VOTRE_RPI>:3000`
    *(Exemple : http://192.168.1.50:3000)*

*   **Mises à jour** :
    Pour mettre à jour le bot plus tard, lancez simplement :
    ```bash
    cd ~/linkedin-birthday-auto
    git pull
    ./scripts/easy_deploy.sh
    ```

---

## 📂 Documentation Avancée
Pour comprendre le fonctionnement interne ou les détails techniques, consultez le dossier `docs/` et notamment `docs/AUTOMATION_DEPLOYMENT_PI4.md`.
