# Configuration du Debugging dans GitHub Actions

Ce guide explique comment activer le système de debugging avancé dans GitHub Actions.

## 🎯 Option 1 : Debugging Basique (Sans Alertes Email)

### Étape 1 : Ajouter le Secret ENABLE_ADVANCED_DEBUG

1. Va sur ton repo GitHub : https://github.com/GaspardD78/linkedin-birthday-auto
2. Clique sur **Settings** (en haut)
3. Dans le menu gauche, clique sur **Secrets and variables** → **Actions**
4. Clique sur **New repository secret**
5. Ajoute :
   - **Name** : `ENABLE_ADVANCED_DEBUG`
   - **Secret** : `true`
6. Clique sur **Add secret**

### C'est tout ! 🎉

Le debugging sera maintenant activé lors de la prochaine exécution. Tu auras accès à :
- ✅ Screenshots automatiques à chaque étape
- ✅ Validation DOM
- ✅ Détection de restrictions LinkedIn
- ✅ Logs détaillés
- ✅ Rapports JSON

### Télécharger les Artefacts de Debug

Après chaque exécution :
1. Va sur l'onglet **Actions**
2. Clique sur l'exécution du workflow
3. Descends jusqu'à **Artifacts**
4. Télécharge :
   - `debug-screenshots-XXX` - Tous les screenshots
   - `debug-logs-XXX` - Logs et rapports JSON

Les artefacts sont conservés **7 jours**.

---

## 📧 Option 2 : Debugging Complet avec Alertes Email

Si tu veux recevoir des emails automatiques en cas de problème, ajoute ces secrets supplémentaires :

### Étape 1 : Créer un App Password Gmail

1. Va sur https://myaccount.google.com/security
2. Active la **vérification en 2 étapes** (si pas déjà fait)
3. Retourne sur https://myaccount.google.com/security
4. Cherche **"App passwords"** ou va sur https://myaccount.google.com/apppasswords
5. Sélectionne :
   - **App** : Mail
   - **Device** : Other (custom name) → Tape "LinkedIn Bot"
6. Clique sur **Generate**
7. **COPIE le mot de passe de 16 caractères** (tu ne pourras plus le voir)

### Étape 2 : Ajouter les Secrets Email

Retourne dans **Settings** → **Secrets and variables** → **Actions** et ajoute :

1. **ENABLE_EMAIL_ALERTS**
   - Secret : `true`

2. **ALERT_EMAIL**
   - Secret : `ton-email@gmail.com` (l'email qui envoie)

3. **ALERT_EMAIL_PASSWORD**
   - Secret : `xxxx xxxx xxxx xxxx` (le mot de passe app de 16 caractères)

4. **RECIPIENT_EMAIL**
   - Secret : `email-notification@example.com` (où tu veux recevoir les alertes)

5. (Optionnel) **SMTP_SERVER**
   - Secret : `smtp.gmail.com` (déjà par défaut)

6. (Optionnel) **SMTP_PORT**
   - Secret : `587` (déjà par défaut)

### Résultat

Tu recevras un email automatique si :
- ❌ La connexion LinkedIn échoue
- ❌ Un CAPTCHA est détecté
- ❌ Une restriction de compte est détectée
- ❌ Le script crash avec une erreur

L'email contiendra :
- Le message d'erreur
- Les screenshots automatiques
- Les logs détaillés

---

## 🔄 Désactiver le Debugging

Pour désactiver le debugging (recommandé en production stable) :

1. Va dans **Settings** → **Secrets and variables** → **Actions**
2. Clique sur `ENABLE_ADVANCED_DEBUG`
3. Clique sur **Update**
4. Change la valeur à `false`
5. Clique sur **Update secret**

Les fonctionnalités anti-détection (délais gaussiens, pauses longues, activité simulée) restent **toujours actives**.

---

## 📊 Récapitulatif des Secrets

### Secrets Obligatoires (déjà configurés)
- ✅ `LINKEDIN_AUTH_STATE` - Ton authentification LinkedIn

### Secrets pour Debugging Basique
- 🆕 `ENABLE_ADVANCED_DEBUG` = `true`

### Secrets pour Alertes Email (optionnels)
- 🆕 `ENABLE_EMAIL_ALERTS` = `true`
- 🆕 `ALERT_EMAIL` = ton email Gmail
- 🆕 `ALERT_EMAIL_PASSWORD` = App Password Gmail (16 caractères)
- 🆕 `RECIPIENT_EMAIL` = email pour recevoir les alertes

---

## 🧪 Tester la Configuration

### Test Manuel

1. Va sur l'onglet **Actions**
2. Clique sur **LinkedIn Birthday Wisher** (à gauche)
3. Clique sur **Run workflow** (bouton à droite)
4. Sélectionne :
   - **dry-run** : `true`
5. Clique sur **Run workflow**

### Vérifier les Résultats

Après l'exécution :
1. Clique sur l'exécution dans la liste
2. Vérifie les logs - tu devrais voir :
   ```
   🔧 Advanced debugging enabled - initializing debug managers...
   🔍 Validating DOM structure...
   🚨 Checking for LinkedIn restrictions...
   ```
3. Télécharge les artifacts (en bas de la page)
4. Vérifie les screenshots dans `debug-screenshots-XXX.zip`

Si tu as activé les alertes email :
- Tu devrais recevoir un email si une erreur se produit
- Vérifie ton dossier spam la première fois

---

## ⚠️ Sécurité

- ✅ Les secrets GitHub sont chiffrés
- ✅ Les screenshots et logs ne sont **jamais** committés dans Git
- ✅ Les artefacts GitHub Actions sont privés (seuls toi et les collaborateurs peuvent les voir)
- ✅ Les artefacts sont automatiquement supprimés après 7 jours
- ✅ N'utilise **JAMAIS** ton mot de passe Gmail normal - uniquement les App Passwords

---

## 🆘 Problèmes Courants

### "Email alerts not working"

**Solution** :
1. Vérifie que tu utilises un **App Password** Gmail (pas ton mot de passe normal)
2. Vérifie que la vérification en 2 étapes est activée sur Gmail
3. Vérifie les noms des secrets (sensibles à la casse)
4. Vérifie ton dossier spam

### "No debug screenshots uploaded"

**Solution** :
1. Vérifie que `ENABLE_ADVANCED_DEBUG` = `true` (pas `True` ou `TRUE`)
2. Vérifie les logs du workflow - tu devrais voir le message "Advanced debugging enabled"
3. Les artifacts n'apparaissent que si le script s'exécute (même avec des erreurs)

### "Artifacts not found"

C'est normal si :
- Le debugging est désactivé
- Le script ne s'est pas exécuté du tout (erreur avant le script Python)
- Tu regardes une exécution de plus de 7 jours

---

## 📚 Plus d'Infos

Consulte `DEBUGGING.md` pour :
- Interpréter les screenshots
- Comprendre les rapports JSON
- Utiliser le debugging en local
- Bonnes pratiques

---

## ✅ Checklist de Configuration

- [ ] Secret `ENABLE_ADVANCED_DEBUG` = `true` ajouté
- [ ] Workflow modifié et pushé sur GitHub
- [ ] Test manuel effectué (Run workflow avec dry-run)
- [ ] Screenshots de debug téléchargés et vérifiés
- [ ] (Optionnel) App Password Gmail créé
- [ ] (Optionnel) Secrets email configurés
- [ ] (Optionnel) Email de test reçu
