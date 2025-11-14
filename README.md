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

### 2. (Optionnel) Personnaliser les messages d'anniversaire

Si vous souhaitez modifier les messages envoyés :

1.  Ouvrez le fichier `linkedin_birthday_wisher.py`.
2.  Trouvez la liste `BIRTHDAY_MESSAGES` au début du fichier.
3.  Modifiez, ajoutez ou supprimez des messages dans cette liste. Assurez-vous de conserver `{name}` qui sera automatiquement remplacé par le prénom de votre contact.

Exemple :
```python
BIRTHDAY_MESSAGES = [
    "Joyeux anniversaire, {name} ! J'espère que tu passes une excellente journée.",
    "Un petit message pour te souhaiter un très bon anniversaire, {name} !",
]
```

## Surveillance de l'automatisation

L'automatisation est configurée pour s'exécuter tous les jours. Voici comment vous pouvez la suivre :

- **Journaux d'exécution** : Pour voir si le script a bien fonctionné, allez dans l'onglet **Actions** de votre dépôt. Vous y verrez la liste de toutes les exécutions. En cliquant sur une exécution, vous pourrez consulter les logs détaillés.
- **Notifications par e-mail** : Si une exécution échoue, GitHub vous enverra un e-mail. Dans ce cas, consultez les logs pour identifier la cause du problème. Si une capture d'écran d'erreur a été générée (`error_*.png`), elle sera disponible en tant qu'artefact téléchargeable en bas de la page de résumé de l'exécution.

## Comment ça marche ?

Le script utilise la bibliothèque **Playwright** pour automatiser un navigateur web. Il se connecte à LinkedIn, navigue vers la page des anniversaires, identifie les contacts concernés et leur envoie un message privé choisi au hasard dans votre liste personnalisée. La première fois qu'il s'exécute, il sauvegarde les informations de session (cookies), ce qui lui permet de ne pas avoir à se reconnecter à chaque fois, rendant l'automatisation plus discrète.
