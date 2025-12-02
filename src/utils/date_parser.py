import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

class DateParsingService:
    """
    Service robust and lightweight for date parsing.
    Replaces heavy libraries like dateparser with optimized regexes per locale.
    """

    # Configuration per locale
    LOCALE_CONFIG: Dict[str, Any] = {
        "en": {
            # Matches: "Oct 24", "October 24", "24 Oct", "24 October"
            "pattern": r"(?P<m_first>(?P<month_1>[a-zA-Z]+)\.?\s+(?P<day_1>\d{1,2}))|(?P<d_first>(?P<day_2>\d{1,2})\s+(?P<month_2>[a-zA-Z]+)\.?)",
            "months": {
                "jan": 1, "january": 1,
                "feb": 2, "february": 2,
                "mar": 3, "march": 3,
                "apr": 4, "april": 4,
                "may": 5,
                "jun": 6, "june": 6,
                "jul": 7, "july": 7,
                "aug": 8, "august": 8,
                "sep": 9, "sept": 9, "september": 9,
                "oct": 10, "october": 10,
                "nov": 11, "november": 11,
                "dec": 12, "december": 12
            },
            "relative": {
                "today": 0,
                "yesterday": 1
            }
        },
        "fr": {
            # Matches: "le 24 oct", "24 octobre", "oct 24" (rare in FR but possible)
            "pattern": r"(?:le\s+)?(?P<d_first>(?P<day_2>\d{1,2})\s+(?P<month_2>[a-zA-Z\u00C0-\u00FF]+\.?))|(?P<m_first>(?P<month_1>[a-zA-Z\u00C0-\u00FF]+\.?)\s+(?P<day_1>\d{1,2}))",
            "months": {
                "jan": 1, "janv": 1, "janvier": 1,
                "fév": 2, "fev": 2, "février": 2, "fevrier": 2,
                "mar": 3, "mars": 3,
                "avr": 4, "avril": 4,
                "mai": 5,
                "juin": 6,
                "juil": 7, "juillet": 7,
                "aoû": 8, "aou": 8, "août": 8,
                "sep": 9, "sept": 9, "septembre": 9,
                "oct": 10, "octobre": 10,
                "nov": 11, "novembre": 11,
                "déc": 12, "dec": 12, "décembre": 12, "decembre": 12
            },
            "relative": {
                "aujourd'hui": 0,
                "aujourd’hui": 0,  # Handle curly apostrophe
                "hier": 1,
                "avant-hier": 2
            }
        }
    }

    @classmethod
    def parse_days_diff(cls, text: str, locale: str = 'en') -> Optional[int]:
        """
        Parses text to determine how many days have passed since the date.
        Returns:
            0 for today
            >0 for past days (late)
            None if parse failed or future date (upcoming)
        """
        text = text.lower().strip()
        config = cls.LOCALE_CONFIG.get(locale, cls.LOCALE_CONFIG['en'])

        # 1. Check relative keywords
        for key, val in config['relative'].items():
            if key in text:
                return val

        # 1b. Check relative "N days ago" (Locale independent numbers generally work, but let's be safe)
        # Simple regex for "5 days ago", "il y a 5 jours"
        ago_match = re.search(r"(\d+)\s*(?:days?|jours?)", text)
        if ago_match:
            return int(ago_match.group(1))

        # 2. Parse explicit date
        day, month = cls._extract_date_components(text, config)
        if day is None or month is None:
            # Fallback: Try all locales if 'en' failed (since LinkedIn might serve mixed content)
            if locale == 'en':
                return cls.parse_days_diff(text, locale='fr')
            return None

        return cls._calculate_delta(day, month)

    @classmethod
    def _extract_date_components(cls, text: str, config: Dict) -> Tuple[Optional[int], Optional[int]]:
        match = re.search(config['pattern'], text, re.IGNORECASE)
        if not match:
            return None, None

        day = None
        month_str = None

        # Logic to extract named groups depending on which side matched
        if match.group('m_first'):
            month_str = match.group('month_1')
            day = int(match.group('day_1'))
        elif match.group('d_first'):
            day = int(match.group('day_2'))
            month_str = match.group('month_2')

        if not month_str:
            return None, None

        # Normalize month string (remove dot)
        month_str = month_str.replace('.', '').lower()

        # Map to integer
        month = None
        # Exact match first
        if month_str in config['months']:
            month = config['months'][month_str]
        else:
            # Partial match (e.g., 'sept' in 'septembre')
            for key, val in config['months'].items():
                if key in month_str: # be careful with short keys matching inside others, but sorted keys might help?
                    # Dictionary order is insertion order in Python 3.7+.
                    # Generally 'months' has specific keys.
                    # Let's rely on the config having enough keys.
                    month = val
                    break

        return day, month

    @classmethod
    def _calculate_delta(cls, day: int, month: int) -> Optional[int]:
        """
        Calculates the difference in days between now and the given day/month.
        Handles year boundary (e.g. looking at Dec 31 when today is Jan 1).
        """
        now = datetime.now()
        current_year = now.year

        try:
            birthday_this_year = datetime(current_year, month, day)
        except ValueError:
            return None # Invalid date (e.g. Feb 30)

        delta = now - birthday_this_year

        # Case 1: Positive delta (Birthday was in the past this year)
        # e.g. Now: Nov 25, Birthday: Nov 23 -> delta = 2 days.
        if delta.days >= 0:
            return delta.days

        # Case 2: Negative delta (Birthday is in the future this year)
        # e.g. Now: Jan 2, Birthday: Dec 31.
        # Simple delta gives ~ -363 days.
        # But this might be a LATE birthday from LAST year.

        # Check if it was last year
        birthday_last_year = datetime(current_year - 1, month, day)
        delta_last = now - birthday_last_year

        # If it was reasonably recent (e.g. < 60 days ago), consider it Late.
        # If it was 300 days ago, it's probably just an upcoming birthday for next year (which we ignore).
        if 0 < delta_last.days < 60:
            return delta_last.days

        return None # Considered "Upcoming" (Future)
