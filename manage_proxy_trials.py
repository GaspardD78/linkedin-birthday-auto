#!/usr/bin/env python3
"""
Script de gestion des essais gratuits de proxies
Permet de basculer automatiquement entre les fournisseurs
"""

import json
import os
from datetime import datetime, timedelta

# Configuration des fournisseurs avec dates de trial
PROXY_PROVIDERS = {
    "smartproxy": {
        "name": "Smartproxy",
        "trial_days": 3,
        "proxy_format": "http://username:password@gate.smartproxy.com:7000",
        "signup_url": "https://smartproxy.com/pricing",
        "notes": "Inscription rapide, pas de CB requise"
    },
    "brightdata": {
        "name": "Bright Data",
        "trial_days": 7,
        "proxy_format": "http://brd-customer-XXX-zone-XXX:password@brd.superproxy.io:22225",
        "signup_url": "https://brightdata.com/",
        "notes": "Meilleure qualité, CB requise (pas de prélèvement)"
    },
    "oxylabs": {
        "name": "Oxylabs",
        "trial_days": 5,
        "proxy_format": "http://customer-USERNAME:PASSWORD@pr.oxylabs.io:7777",
        "signup_url": "https://oxylabs.io/",
        "notes": "Approbation manuelle (24-48h)"
    },
    "iproyal": {
        "name": "IPRoyal",
        "trial_days": 2,
        "proxy_format": "http://username:password@geo.iproyal.com:12321",
        "signup_url": "https://iproyal.com/",
        "notes": "$1 de crédit gratuit"
    }
}

def load_trial_config():
    """Charge la configuration des trials depuis un fichier JSON"""
    config_file = "proxy_trials_config.json"

    if not os.path.exists(config_file):
        return {
            "current_provider": None,
            "trials_used": [],
            "start_dates": {}
        }

    with open(config_file, 'r') as f:
        return json.load(f)

def save_trial_config(config):
    """Sauvegarde la configuration des trials"""
    with open("proxy_trials_config.json", 'w') as f:
        json.dump(config, f, indent=2, default=str)

def get_next_provider(config):
    """Détermine le prochain fournisseur à utiliser"""
    used_providers = set(config.get("trials_used", []))
    available = [p for p in PROXY_PROVIDERS.keys() if p not in used_providers]

    if not available:
        return None

    # Retourner le premier provider disponible
    return available[0]

def check_trial_expiry(config):
    """Vérifie si le trial actuel a expiré"""
    current = config.get("current_provider")
    if not current:
        return True

    start_date_str = config.get("start_dates", {}).get(current)
    if not start_date_str:
        return True

    start_date = datetime.fromisoformat(start_date_str)
    trial_days = PROXY_PROVIDERS[current]["trial_days"]
    expiry_date = start_date + timedelta(days=trial_days)

    return datetime.now() > expiry_date

def start_trial(provider_key):
    """Démarre un nouveau trial"""
    config = load_trial_config()

    config["current_provider"] = provider_key
    config["trials_used"].append(provider_key)
    config["start_dates"][provider_key] = datetime.now().isoformat()

    save_trial_config(config)

    provider = PROXY_PROVIDERS[provider_key]
    print(f"✅ Trial activé : {provider['name']}")
    print(f"📅 Durée : {provider['trial_days']} jours")
    print(f"🔗 Inscription : {provider['signup_url']}")
    print(f"📝 Format proxy : {provider['proxy_format']}")
    print(f"💡 Notes : {provider['notes']}")

def display_status():
    """Affiche le statut actuel des trials"""
    config = load_trial_config()

    print("\n" + "="*60)
    print("📊 STATUT DES ESSAIS GRATUITS DE PROXIES")
    print("="*60 + "\n")

    current = config.get("current_provider")

    if not current:
        print("❌ Aucun trial actif")
        print("\n🎯 Prochaine étape : Démarrer le premier trial\n")
        next_provider = get_next_provider(config)
        if next_provider:
            provider = PROXY_PROVIDERS[next_provider]
            print(f"📌 Prochain fournisseur recommandé : {provider['name']}")
            print(f"   - Durée : {provider['trial_days']} jours")
            print(f"   - Inscription : {provider['signup_url']}")
    else:
        provider = PROXY_PROVIDERS[current]
        start_date = datetime.fromisoformat(config["start_dates"][current])
        expiry_date = start_date + timedelta(days=provider["trial_days"])
        days_left = (expiry_date - datetime.now()).days

        print(f"✅ Trial actif : {provider['name']}")
        print(f"📅 Début : {start_date.strftime('%d/%m/%Y')}")
        print(f"⏳ Expire le : {expiry_date.strftime('%d/%m/%Y')}")
        print(f"⏰ Jours restants : {days_left}")

        if days_left <= 1:
            print(f"\n⚠️ ATTENTION : Le trial expire bientôt !")
            next_provider = get_next_provider(config)
            if next_provider:
                next_p = PROXY_PROVIDERS[next_provider]
                print(f"\n🎯 Prochain fournisseur à configurer : {next_p['name']}")
                print(f"   - Inscription : {next_p['signup_url']}")

    print("\n" + "-"*60)
    print("📋 HISTORIQUE DES TRIALS")
    print("-"*60 + "\n")

    for provider_key in config.get("trials_used", []):
        provider = PROXY_PROVIDERS[provider_key]
        start_date_str = config.get("start_dates", {}).get(provider_key)
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            print(f"✓ {provider['name']} - Utilisé du {start_date.strftime('%d/%m/%Y')} ({provider['trial_days']} jours)")

    # Trials restants
    used = set(config.get("trials_used", []))
    remaining = [k for k in PROXY_PROVIDERS.keys() if k not in used]

    if remaining:
        print("\n" + "-"*60)
        print("🎁 TRIALS DISPONIBLES")
        print("-"*60 + "\n")

        total_days = 0
        for provider_key in remaining:
            provider = PROXY_PROVIDERS[provider_key]
            total_days += provider['trial_days']
            print(f"• {provider['name']} : {provider['trial_days']} jours")

        print(f"\n💰 Total jours gratuits restants : {total_days} jours")
    else:
        print("\n❌ Tous les trials ont été utilisés")
        print("\n💡 Options :")
        print("   1. Installer en local avec votre IP résidentielle (GRATUIT)")
        print("   2. Acheter des proxies premium")
        print("   3. Continuer sans proxies (risque de détection)")

    print("\n" + "="*60 + "\n")

