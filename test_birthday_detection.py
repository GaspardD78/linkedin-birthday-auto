#!/usr/bin/env python3
"""
Test unitaire pour la détection des anniversaires LinkedIn.

Ce script teste la logique de classification des anniversaires sans dépendance à Playwright.
Utile pour valider les améliorations de la fonction get_birthday_type().
"""

import re


def simulate_classification(card_text: str) -> tuple[str, int]:
    """
    Simule la logique de get_birthday_type() pour les tests unitaires.

    Cette fonction reproduit la même logique que linkedin_birthday_wisher.py
    mais sans dépendance à Playwright.

    Args:
        card_text: Texte de la carte d'anniversaire (déjà en minuscules)

    Returns:
        tuple[str, int]: (type, days_late)
    """
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 1: Vérifier explicitement "aujourd'hui" / "today"
    # ═══════════════════════════════════════════════════════════
    today_keywords_fr = ['aujourd\'hui', 'aujourdhui', 'c\'est aujourd\'hui']
    today_keywords_en = ['today', 'is today', '\'s birthday is today']

    for keyword in today_keywords_fr + today_keywords_en:
        if keyword in card_text:
            return 'today', 0

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 2: Détecter "hier" / "yesterday" (1 jour de retard)
    # ═══════════════════════════════════════════════════════════
    yesterday_keywords = ['hier', 'c\'était hier', 'yesterday', 'was yesterday']

    for keyword in yesterday_keywords:
        if keyword in card_text:
            return 'late', 1

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 3: Extraire le nombre de jours via regex (multi-langue)
    # ═══════════════════════════════════════════════════════════

    # Pattern français: "il y a X jour(s)"
    match_fr = re.search(r'il y a (\d+) jours?', card_text)

    # Pattern anglais: "X day(s) ago"
    match_en = re.search(r'(\d+) days? ago', card_text)

    if match_fr or match_en:
        days = int(match_fr.group(1) if match_fr else match_en.group(1))
        return ('late', days) if 1 <= days <= 7 else ('ignore', days)

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 4: Détecter les indicateurs de retard génériques
    # ═══════════════════════════════════════════════════════════
    generic_late_keywords = [
        'avec un peu de retard',
        'avec du retard',
        'en retard',
        'belated',
        'a bit late',
        'little late'
    ]

    for keyword in generic_late_keywords:
        if keyword in card_text:
            return 'ignore', 0

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 5: Validation de la structure de la carte
    # ═══════════════════════════════════════════════════════════
    birthday_indicators = [
        'anniversaire', 'birthday', 'célébrez', 'celebrate',
        'say happy birthday', 'souhaitez', 'wish'
    ]

    has_birthday_indicator = any(indicator in card_text for indicator in birthday_indicators)

    if not has_birthday_indicator:
        return 'ignore', 0

    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 6: Cas par défaut - Classification conservatrice
    # ═══════════════════════════════════════════════════════════
    time_keywords = ['il y a', 'ago', 'hier', 'yesterday', 'retard', 'belated', 'late']
    has_time_keyword = any(keyword in card_text for keyword in time_keywords)

    if not has_time_keyword:
        return 'today', 0
    else:
        return 'ignore', 0


