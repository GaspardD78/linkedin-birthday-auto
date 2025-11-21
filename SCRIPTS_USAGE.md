# Guide d'utilisation des scripts d'anniversaire LinkedIn

Ce projet contient deux scripts distincts pour gérer les souhaits d'anniversaire sur LinkedIn, chacun avec un objectif différent.

## 📋 Vue d'ensemble

### 1. Script Routine (`linkedin_birthday_wisher.py`)
**Usage:** Utilisation quotidienne automatique
**Workflow:** `.github/workflows/main.yml`

#### Caractéristiques :
- ✅ **Tous les anniversaires du jour sont fêtés** (priorité absolue)
- 📅 **Planification intelligente** : Les messages sont répartis automatiquement entre **7h et 19h**
- ⏱️ **Délais calculés dynamiquement** : Le délai entre chaque message est ajusté en fonction du nombre total de messages à envoyer
- 🔄 **Limite hebdomadaire** : 80 messages par semaine maximum (pour les anniversaires en retard)
- 📊 **Tracking** : Compteur hebdomadaire sauvegardé dans `weekly_messages.json`

#### Fonctionnement de la planification :
Le script calcule automatiquement le délai optimal entre les messages :
- Si vous avez **10 anniversaires** à fêter et qu'il est **10h du matin**, le script les répartira sur **9 heures** (jusqu'à 19h)
- Délai moyen : `9 heures / 10 messages = 54 minutes` (avec variation de ±20%)
- Les messages seront donc envoyés toutes les **43 à 65 minutes** environ

#### Exemple de planification :
```
Heure de début: 10h00
Nombre de messages: 10
Temps disponible: 9h (jusqu'à 19h)
Délai moyen: 54 minutes
➡️ Messages envoyés vers: 10h00, 10h54, 11h48, 12h42, 13h36, 14h30, 15h24, 16h18, 17h12, 18h06
```

#### Déclenchement :
```bash
# Automatique : Tous les jours à 8h UTC (via cron)
# Manuel : Via GitHub Actions
gh workflow run main.yml --field dry-run=false
```

---

### 2. Script Unlimited (`linkedin_birthday_wisher_unlimited.py`)
**Usage:** Utilisation unique pour rattraper tous les retards
**Workflow:** `.github/workflows/birthday_unlimited.yml`

