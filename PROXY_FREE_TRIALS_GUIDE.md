# 🎁 Guide des Essais Gratuits de Proxies

Ce guide vous explique comment obtenir **17 jours de proxies premium GRATUITS** en utilisant les essais gratuits des meilleurs fournisseurs.

## 🎯 Vue d'Ensemble

Profitez des essais gratuits de 4 fournisseurs premium pour tester le système sans investissement :

| Fournisseur | Durée Trial | CB Requise ? | Délai Activation | Qualité |
|-------------|-------------|--------------|------------------|---------|
| **Smartproxy** | 3 jours | ❌ Non | Immédiat | ⭐⭐⭐⭐ |
| **Bright Data** | 7 jours | ✅ Oui* | Immédiat | ⭐⭐⭐⭐⭐ |
| **IPRoyal** | 2-3 jours | ❌ Non ($1 crédit) | Immédiat | ⭐⭐⭐ |
| **Oxylabs** | 5 jours | ✅ Oui | 24-48h | ⭐⭐⭐⭐⭐ |

**Total : ~17 jours de proxies premium gratuits**

\* CB requise mais aucun prélèvement pendant le trial

---

## 📋 Stratégie Recommandée

### Semaine 1-2 : Smartproxy (3j) + Bright Data (7j) + IPRoyal (2j)
```
Jour 1-3   : Smartproxy     ✅ Rapide, pas de CB
Jour 4-10  : Bright Data    ✅ Meilleure qualité
Jour 11-13 : IPRoyal        ✅ Économique
Jour 14+   : Oxylabs        ✅ Backup (si besoin)
```

### Semaine 3+ : Décision
- ✅ **Installation locale** (IP résidentielle gratuite) → Voir `LOCAL_INSTALLATION.md`
- ⚠️ **Acheter des proxies** (si volume important)
- 🤔 **Sans proxies** (rate limiting strict)

---

## 🚀 Utilisation du Script `manage_proxy_trials.py`

Un script Python automatise la gestion des trials :

### Installation

```bash
cd ~/linkedin-birthday-auto
chmod +x manage_proxy_trials.py
```

### Commandes Disponibles

#### 1. Voir le Statut Actuel

```bash
python3 manage_proxy_trials.py status
```

**Affiche :**
- Trial actif et jours restants
- Historique des trials utilisés
- Prochains fournisseurs disponibles
- Total de jours gratuits restants

#### 2. Configuration Interactive

```bash
python3 manage_proxy_trials.py setup
```

**Actions :**
- Sélectionne automatiquement le prochain fournisseur
- Guide l'inscription étape par étape
- Demande vos identifiants proxy
- Génère la configuration GitHub Secrets
- Enregistre les dates de début/fin

#### 3. Voir le Prochain Fournisseur

```bash
python3 manage_proxy_trials.py next
```

**Affiche :**
- Nom du prochain fournisseur
- Durée du trial
- URL d'inscription
- Notes importantes

---

## 📝 Guide Détaillé par Fournisseur

### 1️⃣ Smartproxy (3 jours - COMMENCER ICI)

#### ✅ Avantages
- Pas de carte bancaire requise
- Activation instantanée
- Interface simple
- Bon pour débuter

#### 📋 Étapes d'Inscription

1. **Aller sur** : https://smartproxy.com/pricing

2. **Créer un compte**
   - Cliquer sur "Start Free Trial"
   - Email + mot de passe
   - Aucune CB requise

3. **Obtenir les identifiants proxy**
   - Aller dans Dashboard → Residential Proxies
   - Copier Username (ex: `spXXXXX`)
   - Copier Password

4. **Format du proxy** :
   ```
   http://spXXXXX:votre_password@gate.smartproxy.com:7000
   ```

5. **Configuration GitHub Secrets**
   - `ENABLE_PROXY_ROTATION` = `true`
   - `PROXY_LIST` = `["http://spXXXXX:password@gate.smartproxy.com:7000"]`

#### 🧪 Test

```bash
# Tester la connexion
curl -x http://spXXXXX:password@gate.smartproxy.com:7000 https://ipinfo.io
```

---

### 2️⃣ Bright Data (7 jours - MEILLEURE QUALITÉ)