def test_birthday_type_detection():
    """
    Teste la détection des différents types d'anniversaires avec des exemples réels.
    """
    test_cases = [
        # (texte_carte, type_attendu, jours_attendus, description)

        # === ANNIVERSAIRES DU JOUR ===
        ("Célébrez l'anniversaire de Jean aujourd'hui", "today", 0, "FR: aujourd'hui basique"),
        ("C'est aujourd'hui l'anniversaire de Marie", "today", 0, "FR: c'est aujourd'hui"),
        ("Today is Sophie's birthday", "today", 0, "EN: today basique"),
        ("Sophie's birthday is today", "today", 0, "EN: birthday is today"),
        ("Souhaitez un joyeux anniversaire à Paul", "today", 0, "FR: pas de mot-clé temporel"),

        # === HIER (1 JOUR) ===
        ("L'anniversaire de Paul était hier", "late", 1, "FR: hier basique"),
        ("C'était hier l'anniversaire de Laura", "late", 1, "FR: c'était hier"),
        ("Yesterday was Alex's birthday", "late", 1, "EN: yesterday basique"),
        ("Emma's birthday was yesterday", "late", 1, "EN: was yesterday"),

        # === RETARDS QUANTIFIÉS (2-7 JOURS) ===
        ("Il y a 2 jours - Anniversaire de Lucas", "late", 2, "FR: il y a 2 jours"),
        ("Il y a 3 jours - Souhaitez un joyeux anniversaire", "late", 3, "FR: il y a 3 jours"),
        ("Il y a 4 jours - Anniversaire de Thomas", "late", 4, "FR: il y a 4 jours"),
        ("Il y a 5 jours - Marie célèbre son anniversaire", "late", 5, "FR: il y a 5 jours"),
        ("Il y a 6 jours - Anniversaire d'Éric", "late", 6, "FR: il y a 6 jours"),
        ("Il y a 7 jours - Joyeux anniversaire Sarah", "late", 7, "FR: il y a 7 jours"),
        ("Il y a 1 jour - Anniversaire", "late", 1, "FR: il y a 1 jour (singulier)"),

        ("2 days ago - Emma's birthday", "late", 2, "EN: 2 days ago"),
        ("3 days ago - Happy birthday John", "late", 3, "EN: 3 days ago"),
        ("4 days ago - Birthday celebration", "late", 4, "EN: 4 days ago"),
        ("5 days ago - Say happy birthday", "late", 5, "EN: 5 days ago"),
        ("6 days ago - Mike's birthday", "late", 6, "EN: 6 days ago"),
        ("7 days ago - Celebrate with Anna", "late", 7, "EN: 7 days ago"),
        ("1 day ago - Birthday wishes", "late", 1, "EN: 1 day ago (singulier)"),

        # === IGNORÉS (>7 JOURS) ===
        ("Il y a 8 jours - Anniversaire", "ignore", 8, "FR: 8 jours (trop ancien)"),
        ("Il y a 10 jours - Joyeux anniversaire", "ignore", 10, "FR: 10 jours (trop ancien)"),
        ("Il y a 30 jours - Célébrez", "ignore", 30, "FR: 30 jours (très ancien)"),
        ("8 days ago - Birthday", "ignore", 8, "EN: 8 days ago (trop ancien)"),
        ("15 days ago - Happy birthday", "ignore", 15, "EN: 15 days ago (très ancien)"),

        # === RETARDS GÉNÉRIQUES (non quantifiables) ===
        ("Avec un peu de retard - Anniversaire de Thomas", "ignore", 0, "FR: retard générique"),
        ("Souhaitez avec du retard un anniversaire", "ignore", 0, "FR: avec du retard"),
        ("En retard - Célébrez l'anniversaire", "ignore", 0, "FR: en retard"),
        ("Belated birthday wishes for Sarah", "ignore", 0, "EN: belated"),
        ("A bit late - Happy birthday", "ignore", 0, "EN: a bit late"),
        ("Say happy birthday a little late", "ignore", 0, "EN: little late"),

        # === CAS LIMITES ===
        ("Célébrez aujourd'hui", "today", 0, "Sans mot 'anniversaire' mais avec célébrez"),
        ("Say happy birthday", "today", 0, "EN: phrase complète sans temporel"),
        ("Wish John a happy birthday", "today", 0, "EN: wish sans temporel"),
        ("", "ignore", 0, "Texte vide"),
        ("Bonjour comment allez-vous", "ignore", 0, "Pas un anniversaire"),
        ("Il y a longtemps anniversaire", "ignore", 0, "Mot-clé temporel mais pas de nombre"),
    ]

    print("═══════════════════════════════════════════════════")
    print("🧪 TEST DE DÉTECTION DES ANNIVERSAIRES")
    print("═══════════════════════════════════════════════════\n")

    passed = 0
    failed = 0
    failed_tests = []

    for i, (text, expected_type, expected_days, description) in enumerate(test_cases, 1):
        # Convertir en minuscules pour simuler la fonction réelle
        result_type, result_days = simulate_classification(text.lower())

        is_pass = (result_type == expected_type and result_days == expected_days)
        status = "✅ PASS" if is_pass else "❌ FAIL"

        print(f"Test #{i:2d}: {status} - {description}")

        if not is_pass:
            print(f"  Texte: '{text}'")
            print(f"  Attendu: type='{expected_type}', jours={expected_days}")
            print(f"  Obtenu:  type='{result_type}', jours={result_days}")
            print()
            failed_tests.append({
                'index': i,
                'description': description,
                'text': text,
                'expected': (expected_type, expected_days),
                'got': (result_type, result_days)
            })

        if is_pass:
            passed += 1
        else:
            failed += 1

    print("\n═══════════════════════════════════════════════════")
    print(f"📊 RÉSULTATS FINAUX")
    print("═══════════════════════════════════════════════════")
    print(f"Total de tests: {len(test_cases)}")
    print(f"✅ Réussis: {passed} ({passed*100//len(test_cases)}%)")
    print(f"❌ Échoués: {failed} ({failed*100//len(test_cases)}%)")
    print("═══════════════════════════════════════════════════")

    if failed_tests:
        print("\n⚠️ TESTS ÉCHOUÉS - DÉTAILS:")
        print("═══════════════════════════════════════════════════")
        for test in failed_tests:
            print(f"\nTest #{test['index']}: {test['description']}")
            print(f"  Texte: '{test['text']}'")
            print(f"  Attendu: {test['expected']}")
            print(f"  Obtenu:  {test['got']}")

    return passed == len(test_cases)


