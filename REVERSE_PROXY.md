# Configuration du Reverse Proxy Synology pour LinkedIn Dashboard

Pour accéder à votre dashboard depuis l'extérieur de manière sécurisée, il est recommandé d'utiliser le Reverse Proxy intégré à votre NAS Synology.

## Prérequis

1.  Votre Raspberry Pi et votre NAS Synology doivent être sur le même réseau local.
2.  L'application Dashboard doit tourner sur le Raspberry Pi (port 5000 par défaut).
3.  Vous devez avoir un nom de domaine DDNS (ex: `mon-nas.synology.me`).

## ⚠️ Point Important : Choix du nom de domaine

**Si vous utilisez un nom de domaine Synology DDNS (ex: `gaspard.synology.me`), vous ne pouvez PAS utiliser un autre domaine principal comme `linkedin.synology.me`.**

Vous devez utiliser soit :
1.  **Votre domaine DDNS principal avec un port différent** (ex: `gaspard.synology.me` sur le port 8080).
2.  **Un sous-domaine de votre DDNS** (ex: `linkedin.gaspard.synology.me`), MAIS cela nécessite un certificat Wildcard (`*.gaspard.synology.me`).

### Erreur fréquente à éviter
❌ **Ne pas utiliser** : `linkedin.synology.me` (ce domaine ne vous appartient pas !)
✅ **Utiliser** : `linkedin.gaspard.synology.me` (si votre DDNS est `gaspard.synology.me`)

## Étapes de configuration

1.  **Connectez-vous à DSM** sur votre Synology.
2.  Allez dans **Panneau de configuration** > **Portail de connexion** > **Avancé**.
3.  Cliquez sur **Proxy inversé**.
4.  Cliquez sur **Créer**.

## Paramètres de la règle

### Général

*   **Description** : LinkedIn Dashboard
*   **Protocole (Source)** : HTTPS
*   **Nom d'hôte (Source)** :
    *   Si vous avez un certificat Wildcard : `linkedin.votre-ddns.synology.me`
    *   Sinon, utilisez simplement votre DDNS : `votre-ddns.synology.me`
*   **Port (Source)** : 9000 (ou tout autre port libre comme 8080, 8443)
    *   *Attention : N'utilisez pas 5000 (DSM HTTP) ou 5001 (DSM HTTPS) !*
*   **Activer HSTS** : Coché (recommandé pour la sécurité)

### Destination

*   **Protocole** : HTTP
*   **Nom d'hôte** : `IP_DU_RASPBERRY_PI` (ex: `192.168.1.50`)
*   **Port** : `5000`

### En-têtes personnalisés

Allez dans l'onglet **En-tête personnalisé** :
*   Cliquez sur **Créer** > **WebSocket** (Cela ajoute automatiquement les en-têtes Upgrade et Connection, utiles pour les mises à jour en temps réel si ajoutées plus tard).

## Certificat SSL

Pour que la connexion soit sécurisée (HTTPS) sans alerte de sécurité :

1.  Allez dans **Panneau de configuration** > **Sécurité** > **Certificat**.
2.  Vérifiez que vous avez un certificat pour votre domaine DDNS (`votre-ddns.synology.me`).
    *   *Astuce : Les certificats Let's Encrypt par défaut sur Synology couvrent souvent `*.votre-ddns.synology.me`.*
3.  Cliquez sur **Paramètres** (ou "Configurer" selon la version DSM).
4.  Trouvez votre règle de proxy inversé (celle que vous venez de créer) et associez-y le certificat de votre DDNS.

## Accès

Vous pouvez maintenant accéder à votre dashboard via :
`https://linkedin.votre-ddns.synology.me:9000`
(Remplacez 9000 par le port que vous avez choisi).

La connexion est chiffrée de bout en bout entre votre navigateur et le NAS, puis relayée en interne vers le Raspberry Pi.
