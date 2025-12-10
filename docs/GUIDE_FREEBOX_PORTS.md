# 🌐 Guide : Ouvrir les Ports sur Votre Freebox

Ce guide vous explique **pas à pas** comment ouvrir les ports 80 et 443 sur votre Freebox pour permettre l'accès HTTPS à votre bot LinkedIn depuis Internet.

⏱️ **Durée** : 5-10 minutes
🎯 **Difficulté** : Facile
🔧 **Prérequis** : Mot de passe de votre Freebox

---

## 📋 Table des Matières

1. [Pourquoi ouvrir ces ports ?](#pourquoi-ouvrir-ces-ports)
2. [Étape 1 : Accéder à l'interface Freebox](#étape-1--accéder-à-linterface-freebox)
3. [Étape 2 : Trouver l'IP de votre Raspberry Pi](#étape-2--trouver-lip-de-votre-raspberry-pi)
4. [Étape 3 : Créer les redirections de ports](#étape-3--créer-les-redirections-de-ports)
5. [Étape 4 : Vérifier que ça fonctionne](#étape-4--vérifier-que-ça-fonctionne)
6. [Dépannage](#dépannage)

---

## 🤔 Pourquoi Ouvrir Ces Ports ?

### Port 80 (HTTP)
**Rôle** : Permet à Let's Encrypt de vérifier que vous possédez bien le domaine.
**Utilisé pour** : Obtenir et renouveler automatiquement le certificat SSL.
**Sécurité** : Nginx redirigera automatiquement vers HTTPS (port 443).

### Port 443 (HTTPS)
**Rôle** : Permet l'accès sécurisé (chiffré) à votre dashboard depuis Internet.
**Utilisé pour** : Accéder à votre bot LinkedIn en HTTPS.
**Sécurité** : Tout le trafic est chiffré avec SSL/TLS.

> ⚠️ **Important** : Sans ces ports ouverts, vous ne pourrez accéder à votre bot que depuis votre réseau local (WiFi Freebox uniquement).

---

## 📱 Étape 1 : Accéder à l'Interface Freebox

### 1.1 Ouvrir l'interface web

1. Ouvrez votre navigateur (Chrome, Firefox, Safari, etc.)
2. Dans la barre d'adresse, tapez : **`http://mafreebox.freebox.fr`**
3. Appuyez sur **Entrée**

> 💡 **Astuce** : Vous devez être connecté au WiFi de votre Freebox pour accéder à cette page.

### 1.2 Se connecter

1. Cliquez sur **« Se connecter »** (bouton en haut à droite)
2. Entrez le **mot de passe de votre Freebox**

> 🔑 **Mot de passe oublié ?**
> - Regardez sous votre Freebox (étiquette)
> - Ou appuyez sur le bouton de la Freebox quand l'écran demande l'autorisation

---

## 🔍 Étape 2 : Trouver l'IP de Votre Raspberry Pi

Avant de configurer les redirections, vous devez connaître l'adresse IP locale de votre Raspberry Pi sur le réseau Freebox.

### Méthode 1 : Via l'interface Freebox (Recommandé)

1. Dans l'interface Freebox, cliquez sur **« Périphériques réseau »** (icône ordinateur en haut)
2. Vous verrez la liste de tous les appareils connectés
3. Cherchez votre Raspberry Pi dans la liste (nom possible : `raspberrypi`, `pi`, `linuxbot`, etc.)
4. **Notez son adresse IP** (format : `192.168.X.X`)

**Exemple** :
```
Nom : raspberrypi
IP : 192.168.1.42
Type : Ethernet ou WiFi
```

> 💡 **Astuce** : Votre Raspberry Pi peut avoir l'icône d'un ordinateur ou d'un serveur.

### Méthode 2 : Depuis le Raspberry Pi (SSH)

Si vous êtes connecté en SSH au Raspberry Pi, tapez cette commande :

```bash
hostname -I
```

**Résultat attendu** :
```
192.168.1.42
```

> ✅ L'IP doit commencer par `192.168.` ou `10.0.`

### 2.3 Fixer l'IP (IMPORTANT)

Pour éviter que l'IP change, **vous devez la rendre statique** :

1. Dans l'interface Freebox, allez dans **« Périphériques réseau »**
2. Cliquez sur votre Raspberry Pi
3. Activez **« Bail DHCP statique »** ou **« IP fixe »**
4. Cliquez sur **« Enregistrer »**

> ⚠️ **Très important** : Si vous sautez cette étape, l'IP du Raspberry Pi peut changer et les redirections de ports ne fonctionneront plus !

---

## ⚙️ Étape 3 : Créer les Redirections de Ports

Maintenant que vous avez l'IP du Raspberry Pi, vous allez créer 2 redirections de ports.

### 3.1 Accéder aux paramètres de redirections

1. Dans l'interface Freebox, cliquez sur **« Paramètres de la Freebox »** (icône engrenage)
2. Activez le **« Mode avancé »** (bouton en haut à droite)
3. Dans le menu de gauche, cliquez sur **« Gestion des ports »**
4. Puis cliquez sur **« Redirections »**

### 3.2 Créer la redirection pour le port 80 (HTTP)

1. Cliquez sur **« Ajouter une redirection »** (bouton bleu)
2. Remplissez le formulaire comme suit :

| Champ | Valeur |
|-------|--------|
| **Type** | TCP |
| **Port de début** | 80 |
| **Port de fin** | 80 |
| **Port de destination** | 80 |
| **IP de destination** | `192.168.X.X` (l'IP de votre Raspberry Pi) |
| **Commentaire** | `LinkedIn Bot HTTP` |

3. Cliquez sur **« Enregistrer »**

> ✅ Vous devriez voir la ligne apparaître dans la liste des redirections.

### 3.3 Créer la redirection pour le port 443 (HTTPS)

1. Cliquez à nouveau sur **« Ajouter une redirection »**
2. Remplissez le formulaire comme suit :

| Champ | Valeur |
|-------|--------|
| **Type** | TCP |
| **Port de début** | 443 |
| **Port de fin** | 443 |
| **Port de destination** | 443 |
| **IP de destination** | `192.168.X.X` (la MÊME IP que pour le port 80) |
| **Commentaire** | `LinkedIn Bot HTTPS` |

3. Cliquez sur **« Enregistrer »**

### 3.4 Vérification visuelle

À ce stade, vous devriez avoir **2 redirections** dans la liste :

| Protocole | Port externe | IP destination | Port destination | Commentaire |
|-----------|--------------|----------------|------------------|-------------|
| TCP | 80 | 192.168.X.X | 80 | LinkedIn Bot HTTP |
| TCP | 443 | 192.168.X.X | 443 | LinkedIn Bot HTTPS |

> ⚠️ Vérifiez bien que l'**IP de destination est la même** pour les 2 redirections !

---

## ✅ Étape 4 : Vérifier Que Ça Fonctionne

### 4.1 Tester depuis Internet

Pour vérifier que les ports sont bien ouverts, utilisez un outil en ligne :

1. Allez sur : **https://www.canyouseeme.org/**
2. Dans "Port to Check", entrez : **80**
3. Cliquez sur **« Check Port »**

**Résultat attendu** :
```
✅ Success: I can see your service on [VOTRE_IP] on port 80
```

4. Refaites le test avec le port **443**

**Résultat attendu** :
```
✅ Success: I can see your service on [VOTRE_IP] on port 443
```

### 4.2 Vérifier que Nginx répond

Si Nginx est installé et démarré sur votre Raspberry Pi, testez depuis votre navigateur :

1. Allez sur : **`http://VOTRE_IP_PUBLIQUE`**
2. Vous devriez voir la page d'accueil Nginx ou votre dashboard

> 💡 **Trouver votre IP publique** : Allez sur https://whatismyip.com/ ou tapez "quelle est mon IP" dans Google.

### 4.3 Tester avec votre nom de domaine

Si vous avez configuré un nom de domaine :

1. Allez sur : **`http://bot.votre-domaine.com`**
2. Vous devriez voir votre dashboard

> ⚠️ Attendez 5-10 minutes si vous venez de configurer le DNS (propagation).

---

## 🛠️ Dépannage

### ❌ Problème : "Port is closed" sur canyouseeme.org

**Causes possibles** :

1. **Les redirections ne sont pas enregistrées**
   - Retournez dans l'interface Freebox
   - Vérifiez que les 2 redirections sont bien présentes
   - Essayez de les supprimer et les recréer

2. **L'IP du Raspberry Pi est incorrecte**
   - Vérifiez l'IP : `hostname -I` depuis le Raspberry Pi
   - Comparez avec l'IP dans les redirections Freebox
   - Si elles diffèrent, mettez à jour les redirections

3. **Nginx n'est pas démarré**
   - Connectez-vous en SSH au Raspberry Pi
   - Tapez : `sudo systemctl status nginx`
   - Si "inactive", démarrez-le : `sudo systemctl start nginx`

4. **Firewall sur le Raspberry Pi**
   - Désactivez temporairement le firewall : `sudo ufw disable`
   - Retestez les ports
   - Si ça marche, configurez ufw pour autoriser 80 et 443

### ❌ Problème : "Connection refused" ou "Page introuvable"

**Causes possibles** :

1. **Nginx n'écoute pas sur le bon port**
   - Vérifiez : `sudo netstat -tlnp | grep nginx`
   - Vous devriez voir `:80` et `:443` dans la liste

2. **La configuration Nginx est incorrecte**
   - Testez la config : `sudo nginx -t`
   - Corrigez les erreurs affichées
   - Rechargez : `sudo systemctl reload nginx`

3. **Le DNS ne pointe pas vers votre IP**
   - Vérifiez avec : `nslookup bot.votre-domaine.com`
   - L'IP doit correspondre à votre IP publique Freebox

### ❌ Problème : L'IP du Raspberry Pi change souvent

**Solution** : Fixer l'IP avec un bail DHCP statique (voir Étape 2.3)

1. Interface Freebox → Périphériques réseau
2. Cliquez sur votre Raspberry Pi
3. Activez **« Bail DHCP statique »**
4. Enregistrez

### ❌ Problème : "Port 80 already in use" lors de l'installation de Nginx

**Cause** : Un autre service utilise déjà le port 80.

**Solution** :
```bash
# Trouver quel processus utilise le port 80
sudo netstat -tlnp | grep :80

# Arrêter le processus (remplacez PID par le numéro affiché)
sudo kill PID

# Ou arrêter Apache si installé
sudo systemctl stop apache2
sudo systemctl disable apache2
```

---

## 📞 Besoin d'Aide ?

### Ressources utiles

- **Documentation Freebox** : https://www.free.fr/assistance/
- **Support Free** : 3244 (depuis un poste fixe)
- **Forum Freebox** : https://www.universfreebox.com/

### Informations à fournir si vous demandez de l'aide

1. Modèle de votre Freebox (Revolution, Delta, Pop, etc.)
2. IP locale du Raspberry Pi : `hostname -I`
3. IP publique Freebox : https://whatismyip.com/
4. Résultat de : `sudo systemctl status nginx`
5. Résultat de : `sudo netstat -tlnp | grep :80`
6. Capture d'écran de vos redirections Freebox

---

## 🎯 Récapitulatif

Une fois les ports ouverts, vous pourrez :

✅ Obtenir un certificat SSL Let's Encrypt
✅ Accéder à votre dashboard en HTTPS depuis n'importe où
✅ Bénéficier du renouvellement automatique du certificat
✅ Avoir une connexion sécurisée et chiffrée

**Prochaine étape** : Exécutez le script d'installation de sécurité :
```bash
./scripts/setup_security.sh
```

---

**Fait avec ❤️ pour les utilisateurs non-techniques**
*Si ce guide vous a aidé, n'hésitez pas à laisser une étoile ⭐ sur le repo !*