def test_regex_patterns():
    """
    Teste spécifiquement les patterns regex pour la détection des jours.
    """
    print("\n═══════════════════════════════════════════════════")
    print("🔍 TEST DES PATTERNS REGEX")
    print("═══════════════════════════════════════════════════\n")

    regex_tests = [
        # (texte, pattern_name, should_match, expected_days)
        ("il y a 2 jours", "FR plural", True, 2),
        ("il y a 1 jour", "FR singular", True, 1),
        ("il y a 10 jours", "FR 2 digits", True, 10),
        ("2 days ago", "EN plural", True, 2),
        ("1 day ago", "EN singular", True, 1),
        ("15 days ago", "EN 2 digits", True, 15),
        ("days ago", "EN no number", False, None),
        ("il y a jours", "FR no number", False, None),
    ]

    pattern_fr = r'il y a (\d+) jours?'
    pattern_en = r'(\d+) days? ago'

    for text, name, should_match, expected_days in regex_tests:
        match_fr = re.search(pattern_fr, text.lower())
        match_en = re.search(pattern_en, text.lower())

        matched = match_fr or match_en

        if matched:
            days = int((match_fr or match_en).group(1))
            result = f"✅ Match: {days} jour(s)"
            status = "✅ PASS" if (should_match and days == expected_days) else "❌ FAIL"
        else:
            result = "❌ Pas de match"
            status = "✅ PASS" if not should_match else "❌ FAIL"

        print(f"{status} - {name:15s}: '{text}' -> {result}")

    print()


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════╗")
    print("║   TEST UNITAIRE - DÉTECTION D'ANNIVERSAIRES      ║")
    print("║         linkedin_birthday_wisher.py              ║")
    print("╚═══════════════════════════════════════════════════╝\n")

    # Tester les regex d'abord
    test_regex_patterns()

    # Tester la classification complète
    all_passed = test_birthday_type_detection()

    print("\n╔═══════════════════════════════════════════════════╗")
    if all_passed:
        print("║              ✅ TOUS LES TESTS PASSENT            ║")
    else:
        print("║           ❌ CERTAINS TESTS ONT ÉCHOUÉ            ║")
    print("╚═══════════════════════════════════════════════════╝\n")

    exit(0 if all_passed else 1)
