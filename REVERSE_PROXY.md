# Configuration du Reverse Proxy Synology pour LinkedIn Dashboard

Pour accéder à votre dashboard depuis l'extérieur de manière sécurisée, il est recommandé d'utiliser le Reverse Proxy intégré à votre NAS Synology.

## Prérequis

1.  Votre Raspberry Pi et votre NAS Synology doivent être sur le même réseau local.
2.  L'application Dashboard doit tourner sur le Raspberry Pi (port 5000 par défaut).
3.  Vous devez avoir un nom de domaine (ex: `mon-nas.synology.me` ou un domaine personnalisé).

## Étapes de configuration

1.  **Connectez-vous à DSM** sur votre Synology.
2.  Allez dans **Panneau de configuration** > **Portail de connexion** > **Avancé**.
3.  Cliquez sur **Proxy inversé**.
4.  Cliquez sur **Créer**.

## Paramètres de la règle

### Général

*   **Description** : LinkedIn Dashboard
*   **Protocole (Source)** : HTTPS
*   **Nom d'hôte (Source)** : `linkedin.votre-domaine.com` (ou juste `votre-domaine.com` si vous utilisez un port différent)
*   **Port (Source)** : 443 (ou un autre port personnalisé externe, ex: 8443)
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
2.  Si vous utilisez un domaine Synology (`.synology.me`) ou Let's Encrypt, assurez-vous que votre certificat couvre le sous-domaine `linkedin.votre-domaine.com`.
3.  Cliquez sur **Paramètres** (ou "Configurer" selon la version DSM).
4.  Trouvez votre règle de proxy inversé (`linkedin.votre-domaine.com`) et associez-y le bon certificat.

## Accès

Vous pouvez maintenant accéder à votre dashboard via :
`https://linkedin.votre-domaine.com`

La connexion est chiffrée de bout en bout entre votre navigateur et le NAS, puis relayée en interne vers le Raspberry Pi.
