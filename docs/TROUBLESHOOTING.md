# 🛠️ TROUBLESHOOTING GUIDE (RPi4)

Ce guide couvre les problèmes fréquents rencontrés lors du déploiement sur Raspberry Pi 4.

---

## 1. Problèmes de Démarrage / Installation

### Erreur : `OOM Killed` ou Crash aléatoire pendant le build
*   **Cause :** Le Raspberry Pi 4 manque de RAM pour compiler certains paquets ou lancer tous les conteneurs simultanément.
*   **Solution :**
    1.  Vérifiez que le Swap est actif : `free -h`. Vous devriez avoir au moins 2GB de Swap.
    2.  Si le Swap est insuffisant, relancez `./setup.sh` et acceptez la création du Swap.
    3.  Assurez-vous que ZRAM est actif : `zramctl`.

### Erreur : `network linkedin-network not found`
*   **Cause :** Docker n'a pas créé le réseau correctement ou un conflit existe.
*   **Solution :** `docker network prune -f` puis relancez `docker compose -f docker-compose.pi4-standalone.yml up -d`.

### Le script `setup.sh` échoue sur la génération SSL
*   **Cause :** `openssl` n'est pas installé ou erreur de permissions.
*   **Solution :** `sudo apt install openssl`. Le script utilise des certificats auto-signés par défaut pour garantir le démarrage immédiat.

---

## 2. Problèmes de Connexion / Réseau

### "DNS lookup failed" ou Timeouts dans les logs du bot
*   **Cause :** Les DNS de la box FAI (Freebox, etc.) bloquent parfois les résolutions fréquentes ou ne gèrent pas bien Docker.
*   **Solution :** `setup.sh` configure désormais Docker pour utiliser `1.1.1.1` et `8.8.8.8`. Vérifiez `/etc/docker/daemon.json`.

### Impossible d'accéder au Dashboard (`ERR_CONNECTION_REFUSED`)
*   **Cause :** Le conteneur `dashboard` (Next.js) est lent à démarrer sur RPi4 (30-60s).
*   **Solution :**
    1.  Attendez 1 minute après le `up -d`.
    2.  Vérifiez les logs : `docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard`.
    3.  Si le log indique "Ready on http://localhost:3000", c'est bon.

---

## 3. Problèmes de Bot (LinkedIn)

### Erreur : `SessionExpiredError` ou boucle de login
*   **Cause :** Les cookies dans `auth_state.json` sont invalides ou expirés.
*   **Solution :**
    1.  Supprimez le fichier obsolète : `rm data/auth_state.json`.
    2.  Connectez-vous au Dashboard.
    3.  Allez dans "Comptes" et uploadez un nouveau fichier de cookies (exporté via EditThisCookie).

### Le bot ne trouve pas le bouton "Message"
*   **Cause :** LinkedIn a changé son interface (A/B testing) ou le contact est hors réseau.
*   **Solution :** Le bot utilise des sélecteurs heuristiques robustes. Vérifiez les logs pour voir si un bouton "Se connecter" a été détecté (auquel cas le bot ignore le contact par sécurité).

### Base de données verrouillée (`database is locked`)
*   **Cause :** Concurrence d'accès sur le fichier SQLite (API vs Worker).
*   **Solution :** L'architecture V3.1 utilise le mode WAL pour mitiger cela. Si cela persiste, redémarrez les services : `docker compose -f docker-compose.pi4-standalone.yml restart`.

---

## 4. Maintenance

### Nettoyer l'espace disque (Carte SD pleine)
```bash
# Nettoyage prudent (images non utilisées)
docker image prune -a

# Nettoyage radical (tout ce qui n'est pas lancé)
docker system prune -a --volumes
```

### Voir les logs en temps réel
```bash
# Tous les services
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Juste le bot
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker --tail=50
```
