# LinkedIn Birthday Wisher Bot

Ce projet contient un script d'automatisation Python conçu pour souhaiter automatiquement un joyeux anniversaire à vos contacts de premier niveau sur LinkedIn. Le bot est conçu pour être discret et imiter le comportement humain afin de minimiser les risques de détection.

## Fonctionnalités

- **Connexion Sécurisée** : Utilise les secrets de GitHub pour stocker vos identifiants en toute sécurité, sans jamais les écrire en clair dans le code.
- **Comportement Humain** : Le script intègre des délais aléatoires et simule la frappe au clavier pour paraître moins robotique.
- **Exécution Programmée** : Grâce à GitHub Actions, le script s'exécute automatiquement chaque matin à une heure variable entre 8h00 et 10h00 (UTC).
- **Messages Personnalisables** : Vous pouvez facilement modifier la liste des messages d'anniversaire.
- **Notifications d'Erreur** : Si le script échoue, GitHub Actions vous enverra automatiquement un e-mail et enregistrera une capture d'écran du problème.

### 🚀 Nouvelles fonctionnalités Phase 1

- **Base de Données SQLite** : Stockage persistant de tous les messages, contacts, visites et erreurs avec mode WAL pour performances optimales
- **Dashboard Web** : Interface Flask avec statistiques en temps réel, graphiques, et historique complet
- **Détection de Changements LinkedIn** : Système de validation des sélecteurs CSS pour détecter automatiquement les changements de structure DOM
- **Thread-Safe** : Architecture robuste avec singleton thread-safe et retry logic
- **Tests Automatisés** : Suite de tests complète exécutée via GitHub Actions
- **Métriques & Analytics** : Suivi détaillé des performances avec export JSON

📚 **Documentation complète** : Voir [PHASE1.md](PHASE1.md), [DEPLOYMENT.md](DEPLOYMENT.md), et [BUGFIXES.md](BUGFIXES.md)

## 🧪 Tests

**Les tests sont exécutés uniquement via GitHub Actions.**

Pour lancer les tests :
1. Allez sur **Actions** → **Test Suite - Phase 1**
2. Cliquez sur **Run workflow**
3. Consultez les résultats et téléchargez les artifacts

Les tests s'exécutent aussi automatiquement sur chaque push/PR vers main/master.

## Configuration

Suivez ces étapes pour configurer et activer le bot.

### 1. Stocker vos identifiants LinkedIn en toute sécurité

Pour que le script puisse se connecter à votre compte, vous devez stocker votre e-mail et votre mot de passe LinkedIn en tant que "secrets" dans votre dépôt GitHub. C'est la méthode la plus sûre, car ils sont chiffrés et ne seront jamais visibles publiquement.

1.  Dans votre dépôt GitHub, allez dans **Settings** > **Secrets and variables** > **Actions**.
2.  Cliquez sur **New repository secret**.
3.  Créez un premier secret :
    *   **Name** : `LINKEDIN_EMAIL`
    *   **Secret** : Entrez votre adresse e-mail LinkedIn.
4.  Cliquez sur **Add secret**.
5.  Créez un second secret :
    *   **Name** : `LINKEDIN_PASSWORD`
    *   **Secret** : Entrez votre mot de passe LinkedIn.

Le script est maintenant prêt à s'authentifier en toute sécurité.

### 2. Activer le mode test (Dry Run)

Avant de laisser le bot envoyer de vrais messages, vous pouvez le tester en mode "dry run". Dans ce mode, le script effectuera toutes les actions (connexion, recherche des anniversaires) sauf l'envoi du message final. Il affichera à la place un message dans les logs, indiquant à qui il aurait envoyé un message.

Pour activer ce mode :

1.  Retournez dans **Settings** > **Secrets and variables** > **Actions**.
2.  Créez un nouveau secret :
    *   **Name** : `DRY_RUN`
    *   **Secret** : `true`
3.  Pour revenir en mode normal (envoi de vrais messages), vous pouvez soit supprimer ce secret, soit changer sa valeur pour `false`.

### 3. Personnaliser les messages d'anniversaire

Pour modifier, ajouter ou supprimer des messages d'anniversaire, il vous suffit d'éditer le fichier `messages.txt`.

1.  Ouvrez le fichier `messages.txt` directement dans GitHub.
2.  Chaque ligne du fichier est un modèle de message. Modifiez-les comme vous le souhaitez.
3.  Assurez-vous de conserver le marqueur `{name}`, qui sera automatiquement remplacé par le prénom de votre contact.

**Exemple de contenu pour `messages.txt` :**
```
Joyeux anniversaire, {name} ! J'espère que tu passes une excellente journée.
Un petit message pour te souhaiter un très bon anniversaire, {name} !
Hello {name}, happy birthday!
```
Le script choisira une de ces lignes au hasard pour chaque contact.

### 4. Configuration de la Rotation de Proxies (Optionnel mais Recommandé)

Pour éviter la détection par LinkedIn, vous pouvez configurer une rotation de proxies. Cela permet de masquer votre IP et de faire croire que les requêtes proviennent de différents endroits.

#### 🌐 Pourquoi utiliser des proxies ?

- **Éviter la détection** : Les IPs datacenter de GitHub Actions sont facilement détectables par LinkedIn
- **Sécurité accrue** : Rotation automatique entre plusieurs proxies
- **Fallback automatique** : Si un proxy échoue, le système bascule automatiquement sur un autre
- **Métriques détaillées** : Suivi des performances de chaque proxy dans la base de données

#### Configuration des Proxies

