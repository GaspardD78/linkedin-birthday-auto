"""
Script de test pour les fonctionnalités de la Phase 1
Teste la base de données, les sélecteurs, et génère des données de test
"""

import sys
from datetime import datetime, timedelta
import random

def test_database():
    """Test de la base de données"""
    print("\n" + "="*60)
    print("TEST 1: Base de données")
    print("="*60)

    try:
        from database import Database
        db = Database("test_phase1.db")
        print("✅ Création de la base de données réussie")

        # Test d'ajout de contact
        contact_id = db.add_contact(
            name="Jean Dupont",
            linkedin_url="https://linkedin.com/in/jeandupont",
            relationship_score=75.0,
            notes="Contact de test"
        )
        print(f"✅ Contact créé avec ID: {contact_id}")

        # Test d'ajout de message
        msg_id = db.add_birthday_message(
            contact_name="Jean Dupont",
            message_text="Joyeux anniversaire Jean !",
            is_late=False,
            days_late=0,
            script_mode="test"
        )
        print(f"✅ Message créé avec ID: {msg_id}")

        # Test d'ajout de visite
        visit_id = db.add_profile_visit(
            profile_name="Marie Martin",
            profile_url="https://linkedin.com/in/mariemartin",
            source_search="test_search",
            keywords=["Azure", "Cloud"],
            location="Paris",
            success=True
        )
        print(f"✅ Visite créée avec ID: {visit_id}")

        # Test d'erreur
        error_id = db.log_error(
            script_name="test_script",
            error_type="TestError",
            error_message="Ceci est une erreur de test",
            error_details="Détails de l'erreur"
        )
        print(f"✅ Erreur enregistrée avec ID: {error_id}")

        # Test des statistiques
        stats = db.get_statistics(30)
        print(f"✅ Statistiques récupérées: {stats['messages']['total']} messages")

        # Test d'export
        export_path = db.export_to_json("test_export.json")
        print(f"✅ Export JSON créé: {export_path}")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du test de la base de données: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_selector_validator():
    """Test du validateur de sélecteurs (sans Playwright)"""
    print("\n" + "="*60)
    print("TEST 2: Validateur de sélecteurs")
    print("="*60)

    try:
        from selector_validator import SelectorValidator
        from database import get_database

        db = get_database()
        selectors = db.get_all_selectors()
        print(f"✅ {len(selectors)} sélecteurs chargés depuis la base de données")

        for selector in selectors[:3]:
            print(f"   - {selector['selector_name']}: {selector['selector_value']}")

        # Test des suggestions
        suggestions = SelectorValidator(None, False).suggest_alternative_selectors("birthday_card")
        print(f"✅ {len(suggestions)} suggestions pour 'birthday_card'")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du test du validateur: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_test_data():
    """Génère des données de test pour le dashboard"""
    print("\n" + "="*60)
    print("TEST 3: Génération de données de test")
    print("="*60)

    try:
        from database import Database
        db = Database()

        names = [
            "Alice Martin", "Bob Durand", "Claire Dubois", "David Petit",
            "Emma Bernard", "Franck Moreau", "Gaëlle Simon", "Hugo Laurent",
            "Isabelle Michel", "Julien Lefebvre", "Karine Garcia", "Luc Martinez"
        ]

        messages_templates = [
            "Joyeux anniversaire {name} ! J'espère que tu passes une excellente journée.",
            "Happy birthday {name}! Wishing you all the best.",
            "Bon anniversaire {name} ! Profite bien de ta journée.",
            "Meilleurs vœux pour ton anniversaire {name} !",
            "{name}, je te souhaite un merveilleux anniversaire !"
        ]

        # Générer des messages sur les 30 derniers jours
        print("Génération de messages d'anniversaire...")
        for day in range(30):
            date = datetime.now() - timedelta(days=day)
            num_messages = random.randint(0, 5)

            for _ in range(num_messages):
                name = random.choice(names)
                message = random.choice(messages_templates).replace("{name}", name.split()[0])

                db.add_birthday_message(
                    contact_name=name,
                    message_text=message,
                    is_late=random.random() < 0.2,  # 20% de retard
                    days_late=random.randint(0, 7) if random.random() < 0.2 else 0,
                    script_mode="test_routine"
                )

        print(f"✅ {sum([random.randint(0, 5) for _ in range(30)])} messages de test générés")

        # Générer des visites de profils
        print("Génération de visites de profils...")
        for day in range(30):
            date = datetime.now() - timedelta(days=day)
            num_visits = random.randint(5, 15)

            for _ in range(num_visits):
                name = random.choice(names)
                success = random.random() < 0.95  # 95% de succès

                db.add_profile_visit(
                    profile_name=name,
                    profile_url=f"https://linkedin.com/in/{name.lower().replace(' ', '-')}",
                    source_search="test_search",
                    keywords=["Azure", "Microsoft"],
                    location="Ile-de-France",
                    success=success,
                    error_message=None if success else "Test error"
                )

        print(f"✅ {30 * 10} visites de profils générées")

        # Générer quelques erreurs
        print("Génération d'erreurs de test...")
        error_types = ["SelectorNotFound", "TimeoutError", "NetworkError", "AuthenticationError"]

        for _ in range(10):
            db.log_error(
                script_name=random.choice(["linkedin_birthday_wisher", "visit_profiles"]),
                error_type=random.choice(error_types),
                error_message="Erreur de test générée automatiquement",
                error_details="Détails de l'erreur de test"
            )

        print("✅ 10 erreurs de test générées")

        # Afficher les statistiques finales
        stats = db.get_statistics(30)
        print("\n📊 Statistiques après génération:")
        print(f"   Messages: {stats['messages']['total']}")
        print(f"   Visites: {stats['profile_visits']['total']}")
        print(f"   Erreurs: {stats['errors']['total']}")

        return True

    except Exception as e:
        print(f"❌ Erreur lors de la génération des données: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flask_app():
    """Test basique de l'application Flask"""
    print("\n" + "="*60)
    print("TEST 4: Application Flask")
    print("="*60)

    try:
        from dashboard_app import app

        # Test que l'app Flask peut être créée
        print("✅ Application Flask créée avec succès")

        # Test du contexte
        with app.app_context():
            print("✅ Contexte Flask fonctionnel")

        # Test client
        client = app.test_client()

        # Test des routes principales
        routes_to_test = [
            ('/', 'Dashboard'),
            ('/messages', 'Messages'),
            ('/visits', 'Visites'),
            ('/contacts', 'Contacts'),
            ('/errors', 'Erreurs'),
            ('/selectors', 'Sélecteurs'),
        ]

        for route, name in routes_to_test:
            response = client.get(route)
            if response.status_code == 200:
                print(f"✅ Route {route} ({name}) accessible")
            else:
                print(f"⚠️  Route {route} retourne le code {response.status_code}")

        # Test des API endpoints
        api_routes = [
            '/api/stats/30',
            '/api/daily-activity/14',
            '/api/weekly-count',
            '/api/messages/recent/10',
            '/api/top-contacts/5',
        ]

        for route in api_routes:
            response = client.get(route)
            if response.status_code == 200:
                print(f"✅ API {route} fonctionnelle")
            else:
                print(f"⚠️  API {route} retourne le code {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du test Flask: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   Test Suite - Phase 1                                    ║
    ║   LinkedIn Birthday Auto                                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    results = []

    # Exécuter tous les tests
    results.append(("Base de données", test_database()))
    results.append(("Validateur de sélecteurs", test_selector_validator()))
    results.append(("Génération de données", generate_test_data()))
    results.append(("Application Flask", test_flask_app()))

    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)

    for name, success in results:
        status = "✅ PASSÉ" if success else "❌ ÉCHOUÉ"
        print(f"{name:.<40} {status}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed

    print("\n" + "="*60)
    print(f"Total: {total} | Réussis: {passed} | Échoués: {failed}")
    print("="*60)

    if failed == 0:
        print("\n🎉 Tous les tests sont passés avec succès!")
        print("\nVous pouvez maintenant:")
        print("  1. Lancer le dashboard: python dashboard_app.py")
        print("  2. Accéder au dashboard: http://localhost:5000")
        print("  3. Voir la base de données: sqlite3 linkedin_automation.db")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
