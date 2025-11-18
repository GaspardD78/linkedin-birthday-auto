"""
LinkedIn Birthday Bot - Debug Utilities
Advanced debugging, monitoring, and error detection system
"""

import os
import json
import time
import logging
import smtplib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from playwright.sync_api import Page


class DebugScreenshotManager:
    """Gestionnaire de screenshots pour debugging"""

    def __init__(self, debug_dir="debug_screenshots"):
        self.debug_dir = debug_dir
        os.makedirs(debug_dir, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def capture(self, page: Page, step_name: str, error: bool = False) -> Optional[str]:
        """
        Capture screenshot avec timestamp et contexte

        Args:
            page: Page Playwright
            step_name: Nom de l'étape actuelle
            error: Si True, préfixe avec ERROR

        Returns:
            Chemin du fichier screenshot ou None si échec
        """
        prefix = "ERROR" if error else "DEBUG"
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{prefix}_{self.session_id}_{timestamp}_{step_name}.png"
        path = os.path.join(self.debug_dir, filename)

        try:
            page.screenshot(path=path, full_page=True)
            logging.info(f"📸 Screenshot saved: {filename}")
            return path
        except Exception as e:
            logging.error(f"Failed to capture screenshot: {e}")
            return None

    def capture_element(self, page: Page, selector: str, step_name: str) -> Optional[str]:
        """
        Capture uniquement un élément spécifique

        Args:
            page: Page Playwright
            selector: Sélecteur CSS de l'élément
            step_name: Nom de l'étape

        Returns:
            Chemin du fichier screenshot ou None
        """
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"ELEMENT_{self.session_id}_{timestamp}_{step_name}.png"
        path = os.path.join(self.debug_dir, filename)

        try:
            element = page.locator(selector).first
            if element.count() > 0:
                element.screenshot(path=path)
                logging.info(f"📸 Element screenshot saved: {filename}")
                return path
            else:
                logging.warning(f"Element {selector} not found for screenshot")
                return None
        except Exception as e:
            logging.warning(f"Could not capture element {selector}: {e}")
            return None


class DOMStructureValidator:
    """Valide que les sélecteurs LinkedIn sont toujours valides"""

    CRITICAL_SELECTORS = {
        'birthday_card': "div[role='listitem']",
        'message_button': 'a[aria-label*="Envoyer un message"], a[href*="/messaging/compose"], button:has-text("Message")',
        'message_box': "div.msg-form__contenteditable[role='textbox']",
        'send_button': "button.msg-form__send-button",
        'profile_avatar': "img.global-nav__me-photo",
    }

    def __init__(self, page: Page):
        self.page = page
        self.validation_results: Dict[str, Dict[str, Any]] = {}

    def validate_all_selectors(self, screenshot_mgr: Optional[DebugScreenshotManager] = None) -> bool:
        """
        Vérifie tous les sélecteurs critiques

        Args:
            screenshot_mgr: Gestionnaire de screenshots optionnel

        Returns:
            True si tous les sélecteurs sont valides
        """
        logging.info("🔍 Validating DOM structure...")
        all_valid = True

        for name, selector in self.CRITICAL_SELECTORS.items():
            try:
                count = self.page.locator(selector).count()
                is_visible = False

                if count > 0:
                    try:
                        is_visible = self.page.locator(selector).first.is_visible(timeout=5000)
                    except Exception:
                        is_visible = False

                self.validation_results[name] = {
                    'selector': selector,
                    'found': count > 0,
                    'visible': is_visible,
                    'count': count,
                    'status': '✅' if count > 0 else '⚠️'
                }

                status_emoji = '✅' if count > 0 else '⚠️'
                logging.info(f"  {status_emoji} {name}: found {count} elements (visible: {is_visible})")

            except Exception as e:
                self.validation_results[name] = {
                    'selector': selector,
                    'found': False,
                    'error': str(e),
                    'status': '❌'
                }
                logging.error(f"  ❌ {name}: FAILED - {e}")
                all_valid = False

                # Capture screenshot de l'état actuel
                if screenshot_mgr:
                    screenshot_mgr.capture(self.page, f"selector_failed_{name}", error=True)

        return all_valid

    def export_validation_report(self, filepath: str = "dom_validation_report.json") -> Dict[str, Any]:
        """
        Exporte un rapport JSON des validations

        Args:
            filepath: Chemin du fichier de rapport

        Returns:
            Dictionnaire du rapport
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'selectors': self.validation_results,
            'overall_status': 'PASS' if all(v['found'] for v in self.validation_results.values()) else 'FAIL'
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logging.info(f"📄 Validation report saved: {filepath}")
        return report


class LinkedInPolicyDetector:
    """Détecte les restrictions et changements de politique LinkedIn"""

    WARNING_INDICATORS = {
        'captcha': ["captcha", "verify you're human", "security check", "vérifiez que vous"],
        'rate_limit': ["you've reached", "slow down", "try again later", "too many", "limite atteinte"],
        'restriction': ["restricted", "suspended", "violation", "unusual activity", "restreint", "suspendu"],
        'login_issue': ["sign in", "password", "verify your identity", "connexion", "mot de passe"],
    }

    def __init__(self, page: Page):
        self.page = page

    def check_for_restrictions(self, screenshot_mgr: Optional[DebugScreenshotManager] = None) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Détecte si LinkedIn a affiché des avertissements

        Args:
            screenshot_mgr: Gestionnaire de screenshots optionnel

        Returns:
            Tuple (is_ok: bool, detected_issues: List)
        """
        logging.info("🚨 Checking for LinkedIn restrictions...")

        try:
            # Récupère tout le texte visible de la page
            page_text = self.page.inner_text('body', timeout=5000).lower()

            detected_issues = []

            for issue_type, keywords in self.WARNING_INDICATORS.items():
                for keyword in keywords:
                    if keyword in page_text:
                        detected_issues.append({
                            'type': issue_type,
                            'keyword': keyword,
                            'severity': 'CRITICAL' if issue_type in ['captcha', 'restriction'] else 'WARNING'
                        })
                        logging.error(f"  🚨 {issue_type.upper()} detected: '{keyword}' found in page")

            if detected_issues:
                # Capture screenshot de l'alerte
                if screenshot_mgr:
                    screenshot_mgr.capture(self.page, "policy_restriction_detected", error=True)

                # Exporte les détails
                self._export_restriction_report(detected_issues)
                return False, detected_issues

            logging.info("  ✅ No restrictions detected")
            return True, []

        except Exception as e:
            logging.error(f"Failed to check restrictions: {e}")
            return True, []  # On assume que c'est OK si on ne peut pas vérifier

    def _export_restriction_report(self, issues: List[Dict[str, str]], filepath: str = "restriction_alert.json"):
        """
        Exporte un rapport d'alerte

        Args:
            issues: Liste des problèmes détectés
            filepath: Chemin du fichier de rapport
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'issues': issues,
            'action_required': 'STOP_SCRIPT' if any(i['severity'] == 'CRITICAL' for i in issues) else 'REVIEW'
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logging.critical(f"🚨 Restriction report saved: {filepath}")

    def check_message_sent_successfully(self) -> Optional[bool]:
        """
        Vérifie si le message a bien été envoyé (pas d'erreur silencieuse)

        Returns:
            True si succès, False si échec, None si incertain
        """
        try:
            # Cherche des indicateurs de succès
            success_indicators = [
                "div.msg-overlay-bubble-header__title:has-text('Message sent')",
                "div.artdeco-toast-item--success",
                "span:has-text('Sent')",
                "span:has-text('Envoyé')"
            ]

            for indicator in success_indicators:
                if self.page.locator(indicator).count() > 0:
                    logging.info("  ✅ Message send confirmation detected")
                    return True

            # Cherche des indicateurs d'échec
            error_indicators = [
                "div.artdeco-toast-item--error",
                "span:has-text('failed')",
                "span:has-text('try again')",
                "span:has-text('échec')"
            ]

            for indicator in error_indicators:
                if self.page.locator(indicator).count() > 0:
                    logging.error("  ❌ Message send error detected")
                    return False

            logging.debug("  ⚠️ No clear send confirmation found")
            return None

        except Exception as e:
            logging.error(f"Could not verify message send status: {e}")
            return None


class EnhancedLogger:
    """Logger avec contexte additionnel pour debugging"""

    def __init__(self, log_file: str = "linkedin_bot_detailed.log"):
        self.log_file = log_file

        # Configure un handler de fichier supplémentaire
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

    @staticmethod
    def log_page_state(page: Page, context: str = "") -> Optional[Dict[str, Any]]:
        """
        Log l'état complet de la page

        Args:
            page: Page Playwright
            context: Contexte additionnel

        Returns:
            Dictionnaire d'informations ou None
        """
        try:
            info = {
                'url': page.url,
                'title': page.title(),
                'viewport': page.viewport_size,
                'context': context
            }
            logging.debug(f"📄 Page state: {json.dumps(info, ensure_ascii=False)}")
            return info
        except Exception as e:
            logging.error(f"Could not log page state: {e}")
            return None

    @staticmethod
    def log_element_info(page: Page, selector: str, context: str = "") -> Optional[Dict[str, Any]]:
        """
        Log les infos détaillées d'un élément

        Args:
            page: Page Playwright
            selector: Sélecteur CSS
            context: Contexte additionnel

        Returns:
            Dictionnaire d'informations ou None
        """
        try:
            count = page.locator(selector).count()
            element = page.locator(selector).first

            info = {
                'selector': selector,
                'count': count,
                'visible': element.is_visible() if count > 0 else False,
                'enabled': element.is_enabled() if count > 0 else False,
                'text': element.inner_text()[:100] if count > 0 else None,
                'context': context
            }
            logging.debug(f"🔍 Element info: {json.dumps(info, ensure_ascii=False)}")
            return info
        except Exception as e:
            logging.warning(f"Could not log element info for {selector}: {e}")
            return None


class AlertSystem:
    """Système d'alerte en cas de problème critique"""

    def __init__(self, email_config: Optional[Dict[str, Any]] = None):
        self.email_config = email_config or {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'sender_email': os.getenv('ALERT_EMAIL'),
            'sender_password': os.getenv('ALERT_EMAIL_PASSWORD'),
            'recipient_email': os.getenv('RECIPIENT_EMAIL')
        }

    def send_alert(self, subject: str, body: str, attach_files: Optional[List[str]] = None) -> bool:
        """
        Envoie une alerte par email

        Args:
            subject: Sujet de l'email
            body: Corps de l'email
            attach_files: Liste de fichiers à attacher

        Returns:
            True si succès
        """
        if not all([self.email_config['sender_email'],
                   self.email_config['sender_password'],
                   self.email_config['recipient_email']]):
            logging.warning("Email config incomplete, skipping alert")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.email_config['recipient_email']
            msg['Subject'] = f"🚨 LinkedIn Bot Alert: {subject}"

            msg.attach(MIMEText(body, 'plain'))

            # Attache des fichiers (logs, screenshots)
            if attach_files:
                for filepath in attach_files:
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition',
                                          f'attachment; filename={os.path.basename(filepath)}')
                            msg.attach(part)

            with smtplib.SMTP(self.email_config['smtp_server'],
                            self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['sender_email'],
                           self.email_config['sender_password'])
                server.send_message(msg)

            logging.info(f"✅ Alert email sent: {subject}")
            return True

        except Exception as e:
            logging.error(f"Failed to send alert email: {e}")
            return False

    def alert_policy_violation(self, issues: List[Dict[str, str]], screenshot_path: Optional[str] = None) -> bool:
        """
        Alerte spécifique pour violation de politique

        Args:
            issues: Liste des problèmes détectés
            screenshot_path: Chemin du screenshot optionnel

        Returns:
            True si alerte envoyée avec succès
        """
        subject = "Policy Violation Detected"
        body = f"""
LinkedIn Bot Policy Violation Detected

Timestamp: {datetime.now().isoformat()}

Issues detected:
{json.dumps(issues, indent=2)}

The script has been stopped automatically.
Please review the attached screenshots and logs.

Action required: Manual intervention needed.
        """

        attach_files = []
        if screenshot_path and os.path.exists(screenshot_path):
            attach_files.append(screenshot_path)
        if os.path.exists("linkedin_bot_detailed.log"):
            attach_files.append("linkedin_bot_detailed.log")

        return self.send_alert(subject, body, attach_files)


def retry_with_fallbacks(
    func,
    max_attempts: int = 3,
    fallback_strategies: Optional[List] = None,
    screenshot_mgr: Optional[DebugScreenshotManager] = None,
    page: Optional[Page] = None
):
    """
    Exécute une fonction avec retry automatique et stratégies de repli

    Args:
        func: Fonction à exécuter
        max_attempts: Nombre de tentatives
        fallback_strategies: Liste de fonctions alternatives à essayer
        screenshot_mgr: Gestionnaire de screenshots
        page: Page Playwright pour screenshots

    Returns:
        Résultat de la fonction

    Raises:
        Exception: Si toutes les tentatives échouent
    """
    attempt = 0
    last_error = None

    while attempt < max_attempts:
        try:
            logging.info(f"🔄 Attempt {attempt + 1}/{max_attempts} for {func.__name__}")
            result = func()
            logging.info(f"✅ {func.__name__} succeeded")
            return result

        except Exception as e:
            attempt += 1
            last_error = e
            logging.warning(f"⚠️ Attempt {attempt} failed: {e}")

            # Capture screenshot de l'erreur
            if screenshot_mgr and page:
                screenshot_mgr.capture(page, f"{func.__name__}_attempt_{attempt}_failed", error=True)

            if attempt < max_attempts:
                wait_time = min(2 ** attempt, 10)  # Exponential backoff
                logging.info(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

    # Si toutes les tentatives échouent, essaye les stratégies de repli
    if fallback_strategies:
        for i, fallback in enumerate(fallback_strategies):
            try:
                logging.info(f"🔄 Trying fallback strategy {i+1}/{len(fallback_strategies)}")
                result = fallback()
                logging.info(f"✅ Fallback strategy {i+1} succeeded")
                return result
            except Exception as e:
                logging.warning(f"⚠️ Fallback strategy {i+1} failed: {e}")
                if screenshot_mgr and page:
                    screenshot_mgr.capture(page, f"fallback_{i+1}_failed", error=True)

    # Échec total
    logging.error(f"❌ All attempts and fallbacks failed for {func.__name__}")
    raise last_error


def quick_debug_check(page: Page) -> Dict[str, Any]:
    """
    Diagnostic rapide de l'état actuel

    Args:
        page: Page Playwright

    Returns:
        Dictionnaire des résultats de vérification
    """
    print("\n" + "="*50)
    print("🔍 QUICK DEBUG CHECK")
    print("="*50)

    checks = {
        "Page URL": page.url,
        "Page Title": page.title(),
        "Birthday cards found": page.locator("div[role='listitem']").count(),
        "Message button visible": page.locator("button.artdeco-button--secondary").first.is_visible() if page.locator("button.artdeco-button--secondary").count() > 0 else False,
        "Send button exists": page.locator("button.msg-form__send-button").count() > 0,
    }

    for key, value in checks.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")

    print("="*50 + "\n")

    # Screenshot automatique
    screenshot_path = f"quick_debug_{int(time.time())}.png"
    page.screenshot(path=screenshot_path)
    logging.info(f"Quick debug screenshot saved: {screenshot_path}")

    return checks
