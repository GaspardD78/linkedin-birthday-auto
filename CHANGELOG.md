# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **SSL Auto-Renewal Script** (`scripts/renew_certificates.sh`): Automatic SSL certificate renewal via certbot with zero-downtime nginx reload
- **Cron Job Configuration**: Automatic setup of daily SSL renewal check (3 AM) in `setup.sh`
- **CI/CD Healthchecks**: Post-build container health verification in GitHub Actions workflow
- **Memory Limits**: Strict RAM limits for all Docker services to prevent OOM kills on Raspberry Pi 4:
  - Dashboard: 896MB (NODE_OPTIONS: 800MB)
  - Bot Worker: 1400MB (Chromium/Playwright heavy)
  - API: 384MB
  - Redis (bot): 128MB
  - Redis (dashboard): 128MB
  - Nginx: 64MB
  - Prometheus: 384MB (monitoring profile)
  - Grafana: 256MB (monitoring profile)
  - Node-Exporter: 32MB (monitoring profile)

### Changed
- **Password Hashing Strategy**: Removed host-level Python bcrypt dependency, now uses 3-tier fallback:
  1. Dashboard Docker container with bcryptjs (primary method)
  2. `htpasswd -B` if available on host (fallback)
  3. OpenSSL SHA-512 (last resort)
- **Docker Compose File**: Renamed `docker-compose.pi4-standalone.yml` → `docker-compose.yml` for standardization
- **Setup Script**: Updated to reference new `docker-compose.yml` filename

### Fixed
- **OOM Kills on Pi4**: Memory limits prevent system crashes due to unconstrained container memory usage
- **Bcrypt Installation Failures**: No longer attempts to install Python packages on Debian 12+ systems with externally-managed-environment
- **SSL Certificate Management**: Automated renewal process reduces manual intervention and certificate expiration risks

### Security
- **Password Hashing Robustness**: Multi-strategy approach ensures secure password storage even without Python dependencies
- **Container Resource Isolation**: Memory limits enhance container security and stability

## [4.0.0] - 2025-01 (Previous Release)

### Added
- Modular architecture with reusable library scripts
- State management with checkpoint/resume functionality
- Comprehensive pre-deployment checks
- Enhanced security audit system
- Automatic backup before modifications

### Changed
- Complete refactor of setup.sh with modular design
- Improved error handling and logging
- Better idempotence across all setup phases

### Security
- Hardened password hashing with bcrypt
- Secure API key and JWT secret generation
- Permission management for Docker volumes

---

## Migration Guide

### From Previous Versions

If you're upgrading from a version before these changes:

1. **Pull Latest Changes**:
   ```bash
   cd /path/to/linkedin-birthday-auto
   git pull origin main
   ```

2. **Re-run Setup** (optional but recommended):
   ```bash
   ./setup.sh
   ```

   The setup script will:
   - Detect existing `.env` configuration
   - Apply new memory limits automatically
   - Offer to configure SSL auto-renewal cron job

3. **Manual Docker Compose Update** (if not re-running setup):
   ```bash
   docker compose down
   docker compose up -d
   ```

### Breaking Changes

- **Docker Compose Filename**: If you have custom scripts referencing `docker-compose.pi4-standalone.yml`, update them to use `docker-compose.yml`

### New Features You Can Enable

- **SSL Auto-Renewal**: Run `./setup.sh` and answer "Yes" when asked about cron job configuration
- **Monitoring Stack**: Use `docker compose --profile monitoring up -d` to enable Prometheus/Grafana

---

## Support

For issues, questions, or contributions, please visit:
- **GitHub Issues**: https://github.com/GaspardD78/linkedin-birthday-auto/issues
- **Documentation**: `/docs` directory

---

## Contributors

Special thanks to all contributors, including AI-assisted development by Claude (Anthropic).
