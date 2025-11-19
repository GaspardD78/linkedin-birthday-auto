"""
Proxy Manager for LinkedIn Birthday Automation
Provides rotating proxy support with health checks and fallback mechanisms
"""

import os
import json
import time
import random
import logging
import sqlite3
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages proxy rotation with health checks and automatic fallback

    Features:
    - Round-robin or random proxy selection
    - Proxy health validation before use
    - Automatic fallback on proxy failure
    - Success/failure tracking in database
    - Configurable retry logic
    """

    def __init__(self, db_path: str = "linkedin_birthday.db"):
        """
        Initialize the proxy manager

        Args:
            db_path: Path to SQLite database for tracking proxy metrics
        """
        self.db_path = db_path
        self.proxies: List[Dict] = []
        self.current_index = 0
        self.enabled = False
        self.random_selection = False
        self.max_retries = 3
        self.proxy_timeout = 10

        # Initialize database table for proxy metrics
        self._init_db()

        # Load configuration from environment
        self._load_config()

    def _init_db(self):
        """Create proxy_metrics table if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proxy_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_url TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time REAL,
                    error_message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            logger.info("Proxy metrics table initialized")
        except Exception as e:
            logger.error(f"Error initializing proxy metrics table: {e}")

    def _load_config(self):
        """Load proxy configuration from environment variables"""
        # Check if proxy rotation is enabled
        self.enabled = os.getenv('ENABLE_PROXY_ROTATION', 'false').lower() == 'true'

        if not self.enabled:
            logger.info("Proxy rotation is disabled")
            return

        # Load proxy list from environment variable (JSON format)
        proxy_list_str = os.getenv('PROXY_LIST', '[]')
        try:
            proxy_list = json.loads(proxy_list_str)

            # Parse and validate each proxy
            for proxy_config in proxy_list:
                if isinstance(proxy_config, str):
                    # Simple string format: "http://user:pass@host:port"
                    parsed = self._parse_proxy_url(proxy_config)
                    if parsed:
                        self.proxies.append(parsed)
                elif isinstance(proxy_config, dict):
                    # Dict format with additional metadata
                    self.proxies.append(proxy_config)

            logger.info(f"Loaded {len(self.proxies)} proxies")

            # Additional configuration
            self.random_selection = os.getenv('RANDOM_PROXY_SELECTION', 'false').lower() == 'true'
            self.proxy_timeout = int(os.getenv('PROXY_TIMEOUT', '10'))
            self.max_retries = int(os.getenv('PROXY_MAX_RETRIES', '3'))

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing PROXY_LIST: {e}")
            self.enabled = False
        except Exception as e:
            logger.error(f"Error loading proxy configuration: {e}")
            self.enabled = False

    def _parse_proxy_url(self, proxy_url: str) -> Optional[Dict]:
        """
        Parse a proxy URL and extract components

        Args:
            proxy_url: Proxy URL in format: protocol://[user:pass@]host:port

        Returns:
            Dict with proxy configuration or None if invalid
        """
        try:
            parsed = urlparse(proxy_url)

            if not parsed.hostname or not parsed.port:
                logger.error(f"Invalid proxy URL: {proxy_url}")
                return None

            proxy_config = {
                'server': f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
                'url': proxy_url
            }

            # Add authentication if present
            if parsed.username and parsed.password:
                proxy_config['username'] = parsed.username
                proxy_config['password'] = parsed.password

            return proxy_config

        except Exception as e:
            logger.error(f"Error parsing proxy URL {proxy_url}: {e}")
            return None

    def get_next_proxy(self) -> Optional[Dict]:
        """
        Get the next proxy in rotation

        Returns:
            Dict with proxy configuration or None if no proxies available
        """
        if not self.enabled or not self.proxies:
            return None

        if self.random_selection:
            # Random selection
            selected_proxy = random.choice(self.proxies)
        else:
            # Round-robin selection
            selected_proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

        logger.info(f"Selected proxy: {self._mask_proxy_url(selected_proxy.get('url', selected_proxy.get('server')))}")
        return selected_proxy

    def get_proxy_with_fallback(self) -> Tuple[Optional[Dict], int]:
        """
        Get a working proxy with automatic fallback

        Returns:
            Tuple of (proxy_config, attempts_made)
        """
        if not self.enabled or not self.proxies:
            return None, 0

        attempts = 0
        tried_proxies = set()

        while attempts < min(self.max_retries, len(self.proxies)):
            proxy = self.get_next_proxy()
            proxy_key = proxy.get('url', proxy.get('server'))

            # Avoid trying the same proxy twice
            if proxy_key in tried_proxies:
                continue

            tried_proxies.add(proxy_key)
            attempts += 1

            # Check if proxy has too many recent failures
            if self._has_recent_failures(proxy_key):
                logger.warning(f"Proxy {self._mask_proxy_url(proxy_key)} has recent failures, trying next...")
                continue

            logger.info(f"Attempting to use proxy (attempt {attempts}/{self.max_retries})")
            return proxy, attempts

        logger.warning(f"All proxies failed or exhausted after {attempts} attempts")
        return None, attempts

    def _has_recent_failures(self, proxy_url: str, window_minutes: int = 30, threshold: int = 3) -> bool:
        """
        Check if a proxy has too many recent failures

        Args:
            proxy_url: The proxy URL to check
            window_minutes: Time window to check (default: 30 minutes)
            threshold: Number of failures to consider "too many" (default: 3)

        Returns:
            True if proxy has too many recent failures
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)

            cursor.execute("""
                SELECT COUNT(*) FROM proxy_metrics
                WHERE proxy_url = ?
                AND success = 0
                AND timestamp > ?
            """, (proxy_url, cutoff_time.isoformat()))

            failure_count = cursor.fetchone()[0]
            conn.close()

            return failure_count >= threshold

        except Exception as e:
            logger.error(f"Error checking proxy failures: {e}")
            return False

    def record_proxy_result(self, proxy_url: str, success: bool, response_time: Optional[float] = None,
                           error_message: Optional[str] = None):
        """
        Record the result of using a proxy

        Args:
            proxy_url: The proxy URL that was used
            success: Whether the proxy worked successfully
            response_time: Optional response time in seconds
            error_message: Optional error message if failed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO proxy_metrics (proxy_url, success, response_time, error_message)
                VALUES (?, ?, ?, ?)
            """, (proxy_url, success, response_time, error_message))

            conn.commit()
            conn.close()

            status = "SUCCESS" if success else "FAILED"
            masked_url = self._mask_proxy_url(proxy_url)
            logger.info(f"Recorded proxy result: {masked_url} - {status}")

        except Exception as e:
            logger.error(f"Error recording proxy result: {e}")

    def get_proxy_stats(self, hours: int = 24) -> List[Dict]:
        """
        Get proxy statistics for the last N hours

        Args:
            hours: Number of hours to look back (default: 24)

        Returns:
            List of dicts with proxy statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)

            cursor.execute("""
                SELECT
                    proxy_url,
                    COUNT(*) as total_uses,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                    AVG(CASE WHEN success = 1 THEN response_time ELSE NULL END) as avg_response_time
                FROM proxy_metrics
                WHERE timestamp > ?
                GROUP BY proxy_url
                ORDER BY total_uses DESC
            """, (cutoff_time.isoformat(),))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'proxy_url': self._mask_proxy_url(row[0]),
                    'total_uses': row[1],
                    'successes': row[2],
                    'failures': row[3],
                    'success_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0,
                    'avg_response_time': row[4]
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error getting proxy stats: {e}")
            return []

    def _mask_proxy_url(self, proxy_url: str) -> str:
        """
        Mask sensitive information in proxy URL for logging

        Args:
            proxy_url: The proxy URL to mask

        Returns:
            Masked proxy URL
        """
        try:
            parsed = urlparse(proxy_url)
            if parsed.username and parsed.password:
                # Mask username and password
                masked = f"{parsed.scheme}://***:***@{parsed.hostname}:{parsed.port}"
            else:
                masked = proxy_url
            return masked
        except:
            return "***"

    def get_playwright_proxy_config(self) -> Optional[Dict]:
        """
        Get proxy configuration in Playwright format

        Returns:
            Dict with Playwright proxy configuration or None
        """
        proxy, _ = self.get_proxy_with_fallback()

        if not proxy:
            return None

        # Convert to Playwright format
        playwright_config = {
            'server': proxy.get('server')
        }

        if 'username' in proxy and 'password' in proxy:
            playwright_config['username'] = proxy['username']
            playwright_config['password'] = proxy['password']

        return playwright_config

    def is_enabled(self) -> bool:
        """Check if proxy rotation is enabled"""
        return self.enabled and len(self.proxies) > 0


# Convenience function for simple usage
def get_proxy_config() -> Optional[Dict]:
    """
    Get a proxy configuration for use with Playwright

    Returns:
        Dict with proxy config or None if proxies disabled
    """
    manager = ProxyManager()
    return manager.get_playwright_proxy_config()
