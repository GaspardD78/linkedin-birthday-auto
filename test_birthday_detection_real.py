#!/usr/bin/env python3
"""
Tests de détection d'anniversaires basés sur les screenshots réels LinkedIn (18 Nov 2025).

Ce fichier teste la nouvelle logique de détection améliorée qui distingue:
- Les anniversaires du jour (bouton: "Je vous souhaite un très joyeux anniversaire.")
- Les anniversaires en retard (bouton: "Joyeux anniversaire avec un peu de retard !")
- Et parse les dates explicites comme "le 10 nov."
"""

import re
import logging
from datetime import datetime
from typing import Optional

# Configuration du logging pour les tests
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')


def extract_days_from_date(card_text: str, reference_date: datetime = None) -> Optional[int]:
    """
    Extrait le nombre de jours entre une date mentionnée dans le texte et une date de référence.

    Args:
        card_text: Le texte de la carte d'anniversaire
        reference_date: Date de référence (par défaut: datetime.now())

    Returns:
        int: Nombre de jours de différence (0 = aujourd'hui, positif = passé)
        None: Si aucune date n'a pu être extraite
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Pattern pour capturer "le X mois" (ex: "le 10 nov.")
    pattern = r'le (\d{1,2}) (janv?\.?|févr?\.?|mars?\.?|avr\.?|mai\.?|juin?\.?|juil\.?|août?\.?|sept?\.?|oct\.?|nov\.?|déc\.?|january?|february?|march?|april?|may|june?|july?|august?|september?|october?|november?|december?)'

    match = re.search(pattern, card_text, re.IGNORECASE)

    if not match:
        return None

    day = int(match.group(1))
    month_str = match.group(2).lower()

    # Mapping mois français → numéro
    month_mapping = {
        'janv': 1, 'janvier': 1, 'january': 1,
        'févr': 2, 'fev': 2, 'février': 2, 'february': 2,
        'mars': 3, 'march': 3,
        'avr': 4, 'avril': 4, 'april': 4,
        'mai': 5, 'may': 5,
        'juin': 6, 'june': 6,
        'juil': 7, 'juillet': 7, 'july': 7,
        'août': 8, 'aout': 8, 'august': 8,
        'sept': 9, 'septembre': 9, 'september': 9,
        'oct': 10, 'octobre': 10, 'october': 10,
        'nov': 11, 'novembre': 11, 'november': 11,
        'déc': 12, 'dec': 12, 'décembre': 12, 'december': 12
    }

    # Retirer les points et trouver le mois
    month_key = month_str.rstrip('.')
    month = None

    for key, value in month_mapping.items():
        if month_key.startswith(key):
            month = value
            break

    if month is None:
        logging.warning(f"⚠️ Mois non reconnu: '{month_str}'")
        return None

    # Construire la date de l'anniversaire
    current_year = reference_date.year
    try:
        birthday_date = datetime(current_year, month, day)
    except ValueError:
        logging.error(f"⚠️ Date invalide: jour={day}, mois={month}")
        return None

    # Si la date est dans le futur, c'était l'année dernière
    if birthday_date > reference_date:
        birthday_date = datetime(current_year - 1, month, day)

    # Calculer la différence en jours
    delta = reference_date - birthday_date
    days_diff = delta.days

    logging.debug(f"📅 Date extraite: {day}/{month} → {days_diff} jour(s) de différence")

    return days_diff


def simulate_classification(card_text: str, reference_date: datetime = None) -> tuple[str, int]:
    """
    Simule la classification d'une carte d'anniversaire.

    Args:
        card_text: Le texte de la carte (minuscules)
        reference_date: Date de référence pour les calculs (défaut: maintenant)

    Returns:
        tuple[str, int]: (type, days_late)
    """
    if reference_date is None:
        reference_date = datetime.now()

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 1 : Analyser le texte du bouton
    # ═══════════════════════════════════════════════════════════

    button_text_today = "je vous souhaite un très joyeux anniversaire"
    button_text_late = "joyeux anniversaire avec un peu de retard"

    if button_text_today in card_text:
        logging.info(f"✓ Anniversaire du jour détecté (bouton standard)")
        return 'today', 0

    if button_text_late in card_text:
        logging.info(f"✓ Anniversaire en retard détecté (bouton retard)")
        days = extract_days_from_date(card_text, reference_date)
        if days is not None:
            if 1 <= days <= 10:
                logging.info(f"→ {days} jour(s) de retard - Classé comme 'late'")
                return 'late', days
            else:
                logging.info(f"→ {days} jour(s) de retard - Trop ancien, classé comme 'ignore'")
                return 'ignore', days
        else:
            logging.warning("⚠️ Retard détecté mais date non parsable, estimation à 2 jours")
            return 'late', 2

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 2 : Détection explicite "aujourd'hui"
    # ═══════════════════════════════════════════════════════════

    today_keywords = [
        'aujourd\'hui',
        'aujourdhui',
        'c\'est aujourd\'hui',
        'today',
        'is today'
    ]

    for keyword in today_keywords:
        if keyword in card_text:
            logging.info(f"✓ Anniversaire du jour détecté (mot-clé: '{keyword}')")
            return 'today', 0

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 3 : Parser la date explicite
    # ═══════════════════════════════════════════════════════════

    days = extract_days_from_date(card_text, reference_date)
    if days is not None:
        if days == 0:
            logging.info(f"✓ Date parsée = aujourd'hui")
            return 'today', 0
        elif 1 <= days <= 10:
            logging.info(f"✓ Date parsée = {days} jour(s) de retard")
            return 'late', days
        else:
            logging.info(f"→ Date parsée = {days} jour(s) - Trop ancien")
            return 'ignore', days

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 4 : Regex classique
    # ═══════════════════════════════════════════════════════════

    match_fr = re.search(r'il y a (\d+) jours?', card_text)
    match_en = re.search(r'(\d+) days? ago', card_text)

    if match_fr or match_en:
        days_late = int(match_fr.group(1) if match_fr else match_en.group(1))
        if 1 <= days_late <= 10:
            logging.info(f"✓ Regex détectée: {days_late} jour(s) de retard")
            return 'late', days_late
        else:
            logging.info(f"→ Regex: {days_late} jours - Trop ancien")
            return 'ignore', days_late

    # ═══════════════════════════════════════════════════════════
    # CAS PAR DÉFAUT
    # ═══════════════════════════════════════════════════════════

    time_keywords = ['retard', 'il y a', 'ago', 'récent']
    has_time_keyword = any(kw in card_text for kw in time_keywords)

    if not has_time_keyword:
        logging.info("→ Aucun indicateur de retard, classification: 'today'")
        return 'today', 0
    else:
        logging.warning("→ Indicateurs temporels ambigus, classification: 'ignore'")
        return 'ignore', 0


def test_with_real_linkedin_data():
    """
    Test basé sur les screenshots réels du 18 nov 2025
    """

    # Date de référence : 18 novembre 2025
    reference_date = datetime(2025, 11, 18)

    test_cases = [
        # Format LinkedIn pour anniversaires en retard (screenshot 1)
        {
            'text': "Frédéric LEDIEU\nCélébrez l'anniversaire récent de Frédéric le 10 nov.\nJoyeux anniversaire avec un peu de retard !",
            'expected_type': 'late',
            'expected_days': 8,  # 18 nov - 10 nov = 8 jours
            'description': 'Anniversaire récent du 10 nov (screenshot 1 - Frédéric)'
        },

        # Format LinkedIn pour anniversaires du jour (screenshot 2)
        {
            'text': "Céline Liu\nCélébrez l'anniversaire de Céline aujourd'hui\nJe vous souhaite un très joyeux anniversaire.",
            'expected_type': 'today',
            'expected_days': 0,
            'description': 'Anniversaire du jour (screenshot 2 - Céline)'
        },

        # Autres cas du screenshot 2
        {
            'text': "Philippe Dinard\nCélébrez l'anniversaire de Philippe aujourd'hui\nJe vous souhaite un très joyeux anniversaire.",
            'expected_type': 'today',
            'expected_days': 0,
            'description': 'Anniversaire du jour (screenshot 2 - Philippe)'
        },

        {
            'text': "Romuald Bougé\nCélébrez l'anniversaire récent de Romuald le 10 nov.\nJoyeux anniversaire avec un peu de retard !",
            'expected_type': 'late',
            'expected_days': 8,
            'description': 'Anniversaire récent du 10 nov (screenshot 1 - Romuald)'
        },

        # Test de cas limites
        {
            'text': "Jean Dupont\nCélébrez l'anniversaire récent de Jean le 8 nov.\nJoyeux anniversaire avec un peu de retard !",
            'expected_type': 'late',
            'expected_days': 10,  # 18 nov - 8 nov = 10 jours (limite)
            'description': 'Anniversaire à la limite (10 jours)'
        },

        {
            'text': "Marie Martin\nCélébrez l'anniversaire récent de Marie le 7 nov.\nJoyeux anniversaire avec un peu de retard !",
            'expected_type': 'ignore',
            'expected_days': 11,  # 18 nov - 7 nov = 11 jours (trop ancien)
            'description': 'Anniversaire trop ancien (11 jours) - devrait être ignoré'
        },

        # Test avec mot-clé "aujourd'hui" sans bouton
        {
            'text': "Test User\nCélébrez l'anniversaire de Test aujourd'hui",
            'expected_type': 'today',
            'expected_days': 0,
            'description': 'Détection par mot-clé "aujourd\'hui" sans texte de bouton'
        },
    ]

    print("═══════════════════════════════════════════════════")
    print("🧪 TEST AVEC DONNÉES RÉELLES LINKEDIN (18 NOV 2025)")
    print("═══════════════════════════════════════════════════\n")

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test #{i}: {test['description']}")
        print(f"{'='*60}")

        result_type, result_days = simulate_classification(
            test['text'].lower(),
            reference_date=reference_date
        )

        success = (result_type == test['expected_type'] and
                  result_days == test['expected_days'])

        status = "✅ PASS" if success else "❌ FAIL"

        print(f"\n{status}")
        print(f"  Attendu: type='{test['expected_type']}', jours={test['expected_days']}")
        print(f"  Obtenu:  type='{result_type}', jours={result_days}")

        if not success:
            print(f"\n  ⚠️ ERREUR - Texte analysé:")
            print(f"     {test['text'][:100]}...")

        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "═"*60)
    print(f"📊 Résultats: {passed}/{len(test_cases)} tests réussis")
    if failed > 0:
        print(f"   ❌ {failed} test(s) échoué(s)")
    else:
        print(f"   ✅ Tous les tests sont passés avec succès!")
    print("═"*60 + "\n")

    return passed == len(test_cases)


if __name__ == "__main__":
    all_passed = test_with_real_linkedin_data()
    exit(0 if all_passed else 1)
