# 🔑 GUIDE GESTION MOT DE PASSE
## Change, Reset & Recovery Dashboard Password

**Version:** 3.3+
**Date:** Jan 2025
**Script:** `scripts/manage_dashboard_password.sh`
**Sécurité:** Bcrypt hashing, audit trail, no plaintext storage

---

## 📋 Table des Matières

1. [Concepts Sécurité](#concepts-sécurité)
2. [Usage Script](#usage-script)
3. [Change Password](#change-password)
4. [Reset Password](#reset-password)
5. [Show Status](#show-status)
6. [Recovery Scenarios](#recovery-scenarios)
7. [Troubleshooting](#troubleshooting)

---

## 🔒 Concepts Sécurité

### Hachage Bcrypt

**Votre mot de passe:**
```
MySecurePassword123!
```

**Stocké en .env (hasché):**
```bash
DASHBOARD_PASSWORD=$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

**Avantages:**
- ✅ Mot de passe jamais en clair
- ✅ Impossible de récupérer mot de passe original
- ✅ Même mot de passe = hash différent chaque fois
- ✅ Fonction unidirectionnelle (non réversible)

### Audit Trail

**Chaque action est loggée:**
```bash
# logs/password_history.log:
2025-01-19 10:15:23 - Mot de passe modifié
2025-01-19 11:32:45 - Mot de passe réinitialisé
```

**Note:** Log ne contient JAMAIS le mot de passe!

---

## 🚀 Usage Script

### Accès

```bash
# Depuis répertoire projet:
./scripts/manage_dashboard_password.sh

# Ou depuis ailleurs:
/path/to/linkedin-birthday-auto/scripts/manage_dashboard_password.sh
```

### Menu Principal

```
╔════════════════════════════════════════════════╗
║    Gestion du Mot de Passe Dashboard          ║
╚════════════════════════════════════════════════╝

Que désirez-vous faire ?

  1) Changer le mot de passe
  2) Réinitialiser le mot de passe (générer un aléatoire)
  3) Afficher le statut du mot de passe
  4) Quitter

Votre choix [1-4] (timeout 30s) :
```

---

## 🔐 Change Password

### Utilisation

```bash
./scripts/manage_dashboard_password.sh

# Choisir: 1
```

### Process Détaillé

```
Changement du mot de passe...

Entrez le nouveau mot de passe :
Mot de passe (caché) : ••••••••••••

Confirmez le mot de passe :
Mot de passe (caché) : ••••••••••••
```

**Validations automatiques:**
- ✓ Double saisie (pas de typos)
- ✓ Min 8 caractères recommandé
- ⚠️ Si < 8: warning demande confirmation

### Exemple

```bash
$ ./scripts/manage_dashboard_password.sh

╔════════════════════════════════════════════════╗
║    Gestion du Mot de Passe Dashboard          ║
╚════════════════════════════════════════════════╝

Que désirez-vous faire ?

  1) Changer le mot de passe
  2) Réinitialiser le mot de passe (générer un aléatoire)
  3) Afficher le statut du mot de passe
  4) Quitter

Votre choix [1-4] (timeout 30s) : 1

[INFO] Changement du mot de passe...

Entrez le nouveau mot de passe :
Mot de passe (caché) : NewSecurePass456!

Confirmez le mot de passe :
Mot de passe (caché) : NewSecurePass456!

[INFO] Hachage sécurisé du mot de passe...
[OK] Mot de passe modifié et stocké dans .env (avec $$ doublés)
[INFO]   Hash: $$2b$$12$$EBpvXzNy2... (premiers 20 chars)
[OK] Dashboard redémarré. Nouveau mot de passe actif.
```

### Dashboard Restart

Automatique après changement:
- Docker restart `dashboard` container
- Session existantes: **invalidées**
- Connexion suivante: utiliser nouveau mot de passe

### Accès Après

```bash
# Nouvelle connexion:
https://YOUR_DOMAIN

# Login: admin
# Password: NewSecurePass456!  ← Votre nouveau mot de passe
```

---

## 🔑 Reset Password

### Utilisation (Oubli Mot de Passe!)

```bash
./scripts/manage_dashboard_password.sh

# Choisir: 2
```

### ⚠️ Important

**Le mot de passe réinitialisé:**
- ✓ Sera affichée UNE SEULE FOIS
- ✓ Ne peut pas être récupéré après
- ✓ Doit être sauvegardé immédiatement
- ❌ Si perdu = relancer reset à nouveau

### Process

```bash
$ ./scripts/manage_dashboard_password.sh

# Choisir: 2

[WARN] ⚠️  RÉINITIALISATION DU MOT DE PASSE
[INFO] Un mot de passe temporaire fort sera généré et affiché une seule fois.

Êtes-vous sûr ? [y/N] : y

[INFO] Hachage du mot de passe temporaire...
[INFO] Redémarrage du dashboard...
[OK] Dashboard redémarré avec mot de passe temporaire.

╔══════════════════════════════════════════════════════════╗
║        ✓ MOT DE PASSE TEMPORAIRE GÉNÉRÉ                 ║
╚══════════════════════════════════════════════════════════╝

  sX+4aB9kC2mE7Jp3Qw8Uy1Lk5Tz6Rx9Vb2Hn4

  ⚠️  SAUVEGARDEZ CE MOT DE PASSE MAINTENANT !
  ⚠️  IL NE SERA PAS AFFICHÉ À NOUVEAU.

  Après connexion:
    1. Changez le mot de passe via le dashboard, ou
    2. Relancez ce script et choisissez 'Changer le mot de passe'
```

### Connexion Avec Temporaire

```bash
# URL:
https://YOUR_DOMAIN