1. **Dans GitHub Secrets**, ajoutez les variables suivantes :

   - **ENABLE_PROXY_ROTATION** : `true` (pour activer la rotation)
   - **PROXY_LIST** : Liste JSON des proxies, format :
     ```json
     ["http://username:password@proxy1.com:8080", "http://username:password@proxy2.com:8080"]
     ```
   - **RANDOM_PROXY_SELECTION** (optionnel) : `true` pour sélection aléatoire, `false` pour round-robin (défaut: `false`)
   - **PROXY_TIMEOUT** (optionnel) : Timeout en secondes (défaut: `10`)
   - **PROXY_MAX_RETRIES** (optionnel) : Nombre de tentatives max (défaut: `3`)

2. **Types de proxies recommandés** :
   - ✅ **Résidentiels** : IPs résidentielles (HAUTEMENT RECOMMANDÉ pour LinkedIn)
   - ✅ **Mobiles** : IPs mobiles (HAUTEMENT RECOMMANDÉ)
   - ⚠️ **Datacenter** : IPs datacenter (peu recommandé, facilement détectables)

3. **Exemple de configuration** :

   Voir le fichier `proxy_config.example.json` pour des exemples complets de configuration.

4. **Surveillance des proxies** :

   Les métriques des proxies sont automatiquement enregistrées dans la table `proxy_metrics` de la base de données :
   - Taux de succès/échec par proxy
   - Temps de réponse moyen
   - Messages d'erreur détaillés
   - Historique complet

   Vous pouvez consulter ces métriques via le Dashboard Web ou en interrogeant directement la base de données.

#### 🔒 Bonnes Pratiques

- Utilisez au minimum **3-5 proxies** différents pour une rotation efficace
- Privilégiez les **proxies résidentiels ou mobiles** pour LinkedIn
- **Ne jamais utiliser de proxies gratuits** (très souvent bloqués)
- Vérifiez que vos proxies supportent **HTTPS**
- Remplacez les proxies qui échouent fréquemment
- Localisez vos proxies dans des pays cohérents avec votre profil LinkedIn

#### 📊 Fournisseurs de Proxies Recommandés

- Bright Data (ex-Luminati)
- Smartproxy
- Oxylabs
- Geosurf
- NetNut

> **Note** : Ceci n'est pas une recommandation d'achat. Faites vos propres recherches et choisissez le fournisseur qui correspond à vos besoins.

### 5. Alternatives Gratuites aux Proxies

Si vous ne souhaitez pas investir dans des proxies payants, vous avez plusieurs alternatives **100% gratuites** :

#### 🏠 Installation Locale (Recommandé)

Installez le bot sur votre **propre matériel** pour utiliser votre IP résidentielle légitime :

- **📖 [LOCAL_INSTALLATION.md](LOCAL_INSTALLATION.md)** : Guide complet pour PC, Mac, ou Raspberry Pi
- **📖 [INSTALLATION_NAS_FREEBOX.md](INSTALLATION_NAS_FREEBOX.md)** : Guide pour NAS Synology ou Freebox Pop/Delta

**Avantages** :
- ✅ Totalement gratuit (sauf électricité ~3€/mois)
- ✅ IP résidentielle 100% légitime
- ✅ Aucune détection possible
- ✅ Contrôle total

**Matériel compatible** :
- NAS Synology (IDÉAL si vous en avez un)
- Freebox Pop/Delta
- Raspberry Pi (~35€ une fois)
- N'importe quel PC/Mac/Linux

#### 🎁 Essais Gratuits de Proxies Premium

Utilisez les **trials gratuits** des fournisseurs premium (17 jours total) :

- **📖 [PROXY_FREE_TRIALS_GUIDE.md](PROXY_FREE_TRIALS_GUIDE.md)** : Guide complet des essais gratuits
- **🔧 `manage_proxy_trials.py`** : Script de gestion automatique des trials

**Timeline** :
- Jours 1-3 : Smartproxy (pas de CB)
- Jours 4-10 : Bright Data (meilleure qualité)
- Jours 11-13 : IPRoyal ($1 crédit gratuit)
- Jour 14+ : Installation locale recommandée

#### ⚖️ Sans Proxies (GitHub Actions uniquement)

Possible mais risqué à long terme :
- ⚠️ Limiter strictement à 15-20 messages/jour max
- ⚠️ Surveillance accrue des logs
- ⚠️ Détection possible après quelques semaines

## Surveillance de l'automatisation

L'automatisation est configurée pour s'exécuter tous les jours. Voici comment vous pouvez la suivre :

- **Journaux d'exécution** : Pour voir si le script a bien fonctionné, allez dans l'onglet **Actions** de votre dépôt. Vous y verrez la liste de toutes les exécutions. En cliquant sur une exécution, vous pourrez consulter les logs détaillés.
- **Notifications par e-mail** : Si une exécution échoue, GitHub vous enverra un e-mail. Dans ce cas, consultez les logs pour identifier la cause du problème. Si une capture d'écran d'erreur a été générée (`error_*.png`), elle sera disponible en tant qu'artefact téléchargeable en bas de la page de résumé de l'exécution.

## Comment ça marche ?

Le script utilise la bibliothèque **Playwright** pour automatiser un navigateur web. Il se connecte à LinkedIn, navigue vers la page des anniversaires, identifie les contacts concernés et leur envoie un message privé choisi au hasard dans votre liste personnalisée. La première fois qu'il s'exécute, il sauvegarde les informations de session (cookies), ce qui lui permet de ne pas avoir à se reconnecter à chaque fois, rendant l'automatisation plus discrète.
