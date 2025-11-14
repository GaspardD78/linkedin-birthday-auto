# LinkedIn Birthday Wisher Bot

Ce projet contient un script d'automatisation Python conçu pour souhaiter automatiquement un joyeux anniversaire à vos contacts de premier niveau sur LinkedIn. Le bot est conçu pour être discret et imiter le comportement humain afin de minimiser les risques de détection.

## Fonctionnalités

- **Connexion Sécurisée** : Utilise les secrets de GitHub pour stocker vos identifiants en toute sécurité, sans jamais les écrire en clair dans le code.
- **Comportement Humain** : Le script intègre des délais aléatoires et simule la frappe au clavier pour paraître moins robotique.
- **Exécution Programmée** : Grâce à GitHub Actions, le script s'exécute automatiquement chaque matin à une heure variable entre 8h00 et 10h00 (UTC).
- **Messages Personnalisables** : Vous pouvez facilement modifier la liste des messages d'anniversaire.
- **Notifications d'Erreur** : Si le script échoue, GitHub Actions vous enverra automatiquement un e-mail et enregistrera une capture d'écran du problème.

## Configuration

Suivez ces étapes pour configurer et activer le bot.

### 1. Générer et stocker votre état d'authentification LinkedIn

Pour que le script puisse se connecter à votre compte, vous devez générer un état d'authentification (qui contient votre session LinkedIn avec tous les cookies) et le stocker en tant que "secret" dans votre dépôt GitHub. Cette méthode est plus sûre car elle ne stocke pas directement vos identifiants.

**Étape A : Générer l'état d'authentification**

1.  Sur votre ordinateur local, installez les dépendances :
    ```bash
    pip install playwright
    playwright install chromium
    ```

2.  Exécutez le script de génération :
    ```bash
    python generate_auth_state.py
    ```

3.  Un navigateur s'ouvrira. Connectez-vous à LinkedIn (avec email, mot de passe et code 2FA si activé).

4.  Une fois connecté, revenez au terminal et appuyez sur **Entrée**.

5.  Le script affichera une longue chaîne de caractères Base64. **Copiez-la**.

**Étape B : Créer le secret GitHub**

1.  Dans votre dépôt GitHub, allez dans **Settings** > **Secrets and variables** > **Actions**.
2.  Cliquez sur **New repository secret**.
3.  Créez le secret :
    *   **Name** : `LINKEDIN_AUTH_STATE`
    *   **Secret** : Collez la chaîne Base64 copiée à l'étape A.
4.  Cliquez sur **Add secret**.

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

## Surveillance de l'automatisation

L'automatisation est configurée pour s'exécuter tous les jours. Voici comment vous pouvez la suivre :

- **Journaux d'exécution** : Pour voir si le script a bien fonctionné, allez dans l'onglet **Actions** de votre dépôt. Vous y verrez la liste de toutes les exécutions. En cliquant sur une exécution, vous pourrez consulter les logs détaillés.
- **Notifications par e-mail** : Si une exécution échoue, GitHub vous enverra un e-mail. Dans ce cas, consultez les logs pour identifier la cause du problème. Si une capture d'écran d'erreur a été générée (`error_*.png`), elle sera disponible en tant qu'artefact téléchargeable en bas de la page de résumé de l'exécution.

## Comment ça marche ?

Le script utilise la bibliothèque **Playwright** pour automatiser un navigateur web. Il se connecte à LinkedIn, navigue vers la page des anniversaires, identifie les contacts concernés et leur envoie un message privé choisi au hasard dans votre liste personnalisée. La première fois qu'il s'exécute, il sauvegarde les informations de session (cookies), ce qui lui permet de ne pas avoir à se reconnecter à chaque fois, rendant l'automatisation plus discrète.
