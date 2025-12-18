# AUDIT ARCHITECTURE V3.0 : CLOUD-TO-EDGE OPTIMIZATION
**Date:** 2025-12-18
**Target:** Raspberry Pi 4 (4GB RAM) / SD Card Storage
**Role:** Lead SRE Architect

## 1. EXECUTIVE SUMMARY
The current architecture follows a standard "Web Service" pattern (Docker Compose, Python, SQLite) which is functional but suboptimal for an **Edge IoT Appliance** running on SD Card storage. The primary risks are **SD Card Corruption** (due to high I/O from logs and Docker pulls) and **Service Unavailability** during updates (lack of atomic checks).

We propose a shift from "Script Execution" to **"State Management"** and a strict **"Zero-Write"** policy for ephemeral data.

## 2. CRITICAL ANALYSIS & REMEDIATION

### 2.1 The "Build-to-Run" Disconnect
**Current State:**
- Monolithic Dockerfile building on the runtime image.
- `docker pull` downloads entire layers even for small code changes if base layers aren't optimized.
- High network/disk cost on RPi4 during updates.

**SRE Strategy: "Lean & Verified Artifacts"**
- **Action:** Implement **Multi-Stage Builds**.
    - *Builder Stage:* Heavy tools (`gcc`, `build-essential`).
    - *Runtime Stage:* `python:3.11-slim`, copying only compiled wheels/artifacts.
- **Action:** **Layer Squashing** (logical). Order instructions to keep frequency-of-change low at the bottom.
- **Action:** **Pre-Push Integrity Check** in CI. Never push a broken image to the registry.

### 2.2 The "SD Card Killer" (I/O Analysis)
**Current State:**
- Logs written to `./logs` (persisted to SD).
- Playwright browser cache/profiles written to container overlay (persisted to SD via Docker).
- SQLite Journal/WAL flushing to disk.

**SRE Strategy: "Zero-Write Architecture"**
- **Action:** **Tmpfs Everywhere**.
    - `/app/logs` -> Mounted to RAM (`tmpfs`). Logs are ephemeral monitoring streams, not archives.
    - `/tmp` -> Mounted to RAM (`tmpfs`).
- **Action:** **SQLite Optimization**.
    - `synchronous = NORMAL` (Safe for WAL).
    - `journal_mode = WAL`.
    - Maintenance: Periodic `VACUUM` to keep the file contiguous and reduce seek times.
- **Action:** **Docker Hygiene**.
    - Aggressive `docker system prune` during setup to free blocks.

### 2.3 System Orchestration (`setup.sh`)
**Current State:**
- Linear script. Fails if a step fails. Updates blindly.

**SRE Strategy: "State Manager"**
- **Concept:** The script ensures a *desired state*. It is idempotent.
- **Phases:**
    1.  **Hardware State:** Check ZRAM/Swap. if mismatch -> fix -> verify.
    2.  **Maintenance State:** Clean disk. Optimize DB.
    3.  **Application State:** Atomic Update.
        - `docker compose pull` (Download).
        - `docker compose config` (Verify syntax).
        - `docker compose up -d` (Recreate).
        - `curl health_check` (Verify).
        - *Rollback capability is implicit via previous image tag if needed, but manual for now.*

### 2.4 Security Hardening
**Current State:**
- Basic Nginx proxy.
- Potential exposure of internal ports if not strictly bound to localhost (fixed in Compose).

**SRE Strategy: "Defense in Depth"**
- **Action:** **Nginx Hardening**.
    - HSTS (Force HTTPS).
    - CSP (Prevent XSS).
    - Rate Limiting (Prevent Brute Force).
- **Action:** **Isolation**.
    - UID 1000 enforcement (already present, verify strictness).
    - Read-Only containers where possible (difficult with Python bytecodes, but `PYTHONDONTWRITEBYTECODE=1` helps).

## 3. IMPLEMENTATION PLAN
1.  **Cloud:** Optimize `Dockerfile.multiarch` & GitHub Actions.
2.  **Edge:** Refactor `setup.sh` into the new State Manager.
3.  **Edge:** Update `docker-compose.pi4-standalone.yml` with `tmpfs` and limits.
4.  **Edge:** Deploy Security Configs.
