# 🚀 Déploiement sur Render.com

Guide complet pour déployer le dashboard LinkedIn Birthday Auto sur Render.com (gratuit).

## 📋 Prérequis

- Compte GitHub (déjà configuré ✓)
- Compte Render.com (gratuit, pas de carte bancaire requise)

## 🌟 Étapes de déploiement

### 1. Créer un compte Render

1. Allez sur [render.com](https://render.com)
2. Cliquez sur "Get Started for Free"
3. Connectez-vous avec votre compte GitHub
4. Autorisez Render à accéder à vos repositories

### 2. Créer un nouveau Web Service

1. Dans le dashboard Render, cliquez sur "New +" → "Web Service"
2. Sélectionnez votre repository `linkedin-birthday-auto`
3. Render détectera automatiquement le fichier `render.yaml`

### 3. Configuration automatique

Le fichier `render.yaml` configure automatiquement :

- **Runtime**: Python 3.11
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn dashboard_app:app`
- **Région**: Frankfurt (modifiable dans render.yaml)
- **Plan**: Free (750h/mois gratuit)
- **Disk**: 1GB de stockage persistant pour la base de données

### 4. Variables d'environnement

Les variables suivantes sont automatiquement configurées via `render.yaml`:

- `FLASK_SECRET_KEY` - Généré automatiquement (sécurisé)
- `DATABASE_PATH` - `linkedin_automation.db`
- `PYTHON_VERSION` - `3.11.0`

Vous pouvez les modifier dans le dashboard Render si nécessaire.

### 5. Déploiement

1. Cliquez sur "Create Web Service"
2. Render va :
   - Cloner votre repository
   - Installer les dépendances
   - Démarrer l'application
3. Le déploiement prend ~2-3 minutes

### 6. Accéder au dashboard

Une fois déployé, vous recevrez une URL comme :
```
https://linkedin-birthday-dashboard.onrender.com
```

Le dashboard sera accessible à cette adresse !

## 🔧 Configuration avancée

### Changer la région

Éditez `render.yaml` ligne 5:
```yaml
region: frankfurt  # Options: oregon, frankfurt, singapore
```

### Augmenter le stockage

Plan gratuit: 1GB
Plan payant ($7/mois): jusqu'à 10GB

Modifiez `render.yaml` ligne 15:
```yaml
sizeGB: 1  # Augmentez si nécessaire
```

### Mettre à jour l'application

Render redéploie automatiquement à chaque `git push` sur la branche principale.

Pour forcer un redéploiement:
1. Dashboard Render → Votre service → "Manual Deploy" → "Deploy latest commit"

## 📊 Monitoring

### Vérifier les logs

1. Dashboard Render → Votre service → "Logs"
2. Logs en temps réel de l'application

### Métriques

1. Dashboard Render → Votre service → "Metrics"
2. CPU, RAM, Network usage

## ⚠️ Limitations du plan gratuit

- **Sleep après inactivité**: Le service s'endort après 15 minutes sans requête
- **Réveil**: ~30 secondes au premier accès
- **750h/mois**: Largement suffisant pour un usage personnel
- **Pas de custom domain**: Uniquement sous-domaine `.onrender.com`

## 🔄 Upgrade vers un plan payant

Si vous avez besoin de plus:

**Starter ($7/mois)**:
- Pas de sleep
- Custom domain
- Plus de ressources
- Meilleur support

## 🐛 Dépannage

### Le service ne démarre pas

Vérifiez les logs:
```bash
# Dashboard Render → Logs
```

Erreurs communes:
- Dépendances manquantes → Vérifier `requirements.txt`
- Port incorrect → Gunicorn utilise automatiquement le port de Render
- Base de données → Elle sera créée au premier démarrage

### Base de données vide

Normal au premier démarrage. La base se remplit quand:
1. Le script `linkedin_birthday_wisher.py` s'exécute (localement)
2. Les données sont synchronisées via git (pas recommandé)

**Recommandation**: Utilisez le dashboard pour visualiser, mais continuez à exécuter les scripts localement.

### Erreur 500

1. Consultez les logs Render
2. Vérifiez que tous les templates sont présents
3. Vérifiez les variables d'environnement

## 🔐 Sécurité

### Variables sensibles

Ne committez JAMAIS:
- Credentials LinkedIn
- Tokens d'API
- Clés secrètes personnalisées

Utilisez les variables d'environnement Render à la place.

### Base de données

La base `linkedin_automation.db` est stockée sur le disque persistant Render.
Elle persiste entre les redéploiements.

**Important**: Ne committez pas la base dans git (déjà dans `.gitignore`).

## 📚 Ressources

- [Documentation Render](https://render.com/docs)
- [Guide Python sur Render](https://render.com/docs/deploy-flask)
- [Support Render](https://render.com/support)

## 🎉 Résumé

Vous avez maintenant :

✅ Dashboard accessible en ligne 24/7
✅ HTTPS gratuit
✅ Déploiement automatique via Git
✅ Monitoring intégré
✅ Stockage persistant pour la base de données

**URL de votre dashboard**: Notez-la depuis le dashboard Render !

---

Pour toute question, consultez la [documentation officielle](https://render.com/docs) ou ouvrez une issue sur GitHub.
