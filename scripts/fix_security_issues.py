#!/usr/bin/env python3
import os
import subprocess
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_root():
    """Check if script is running as root."""
    if os.geteuid() != 0:
        logger.error("This script must be run as root (sudo) to modify Nginx configuration and file permissions.")
        sys.exit(1)

def fix_nginx_config():
    """Fix Nginx configuration for HTTP2 deprecation and reload."""
    nginx_conf_path = "/etc/nginx/sites-available/linkedin-bot.conf"

    if not os.path.exists(nginx_conf_path):
        logger.warning(f"Nginx config not found at {nginx_conf_path}. Skipping Nginx fix.")
        return

    logger.info("Checking Nginx configuration...")
    try:
        with open(nginx_conf_path, 'r') as f:
            content = f.read()

        # Check for deprecated http2 parameter
        if "listen 443 ssl http2;" in content:
            logger.info("Found deprecated 'http2' parameter in listen directive. Fixing...")
            new_content = content.replace("listen 443 ssl http2;", "listen 443 ssl;")
            new_content = new_content.replace("listen [::]:443 ssl http2;", "listen [::]:443 ssl;")

            # Add http2 on; once
            if "http2 on;" not in new_content:
                # Find the server block start for HTTPS and add http2 on;
                # A simple way is to add it after the listen directive
                new_content = new_content.replace("listen [::]:443 ssl;", "listen [::]:443 ssl;\n    http2 on;")

            with open(nginx_conf_path, 'w') as f:
                f.write(new_content)
            logger.info("Nginx configuration updated.")

            # Test configuration
            logger.info("Testing Nginx configuration...")
            result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Nginx configuration valid. Reloading...")
                subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
                logger.info("Nginx reloaded successfully.")
            else:
                logger.error(f"Nginx configuration invalid: {result.stderr}")
        else:
            logger.info("Nginx configuration already uses correct http2 syntax or does not use http2.")

    except Exception as e:
        logger.error(f"Failed to fix Nginx configuration: {e}")

def fix_database():
    """Ensure data directory and database file exist."""
    data_dir = "data"
    db_file = os.path.join(data_dir, "linkedin_bot.db")

    logger.info("Checking database...")
    if not os.path.exists(data_dir):
        logger.info(f"Creating directory {data_dir}...")
        os.makedirs(data_dir, exist_ok=True)
        # Set permissions to 777 as per deployment script recommendations for Docker
        os.chmod(data_dir, 0o777)

    if not os.path.exists(db_file):
        logger.info(f"Database file {db_file} missing. Initializing empty database...")
        # We can just touch the file, the app handles schema creation
        with open(db_file, 'w') as f:
            pass
        os.chmod(db_file, 0o666) # Read/Write for everyone (Docker needs this)
        logger.info("Database file created.")
    else:
        logger.info("Database file exists.")

def hash_password_node(password):
    """Hash password using the existing Node.js script."""
    node_script = "dashboard/scripts/hash_password.js"
    if not os.path.exists(node_script):
        logger.error(f"Node script not found at {node_script}")
        return None

    # Check if we are in the root directory where dashboard/ exists
    # If not, we might need to adjust path or change directory
    cwd = os.getcwd()

    try:
        # Run node script in quiet mode
        # We don't need sudo for this unless the script needs to write somewhere restricted, which it doesn't
        # But we are running as root.
        # Note: running node as root is generally okay for this utility script.

        result = subprocess.run(
            ['node', node_script, '--quiet', password],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd # Ensure we run from root so relative paths inside js work if any
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to hash password with Node script: {e.stderr}")
        return None
    except FileNotFoundError:
        logger.error("Node.js executable not found. Cannot hash password.")
        return None

def hash_password_in_env():
    """Hash DASHBOARD_PASSWORD or ADMIN_PASSWORD in .env if cleartext."""
    env_file = ".env"

    if not os.path.exists(env_file):
        logger.warning(f"{env_file} not found. Skipping password hashing.")
        return

    logger.info("Checking .env for cleartext passwords...")

    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()

        updated_lines = []
        modified = False

        for line in lines:
            line = line.strip()
            if line.startswith("DASHBOARD_PASSWORD=") or line.startswith("ADMIN_PASSWORD="):
                key, value = line.split("=", 1)
                value = value.strip().strip("'").strip('"')

                # Check if already hashed (bcrypt hash starts with $2a$ or $2b$)
                if not value.startswith("$2a$") and not value.startswith("$2b$") and value:
                    logger.info(f"Hashing cleartext password for {key}...")

                    hashed = hash_password_node(value)

                    if hashed:
                        # Docker Compose treats .env values as literals, no need to escape $
                        updated_lines.append(f"{key}={hashed}\n")
                        modified = True
                    else:
                        logger.warning(f"Could not hash password for {key}. Keeping original.")
                        updated_lines.append(line + "\n")
                else:
                    updated_lines.append(line + "\n")
            else:
                updated_lines.append(line + "\n")

        if modified:
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            logger.info(".env updated with hashed passwords.")
        else:
            logger.info("No cleartext passwords found in .env.")

    except Exception as e:
        logger.error(f"Failed to process .env file: {e}")

def fix_permissions():
    """Fix file permissions."""
    env_file = ".env"
    if os.path.exists(env_file):
        logger.info(f"Setting permissions 600 for {env_file}...")
        os.chmod(env_file, 0o600)

    # Ensure data directory is accessible
    data_dir = "data"
    if os.path.exists(data_dir):
        logger.info(f"Ensuring {data_dir} is writable (777 for Docker)...")
        os.chmod(data_dir, 0o777)

def main():
    check_root()
    logger.info("Starting Security Fix Script...")

    # 1. Fix Database
    fix_database()

    # 2. Fix Password Hashing
    hash_password_in_env()

    # 3. Fix Permissions
    fix_permissions()

    # 4. Fix Nginx
    fix_nginx_config()

    logger.info("Security fixes completed. Please restart your containers if needed.")

if __name__ == "__main__":
    main()
