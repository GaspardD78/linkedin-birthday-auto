# Guide du Scraping de Profils LinkedIn

## 📋 Vue d'ensemble

Le `VisitorBot` a été amélioré pour scraper automatiquement les données détaillées de chaque profil visité et les sauvegarder dans une base de données SQLite avec export CSV.

## 🎯 Données collectées

Pour chaque profil visité, le bot collecte :

- **Nom complet** (`full_name`)
- **Prénom** (`first_name`)
- **Nom de famille** (`last_name`)
- **Niveau de relation** (`relationship_level`) : 1er, 2e, 3e degré
- **Entreprise actuelle** (`current_company`)
- **Formation** (`education`) : Premier diplôme/établissement
- **Années d'expérience** (`years_experience`) : Calculées automatiquement
- **URL du profil** (`profile_url`)
- **Date de scraping** (`scraped_at`)

## 🚀 Utilisation

### 1. Lancer le VisitorBot avec scraping

Le scraping est automatiquement activé lors de l'exécution du VisitorBot :

```bash
# Mode production (visite réelle + scraping)
python main.py --mode visitor

# Mode dry-run (simulation sans visite)
python main.py --mode visitor --dry-run
```

### 2. Exporter les données en CSV

Utilisez le script d'export pour générer un fichier CSV :

```bash
# Export avec nom par défaut (scraped_profiles_YYYY-MM-DD.csv)
python export_scraped_data.py

# Export vers un fichier spécifique
python export_scraped_data.py my_profiles.csv

# Export vers un répertoire spécifique
python export_scraped_data.py exports/linkedin_profiles.csv

# Voir uniquement les statistiques (sans exporter)
python export_scraped_data.py --stats
```

### 3. Consulter les statistiques

```bash
# Afficher les statistiques sans exporter
python export_scraped_data.py --stats
```

Cela affichera :
- Nombre total de profils scrapés
- Top 5 des entreprises
- Répartition par niveau de relation

## 📊 Format du CSV exporté

Le fichier CSV contient les colonnes suivantes (séparateur `,`) :

```csv
profile_url,first_name,last_name,full_name,relationship_level,current_company,education,years_experience,scraped_at
https://linkedin.com/in/john-doe,John,Doe,John Doe,1er,Acme Corp,MIT,12,2025-11-28T14:30:00
```

## 🔧 Architecture technique

### Base de données

Une nouvelle table `scraped_profiles` a été ajoutée à la base SQLite :

```sql
CREATE TABLE scraped_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_url TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    relationship_level TEXT,
    current_company TEXT,
    education TEXT,
    years_experience INTEGER,
    scraped_at TEXT NOT NULL
)
```

### Méthodes ajoutées

#### Dans `src/core/database.py`

- `save_scraped_profile(...)` : Enregistre ou met à jour (UPSERT) un profil
- `get_scraped_profile(profile_url)` : Récupère un profil par URL
- `get_all_scraped_profiles(limit)` : Récupère tous les profils
- `export_scraped_data_to_csv(output_path)` : Export CSV avec gestion UTF-8

#### Dans `src/bots/visitor_bot.py`

- `_scrape_profile_data()` : Scrape les données d'un profil LinkedIn
- `_save_scraped_profile_data(scraped_data)` : Sauvegarde en base

## 🛡️ Gestion des erreurs

Le scraping est **non-bloquant** :
- Si un élément n'est pas trouvé, la valeur par défaut est `"Unknown"` ou `None`
- Les erreurs de scraping sont loguées mais ne font pas planter le bot
- La visite de profil continue même si le scraping échoue partiellement

## 📝 Logs

Le bot génère des logs détaillés :

```
[INFO] Données récupérées pour John Doe (Acme Corp)
[INFO] ✅ Scraped data saved for John Doe
[DEBUG] Could not extract education: Timeout
```

## 🎨 Sélecteurs LinkedIn

Le bot utilise plusieurs sélecteurs de secours pour gérer les variations du DOM LinkedIn :

- **Nom** : `h1.text-heading-xlarge`, `h1.inline`, `div.ph5 h1`
- **Relation** : `span.dist-value`, `div.pv-top-card--list-bullet li`
- **Entreprise** : `div.text-body-medium`, section Expérience
- **Formation** : `section:has-text("Formation")`, `section:has-text("Education")`
- **Expérience** : Parsing des dates dans la section Expérience

## 🔄 UPSERT automatique

Si un profil est visité plusieurs fois, ses données sont **mises à jour** automatiquement grâce à la contrainte `UNIQUE` sur `profile_url`.

## 📈 Performance

- **Scraping non-bloquant** : N'ajoute que quelques secondes au temps de visite
- **Base SQLite optimisée** : Mode WAL, indexes sur `profile_url` et `scraped_at`
- **Export CSV rapide** : Gestion efficace de l'UTF-8 et des caractères spéciaux

## 🐛 Troubleshooting

### Le scraping ne fonctionne pas

1. Vérifier que la base de données est activée dans `config.yaml` :
   ```yaml
   database:
     enabled: true
     db_path: "linkedin_automation.db"
   ```

2. Vérifier les logs pour voir si des sélecteurs ont échoué

3. LinkedIn a peut-être changé son DOM → Adapter les sélecteurs dans `_scrape_profile_data()`

### Le CSV est vide

1. Vérifier que des profils ont été visités : `python export_scraped_data.py --stats`
2. Vérifier que la base de données existe : `ls -lh linkedin_automation.db`

### Caractères mal encodés dans le CSV

Le CSV utilise UTF-8 par défaut. Pour ouvrir correctement dans Excel :
1. Ouvrir Excel
2. Données → Depuis un fichier texte/CSV
3. Choisir l'encodage UTF-8

## 🔐 Conformité et éthique

- ⚠️ Respectez les conditions d'utilisation de LinkedIn
- 🔒 Ne partagez pas les données scrapées publiquement
- 🤖 Utilisez des délais réalistes pour simuler un comportement humain
- 📜 Ce projet est à des fins éducatives et personnelles

## 📚 Exemples d'utilisation

### Exemple 1 : Export quotidien automatisé

```bash
#!/bin/bash
# Cron job pour export quotidien
cd /path/to/linkedin-birthday-auto
python export_scraped_data.py exports/profiles_$(date +%Y%m%d).csv
```

### Exemple 2 : Analyse avec pandas

```python
import pandas as pd

# Charger le CSV
df = pd.read_csv('scraped_profiles.csv')

# Top 10 entreprises
print(df['current_company'].value_counts().head(10))

# Moyenne d'années d'expérience
print(f"Moyenne: {df['years_experience'].mean():.1f} ans")

# Filtrer par niveau de relation
first_degree = df[df['relationship_level'].str.contains('1er|1st')]
print(f"Contacts de 1er degré: {len(first_degree)}")
```

## 🎯 Prochaines améliorations possibles

- [ ] Scraping des compétences (skills)
- [ ] Extraction des recommandations
- [ ] Historique complet des expériences
- [ ] Export JSON en plus du CSV
- [ ] Dashboard de visualisation des données scrapées
- [ ] Détection automatique des changements de poste

---

**Version** : 2.1.0
**Dernière mise à jour** : 2025-11-28