#### ✅ Avantages
- 7 jours gratuits (le plus long)
- Meilleure qualité du marché
- Moins de blocages LinkedIn
- 72M+ IPs résidentielles

#### ⚠️ Inconvénients
- CB requise (mais pas de prélèvement pendant trial)
- Configuration plus complexe

#### 📋 Étapes d'Inscription

1. **Aller sur** : https://brightdata.com/

2. **Créer un compte**
   - Cliquer sur "Get Started Free"
   - Remplir le formulaire
   - Entrer CB (aucun prélèvement avant fin du trial)

3. **Créer une zone proxy**
   - Aller dans Proxies → Add Zone
   - Type : Residential
   - Plan : Pay as you go

4. **Obtenir les identifiants**
   - Username format : `brd-customer-XXXXXXX-zone-YYYYYYY`
   - Password : Votre mot de passe de compte
   - Port : `22225`
   - Host : `brd.superproxy.io`

5. **Format du proxy** :
   ```
   http://brd-customer-XXXXXXX-zone-YYYYYYY:password@brd.superproxy.io:22225
   ```

6. **Configuration GitHub Secrets**
   - `ENABLE_PROXY_ROTATION` = `true`
   - `PROXY_LIST` = `["http://brd-customer-XXX-zone-YYY:pass@brd.superproxy.io:22225"]`

#### 🧪 Test

```bash
curl -x http://brd-customer-XXX-zone-YYY:pass@brd.superproxy.io:22225 https://ipinfo.io
```

---

### 3️⃣ IPRoyal (2-3 jours - ÉCONOMIQUE)

#### ✅ Avantages
- $1 de crédit gratuit offert
- Pas de CB requise
- Prix abordables après trial
- Bon pour tester

#### 📋 Étapes d'Inscription

1. **Aller sur** : https://iproyal.com/

2. **Créer un compte**
   - Sign Up
   - Confirmer email
   - $1 offert automatiquement

3. **Créer un proxy résidentiel**
   - Dashboard → Residential Proxies
   - Add Proxy
   - Choisir pays (France recommandé)

4. **Obtenir les identifiants**
   - Username : Celui créé
   - Password : Votre mot de passe
   - Host : `geo.iproyal.com`
   - Port : `12321`

5. **Format du proxy** :
   ```
   http://username:password@geo.iproyal.com:12321
   ```

6. **Configuration GitHub Secrets**
   - `ENABLE_PROXY_ROTATION` = `true`
   - `PROXY_LIST` = `["http://username:password@geo.iproyal.com:12321"]`

#### 💡 Astuce
Le crédit de $1 permet ~200-300 requêtes (largement suffisant pour 2-3 jours de tests)

---

### 4️⃣ Oxylabs (5 jours - BACKUP)

#### ✅ Avantages
- 5 jours gratuits
- Très stable
- Bon support

#### ⚠️ Inconvénients
- CB requise
- Approbation manuelle (24-48h)
- À utiliser en dernier

#### 📋 Étapes d'Inscription

1. **Aller sur** : https://oxylabs.io/

2. **Demander un trial**
   - Remplir le formulaire de demande
   - Attendre approbation (24-48h)
   - Recevoir les credentials par email

3. **Format du proxy** :
   ```
   http://customer-USERNAME:PASSWORD@pr.oxylabs.io:7777
   ```

4. **Configuration GitHub Secrets**
   - `ENABLE_PROXY_ROTATION` = `true`
   - `PROXY_LIST` = `["http://customer-USER:PASS@pr.oxylabs.io:7777"]`

---

## ⚙️ Configuration GitHub Actions

### Ajouter les Secrets

1. Aller dans votre repo → **Settings** → **Secrets and variables** → **Actions**

2. Cliquer sur **New repository secret**

3. Ajouter les secrets suivants :

#### Secret 1 : ENABLE_PROXY_ROTATION
```
Name: ENABLE_PROXY_ROTATION
Secret: true
```

#### Secret 2 : PROXY_LIST
```
Name: PROXY_LIST
Secret: ["http://username:password@proxy.com:port"]
```

**Remplacer** par vos vraies credentials du fournisseur actuel

#### Secret 3 (Optionnel) : RANDOM_PROXY_SELECTION
```
Name: RANDOM_PROXY_SELECTION
Secret: false
```