def generate_github_secrets_config(provider_key, credentials):
    """Génère la configuration pour GitHub Secrets"""
    provider = PROXY_PROVIDERS[provider_key]

    print("\n" + "="*60)
    print("⚙️ CONFIGURATION GITHUB SECRETS")
    print("="*60 + "\n")

    print("Allez dans : Settings → Secrets and variables → Actions\n")

    print("1. ENABLE_PROXY_ROTATION")
    print("   Value: true\n")

    print("2. PROXY_LIST")
    proxy_url = provider['proxy_format'].replace('username', credentials.get('username', 'USERNAME'))
    proxy_url = proxy_url.replace('password', credentials.get('password', 'PASSWORD'))
    proxy_url = proxy_url.replace('XXX', credentials.get('customer_id', 'XXX'))
    print(f'   Value: ["{proxy_url}"]\n')

    print("3. RANDOM_PROXY_SELECTION")
    print("   Value: false\n")

    print("4. PROXY_TIMEOUT")
    print("   Value: 15\n")

    print("="*60 + "\n")

def interactive_setup():
    """Mode interactif pour configurer un nouveau trial"""
    print("\n🚀 CONFIGURATION INTERACTIVE D'UN NOUVEAU TRIAL\n")

    config = load_trial_config()
    next_provider = get_next_provider(config)

    if not next_provider:
        print("❌ Tous les trials ont déjà été utilisés")
        return

    provider = PROXY_PROVIDERS[next_provider]

    print(f"📌 Fournisseur sélectionné : {provider['name']}")
    print(f"⏱️  Durée du trial : {provider['trial_days']} jours")
    print(f"🔗 URL d'inscription : {provider['signup_url']}")
    print(f"💡 Notes : {provider['notes']}\n")

    input("Appuyez sur Entrée après avoir créé votre compte...")

    print("\n📝 Entrez vos identifiants proxy :\n")

    if next_provider == "smartproxy":
        username = input("Username Smartproxy : ")
        password = input("Password Smartproxy : ")
        credentials = {"username": username, "password": password}

    elif next_provider == "brightdata":
        username = input("Username Bright Data (ex: brd-customer-XXX-zone-XXX) : ")
        password = input("Password Bright Data : ")
        credentials = {"username": username, "password": password}

    elif next_provider == "oxylabs":
        username = input("Username Oxylabs (ex: customer-USERNAME) : ")
        password = input("Password Oxylabs : ")
        credentials = {"username": username, "password": password}

    elif next_provider == "iproyal":
        username = input("Username IPRoyal : ")
        password = input("Password IPRoyal : ")
        credentials = {"username": username, "password": password}

    # Démarrer le trial
    start_trial(next_provider)

    # Générer la config GitHub Secrets
    generate_github_secrets_config(next_provider, credentials)

    print("\n✅ Configuration terminée !")
    print("\n🎯 Prochaines étapes :")
    print("   1. Copier les secrets ci-dessus dans GitHub")
    print("   2. Lancer un workflow avec DRY_RUN=true pour tester")
    print("   3. Vérifier les logs : chercher '🌐 Proxy rotation enabled'")
    print("   4. Si succès, passer en production (DRY_RUN=false)")

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 manage_proxy_trials.py status    # Afficher le statut")
        print("  python3 manage_proxy_trials.py setup     # Configuration interactive")
        print("  python3 manage_proxy_trials.py next      # Voir le prochain provider")
        return

    command = sys.argv[1]

    if command == "status":
        display_status()
    elif command == "setup":
        interactive_setup()
    elif command == "next":
        config = load_trial_config()
        next_provider = get_next_provider(config)
        if next_provider:
            provider = PROXY_PROVIDERS[next_provider]
            print(f"\n🎯 Prochain fournisseur : {provider['name']}")
            print(f"📅 Durée : {provider['trial_days']} jours")
            print(f"🔗 Inscription : {provider['signup_url']}")
            print(f"💡 Notes : {provider['notes']}\n")
        else:
            print("\n❌ Aucun trial disponible\n")
    else:
        print(f"❌ Commande inconnue : {command}")

if __name__ == "__main__":
    main()