# Login: admin
# Password: sX+4aB9kC2mE7Jp3Qw8Uy1Lk5Tz6Rx9Vb2Hn4
```

### Changer de Nouveau Mot de Passe

**Via Dashboard (si disponible):**
- Settings → Account → Change Password

**Via Script (alternative):**
```bash
./scripts/manage_dashboard_password.sh
# Choisir: 1 (Change Password)
# Entrer nouveau mot de passe
```

---

## 📊 Show Status

### Utilisation

```bash
./scripts/manage_dashboard_password.sh

# Choisir: 3
```

### Affichage

```bash
Statut du Mot de Passe Dashboard

  ✓ Hash bcrypt présent
  Hash (premiers 30 chars): $$2b$$12$$EBpvXzNy2TxUz7r3Q5m9...
  Dernier changement: 2025-01-19 10:15:23 - Mot de passe modifié
```

### Interprétation

| Affichage | Sens |
|-----------|------|
| ✓ Hash bcrypt présent | OK - Mot de passe configuré |
| ✗ CONFIGURATION MANQUANTE | ⚠️ Mot de passe par défaut - à changer! |
| ⚠ FORMAT INCONNU | ⚠️ Problème format - contacter support |

---

## 🆘 Recovery Scenarios

### Scenario 1: Mot de Passe Oublié

**Problème:** Vous ne vous souvenez plus du mot de passe dashboard

**Solution:**

```bash
# 1. SSH vers RPi:
ssh user@raspberry-pi

# 2. Relancer reset password:
./scripts/manage_dashboard_password.sh

# 3. Choisir option 2 (Reset)

# 4. Nouveau mot de passe temporaire s'affiche

# 5. Connexion avec temporaire

# 6. Changer vers nouveau mot de passe sécurisé
```

### Scenario 2: Accès SSH Indisponible

**Problème:** Pas d'accès SSH à RPi4

**Solutions alternatives:**

1. **HDMI + Clavier (si RPi4 en local)**
   ```bash
   # Terminal physique:
   cd linkedin-birthday-auto
   ./scripts/manage_dashboard_password.sh
   # Choisir option 2
   ```

2. **VNC/Remote Desktop**
   - Se connecter via VNC
   - Ouvrir terminal
   - Relancer script

3. **Re-setup complet (dernière option)**
   ```bash
   git pull  # Dernière version
   ./setup.sh  # Relance complet setup
   # Lors de Phase 3 (Password), new prompt demande config
   ```

### Scenario 3: .env Fichier Corrompu

**Problème:** Fichier .env endommagé

**Solution:**

```bash
# 1. Restaurer de backup:
cp .env .env.bak
git checkout .env

# 2. Ou recréer depuis template:
cp .env.pi4.example .env

# 3. Relancer setup:
./setup.sh

# 4. Lors Password phase, nouvelle config
```

### Scenario 4: Docker Container Crashed

**Problème:** Dashboard container mort

**Solution:**

```bash
# 1. Redémarrer services:
docker compose restart

# 2. Vérifier status:
docker compose ps

# 3. Si problème persiste:
docker compose logs dashboard

# 4. Relancer script password:
./scripts/manage_dashboard_password.sh

# 5. Re-hash et restart
```

---

## 🐛 Troubleshooting

### ❌ ".env non trouvé"

```bash
# Erreur:
/INFO/ .env non trouvé. Lancez setup.sh d'abord.

# Solution:
cd linkedin-birthday-auto  # Bon répertoire
./setup.sh
# Puis retry password script
```

### ❌ "Docker image not found"

```bash
# Erreur:
docker: image not found

# Solution:
# Script va télécharger automatiquement:
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest

# Retry
```

### ❌ "Permission denied"

```bash
# Erreur:
sed: can't read .env: Permission denied

# Solution 1: Run avec sudo
sudo ./scripts/manage_dashboard_password.sh

# Solution 2: Fixer permissions
chmod 600 .env
./scripts/manage_dashboard_password.sh

# Solution 3: Owner change
sudo chown $USER:$USER .env
./scripts/manage_dashboard_password.sh
```

### ❌ "Timeout"

```bash
# Timeout après 30 secondes

# Solution:
# Redémarrer script et répondre plus vite
./scripts/manage_dashboard_password.sh

# Ou modifier timeout dans script (avancé):
nano scripts/manage_dashboard_password.sh
# Trouver: timeout=30
# Changer à: timeout=60
```

### ❌ "Dashboard restart failed"

```bash
# Erreur lors restart

# Solution:
# Redémarrer manuellement:
docker compose restart dashboard

# Ou tout:
docker compose restart
```

---

## ✅ Checklist Password

- [ ] Script accessible (`./scripts/manage_dashboard_password.sh`)
- [ ] Option 1 (Change): Teste avec nouveau password
- [ ] Option 2 (Reset): Teste avec temporaire généré
- [ ] Option 3 (Status): Affiche info correcte
- [ ] Dashboard redémarre après changement
- [ ] New password works lors reconnexion
- [ ] logs/password_history.log loggé

---

## 🎯 Best Practices

1. **Mot de passe fort**
   - Minimum 12 caractères
   - Majuscules + minuscules + chiffres + symboles
   - Exemple: `MyS3cur3P@ssw0rd!`

2. **Changer régulièrement**
   - Tous les 90 jours recommandé
   - Après accès soupçonné
   - Après changement staff

3. **Ne pas partager**
   - Mot de passe = personnel
   - Si partagé: changer immédiatement

4. **Sauvegarde sécurisée**
   - Si temporaire: copier ailleurs
   - Ne pas committer dans git
   - Utiliser password manager

---

**Besoin d'aide?** Consultez [docs/TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md)