#### Secret 4 (Optionnel) : PROXY_TIMEOUT
```
Name: PROXY_TIMEOUT
Secret: 15
```

---

## 🧪 Tester la Configuration

### 1. Mode DRY_RUN

Avant de lancer en production, testez d'abord :

```
# Dans GitHub Secrets, vérifier/ajouter
DRY_RUN = true
```

### 2. Déclencher un Workflow

- Aller dans **Actions**
- Sélectionner votre workflow
- Cliquer sur **Run workflow**
- Lancer manuellement

### 3. Vérifier les Logs

Chercher dans les logs :

```
✅ Indicateurs de succès :
🌐 Proxy rotation enabled - using proxy
✅ Proxy completed successfully (response time: X.XXs)

❌ Indicateurs d'échec :
⚠️ Proxy rotation enabled but no proxy available
❌ Timeout error
❌ Connection refused
```

### 4. Vérifier la Base de Données

Le Dashboard Web affiche les métriques proxy automatiquement :
- Table `proxy_metrics`
- Taux de succès
- Temps de réponse
- Erreurs

---

## 📊 Surveillance des Trials

### Script de Monitoring

Le script `manage_proxy_trials.py` track automatiquement :

```bash
# Vérifier le statut quotidiennement
python3 manage_proxy_trials.py status

# Résultat exemple :
# ✅ Trial actif : Smartproxy
# 📅 Début : 19/11/2024
# ⏳ Expire le : 22/11/2024
# ⏰ Jours restants : 2
#
# ⚠️ ATTENTION : Le trial expire bientôt !
# 🎯 Prochain fournisseur à configurer : Bright Data
```

### Automatiser les Rappels

Ajouter au crontab pour recevoir des notifications :

```bash
# Vérifier chaque matin à 8h
0 8 * * * python3 ~/linkedin-birthday-auto/manage_proxy_trials.py status | mail -s "Statut Proxy Trials" votre@email.com
```

---

## 🔄 Rotation entre Fournisseurs

### Quand Changer ?

**Indicateurs qu'il faut changer :**
- ⏰ Trial expire dans moins de 24h
- ❌ Taux d'échec > 30%
- 🐌 Temps de réponse > 10s
- 🚫 Blocages fréquents

### Procédure de Changement

1. **Configurer le nouveau fournisseur**
   ```bash
   python3 manage_proxy_trials.py setup
   ```

2. **Copier les nouveaux secrets dans GitHub**
   - Mettre à jour `PROXY_LIST` avec le nouveau proxy

3. **Tester avec DRY_RUN=true**
   - Lancer un workflow test
   - Vérifier les logs

4. **Activer en production**
   - Passer `DRY_RUN=false`
   - Surveiller les premières exécutions

---

## 💡 Conseils et Astuces

### Maximiser la Durée Gratuite