#### Caractéristiques :
- 🚀 **AUCUNE LIMITE** : Traite TOUS les anniversaires (aujourd'hui + retards) en une seule fois
- ⚠️ **Utilisation unique recommandée** : Pour rattraper un grand retard
- 🔒 **Confirmation requise** : Nécessite de taper "CONFIRM" pour éviter les erreurs
- 📊 **Pas de tracking** : N'impacte pas le compteur hebdomadaire du script routine
- 💾 **Fichier séparé** : Utilise `weekly_messages_unlimited.json` (séparé du routine)

#### ⚠️ Attention :
Ce script est conçu pour une **utilisation ponctuelle uniquement**. Il enverra TOUS les messages sans limite, ce qui peut être détecté par LinkedIn comme un comportement suspect si utilisé trop souvent.

#### Déclenchement :
```bash
# Manuel uniquement : Via GitHub Actions
gh workflow run birthday_unlimited.yml --field dry-run=false --field confirm=CONFIRM
```

---

## 🔧 Configuration

### Variables d'environnement communes :
- `LINKEDIN_AUTH_STATE` : État d'authentification LinkedIn (secret GitHub)
- `DRY_RUN` : Mode test (true/false)
- `ENABLE_ADVANCED_DEBUG` : Débogage avancé (true/false)
- `ENABLE_EMAIL_ALERTS` : Alertes email (true/false)

### Paramètres modifiables :

#### Dans `linkedin_birthday_wisher.py` (Routine) :
```python
WEEKLY_MESSAGE_LIMIT = 80        # Limite hebdomadaire
DAILY_START_HOUR = 7             # Début d'envoi (7h)
DAILY_END_HOUR = 19              # Fin d'envoi (19h)
```

#### Dans `linkedin_birthday_wisher_unlimited.py` (Unlimited) :
```python
MAX_MESSAGES_PER_RUN = None      # Pas de limite
WEEKLY_MESSAGE_LIMIT = None      # Pas de limite
```

---

## 📊 Stratégie recommandée

### Utilisation optimale :

1. **Au démarrage du projet** (rattrapage) :
   - Utiliser le **script unlimited** UNE FOIS pour rattraper tous les retards
   - Attendre 2-3 jours avant d'utiliser le script routine

2. **Utilisation quotidienne** :
   - Laisser le **script routine** s'exécuter automatiquement
   - Tous les anniversaires du jour seront fêtés automatiquement
   - Les messages seront répartis intelligemment dans la journée

3. **En cas d'absence prolongée** :
   - Si vous avez raté plusieurs jours, vous pouvez utiliser le **script unlimited** à nouveau
   - Mais attendez au moins une semaine entre deux utilisations

---

## 🔍 Monitoring et logs

### Vérifier l'exécution :
Les workflows GitHub Actions génèrent des artifacts avec :
- Screenshots de débogage (`debug_screenshots/`)
- Logs détaillés (`linkedin_bot_detailed.log`)
- Rapports JSON (`*_report.json`)

### Fichiers de suivi :
- `weekly_messages.json` : Compteur hebdomadaire du script routine
- `weekly_messages_unlimited.json` : Compteur du script unlimited (séparé)
- `visited_profiles.txt` : Profils déjà visités

---

## ⚠️ Bonnes pratiques

### À FAIRE ✅
- Utiliser le script routine pour l'automatisation quotidienne
- Vérifier les logs après chaque exécution
- Ajuster DAILY_START_HOUR et DAILY_END_HOUR selon votre fuseau horaire
- Tester avec DRY_RUN=true avant la première utilisation

### À ÉVITER ❌
- N'utilisez PAS le script unlimited plus d'une fois par semaine
- Ne modifiez PAS les fichiers de tracking manuellement
- N'exécutez PAS les deux scripts en même temps
- Ne désactivez PAS la limite hebdomadaire du script routine (sauf si nécessaire)

---

## 🐛 Dépannage

### "Quota hebdomadaire atteint"
➡️ Normal, attendez la réinitialisation hebdomadaire (7 jours après le dernier reset)

### "Heure actuelle dépasse l'heure de fin"
➡️ Le script a démarré après 19h, les messages seront envoyés avec un délai minimal

### "Pas assez de quota pour tous les anniversaires du jour"
➡️ Le script enverra quand même tous les anniversaires du jour (priorité absolue)

---

## 📝 Exemples d'utilisation

### Cas d'usage 1 : Premier jour (10 anniversaires)
```
Heure de début: 8h30 (après le délai de démarrage aléatoire)
Anniversaires du jour: 10
Temps disponible: 10h30 (jusqu'à 19h)
Délai moyen: 63 minutes
Résultat: Tous les anniversaires fêtés avant 19h ✅
```

### Cas d'usage 2 : Retour de vacances (50 anniversaires en retard)
```
Solution: Utiliser le script unlimited UNE FOIS
Durée estimée: ~3-7 heures
Résultat: Tous les retards rattrapés en une seule exécution ✅
```

### Cas d'usage 3 : Journée chargée (30 anniversaires)
```
Heure de début: 7h00
Anniversaires du jour: 30
Temps disponible: 12h
Délai moyen: 24 minutes
Résultat: Tous les anniversaires fêtés régulièrement dans la journée ✅
```

---

## 🎯 Résumé

| Critère | Script Routine | Script Unlimited |
|---------|---------------|------------------|
| **Fréquence** | Quotidien | Ponctuel |
| **Limite** | Aucune pour aujourd'hui | Aucune |
| **Planification** | 7h-19h | Immédiat |
| **Tracking** | Oui | Non |
| **Usage** | Automatique | Manuel uniquement |
| **Déclenchement** | Cron + Manuel | Manuel avec CONFIRM |

---

**Dernière mise à jour :** 2025-11-18

---

## 🚀 Script de mise à jour (`update_bot.sh`)

Ce script simplifie la mise à jour du bot sur Raspberry Pi.

### Fonctionnalités
- ✅ **Sauvegarde automatique** des fichiers de configuration et données (`.env`, `auth_state.json`, `linkedin_birthday.db`, etc.)
- ✅ **Mise à jour Git** propre (fetch + pull)
- ✅ **Restauration** des fichiers personnels après mise à jour
- ✅ **Installation des dépendances** (pip + playwright)
- ✅ **Test rapide** pour vérifier que le script se lance bien

### Utilisation

```bash
# Rendre exécutable (première fois)
chmod +x update_bot.sh

# Lancer la mise à jour
./update_bot.sh
```

**Note :** N'utilisez pas `python3 update_bot.sh`, c'est un script Bash !