1. **Commencer par Smartproxy** (pas de CB, activation immédiate)
2. **Configurer Bright Data en parallèle** (pendant l'utilisation de Smartproxy)
3. **IPRoyal en backup** (pour les jours entre les trials)
4. **Oxylabs en dernier recours** (approbation lente)

### Économiser le Crédit

- Limiter à 1 exécution/jour pendant les tests
- Utiliser `DRY_RUN=true` pour tester sans consommer
- Ne pas exécuter le weekend si pas nécessaire

### Qualité des Proxies par Cas d'Usage

**Pour LinkedIn (recommandé par ordre) :**
1. 🥇 Bright Data (meilleur taux de succès)
2. 🥈 Smartproxy (bon compromis)
3. 🥉 Oxylabs (très stable)
4. 💰 IPRoyal (budget serré)

---

## 🚨 Dépannage

### Erreur : "Proxy connection failed"

```bash
# Tester la connexion proxy manuellement
curl -x http://user:pass@proxy.com:port https://ipinfo.io

# Si timeout → vérifier credentials
# Si "407 Proxy Authentication Required" → mauvais user/pass
# Si "Connection refused" → mauvais host/port
```

### Erreur : "All proxies failed"

**Causes possibles :**
1. Trial expiré → changer de fournisseur
2. Credentials invalides → vérifier GitHub Secrets
3. Proxy bloqué par LinkedIn → changer de fournisseur
4. Format incorrect → vérifier le format du proxy

### Voir les Métriques Détaillées

```bash
# Connexion à la base de données
sqlite3 linkedin_birthday.db

# Voir les résultats des proxies
SELECT
    proxy_url,
    COUNT(*) as total,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
    ROUND(AVG(response_time), 2) as avg_time
FROM proxy_metrics
GROUP BY proxy_url;
```

---

## 📅 Timeline Optimale (17 Jours Gratuits)

```
📆 JOUR 1-3 : Smartproxy
└─ ✅ Inscription immédiate (pas de CB)
└─ 🧪 Tests et ajustements
└─ 📊 Vérifier les métriques

📆 JOUR 4-10 : Bright Data
└─ ✅ Meilleure qualité
└─ 🚀 Production stable
└─ 📈 Volume maximal

📆 JOUR 11-13 : IPRoyal
└─ ✅ $1 crédit gratuit
└─ ⚖️ Utilisation modérée
└─ 🔍 Évaluer les besoins

📆 JOUR 14+ : DÉCISION
├─ Option A : Installation locale (IP résidentielle)
│  └─ ✅ GRATUIT à long terme
│  └─ ✅ Zéro détection
│  └─ 📖 Voir LOCAL_INSTALLATION.md
│
├─ Option B : Acheter des proxies
│  └─ Bright Data (~$100/mois)
│  └─ Smartproxy (~$50/mois)
│  └─ IPRoyal (~$30/mois)
│
└─ Option C : Sans proxies (risqué)
   └─ Rate limiting strict
   └─ Surveillance accrue
```

---

## ✅ Checklist de Démarrage

### Avant de Commencer

- [ ] Script `manage_proxy_trials.py` téléchargé
- [ ] Compte GitHub configuré
- [ ] Repository GitHub Actions fonctionnel
- [ ] Email de confirmation prêt

### Jour 1 : Smartproxy

- [ ] Inscription sur Smartproxy (pas de CB)
- [ ] Récupération username + password
- [ ] Configuration GitHub Secrets
- [ ] Test avec DRY_RUN=true
- [ ] Premier workflow en production
- [ ] Vérification logs : "Proxy rotation enabled"
- [ ] Enregistrer date d'expiration (J+3)

### Jour 4 : Bright Data

- [ ] Inscription sur Bright Data (CB requise)
- [ ] Création zone proxy résidentielle
- [ ] Récupération credentials complets
- [ ] Mise à jour GitHub Secrets (PROXY_LIST)
- [ ] Test immédiat
- [ ] Vérifier taux de succès > 90%
- [ ] Enregistrer date d'expiration (J+10)

### Jour 11 : IPRoyal

- [ ] Inscription IPRoyal
- [ ] Vérifier $1 crédit
- [ ] Configuration proxy résidentiel
- [ ] Mise à jour PROXY_LIST
- [ ] Surveillance crédit restant

### Jour 14+ : Choix Long Terme

- [ ] Évaluer les statistiques (proxy_metrics)
- [ ] Décider : Local / Payant / Sans proxy
- [ ] Implémenter la solution choisie

---

## 🎓 Ressources Complémentaires

- 📖 **LOCAL_INSTALLATION.md** : Guide installation locale (IP résidentielle gratuite)
- 📖 **proxy_config.example.json** : Exemples de configuration
- 📖 **README.md** : Documentation principale
- 🔧 **manage_proxy_trials.py** : Script de gestion des trials
- 📊 **Dashboard Web** : Surveillance des métriques

---

## 🆘 Support

Questions fréquentes :

**Q : Puis-je utiliser plusieurs trials en même temps ?**
R : Non, utilisez-les séquentiellement pour maximiser la durée gratuite totale.

**Q : Que se passe-t-il à la fin du trial ?**
R : Le proxy ne fonctionne plus. Passez au fournisseur suivant ou choisissez une solution long terme.

**Q : Dois-je annuler après le trial ?**
R : Oui, pour éviter les frais. Consultez les conditions de chaque fournisseur.

**Q : Puis-je réutiliser un trial ?**
R : Non, un seul trial par fournisseur. D'où l'importance de les utiliser stratégiquement.

---

**Prêt à démarrer ?** 🚀

```bash
python3 manage_proxy_trials.py setup
```

Bonne chance ! 🎉
