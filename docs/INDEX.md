# 📚 Documentation Index - LinkedIn Auto RPi4

**Last Updated:** 2025-12-18
**Version:** v1.1 (Complete Restructure)

---

## 📢 Important Note

**2025-12-18:** Documentation was consolidated into a single authoritative source. See **[DOCUMENTATION_CONSOLIDATION.md](../DOCUMENTATION_CONSOLIDATION.md)** for details. Obsolete docs have been archived in **[_ARCHIVE_2025/](../_ARCHIVE_2025/)**

---

## 🎯 Start Here

1. **New to the project?** → Start with [README.md](../README.md)
2. **Need technical details?** → Go to [KNOWLEDGE_BASE_v1.1.md](KNOWLEDGE_BASE_v1.1.md)
3. **Deploying for first time?** → Jump to [KNOWLEDGE_BASE_v1.1.md#part-d--procédures-opérationnelles](KNOWLEDGE_BASE_v1.1.md#partie-d--procédures-opérationnelles)
4. **Fixing a problem?** → See [README.md#troubleshooting](../README.md#-troubleshooting)
5. **Contributing code?** → Read [KNOWLEDGE_BASE_v1.1.md#part-e--standards--normes](KNOWLEDGE_BASE_v1.1.md#partie-e--standards--normes)

---

## 📖 Complete Documentation Map

### **Core Documentation**

| Document | Purpose | Best For |
|----------|---------|----------|
| **[README.md](../README.md)** | Quick start & overview | Everyone, first-time users |
| **[KNOWLEDGE_BASE_v1.1.md](KNOWLEDGE_BASE_v1.1.md)** | Complete technical reference (THE source of truth) | Architects, DevOps, Developers |
| **[ARCHITECTURE_DETAILS.md](ARCHITECTURE_DETAILS.md)** | Deep dive: All bots, API routes, DB schema | Developers, Architects |
| **[INDEX.md](INDEX.md)** | This file - navigation guide | Everyone |

### **Audit & Compliance**

| Document | Purpose | Status |
|----------|---------|--------|
| **[AUDIT_REPORT.md](../AUDIT_REPORT.md)** | Performance & security audit | ✅ Recent (2025-12-18) |
| **[AUDIT_REFACTORING_2025-12-18.md](../AUDIT_REFACTORING_2025-12-18.md)** | Code changes & optimizations | ✅ Applied |
| **[AUDIT_SECURITE_2025-12-18.md](../AUDIT_SECURITE_2025-12-18.md)** | Security hardening report | ✅ Reviewed |
| **[CONTEXT.md](../CONTEXT.md)** | Project context & history | ℹ️ Reference |

---

## 🔍 How to Find What You Need

### By Role

#### **🏗️ System Architect**
1. Read [KNOWLEDGE_BASE_v1.1.md#partie-a--vision-stratégique](KNOWLEDGE_BASE_v1.1.md#partie-a--vision-stratégique) (Strategy)
2. Review [KNOWLEDGE_BASE_v1.1.md#partie-b--architecture-technique](KNOWLEDGE_BASE_v1.1.md#partie-b--architecture-technique) (Architecture)
3. Check [AUDIT_REPORT.md](../AUDIT_REPORT.md) (Validation)

#### **👨‍💻 Developer**
1. Start with [ARCHITECTURE_DETAILS.md#1-bots-detailed-specification](ARCHITECTURE_DETAILS.md#1-bots-detailed-specification) (All bots explained)
2. Review [ARCHITECTURE_DETAILS.md#2-api-routes-complete-reference](ARCHITECTURE_DETAILS.md#2-api-routes-complete-reference) (All API endpoints)
3. Learn [ARCHITECTURE_DETAILS.md#3-database-schema](ARCHITECTURE_DETAILS.md#3-database-schema) (Database structure)
4. Check [KNOWLEDGE_BASE_v1.1.md#partie-e--standards--normes](KNOWLEDGE_BASE_v1.1.md#partie-e--standards--normes) (Coding standards)
5. See [README.md#contributing](../README.md#-contributing) (Contribution guide)

#### **🔧 DevOps / SysAdmin**
1. Follow [KNOWLEDGE_BASE_v1.1.md#partie-d--procédures-opérationnelles](KNOWLEDGE_BASE_v1.1.md#partie-d--procédures-opérationnelles) (SOP)
2. Refer to [README.md#common-operations](../README.md#-common-operations) (Daily tasks)
3. Check [README.md#troubleshooting](../README.md#-troubleshooting) (Problem-solving)

#### **👤 End User (Dashboard Only)**
1. Follow [README.md#installation](../README.md#-installation) (Setup)
2. See [README.md#common-operations](../README.md#-common-operations) (Running bots)
3. Reference [README.md#faq](../README.md#-faq) (Common questions)

---

### By Task

#### **Installation & Setup**
- Quick start: [README.md#installation](../README.md#-installation)
- Detailed procedure: [KNOWLEDGE_BASE_v1.1.md#d1---protocole-de-déploiement-initial](KNOWLEDGE_BASE_v1.1.md#d1---protocole-de-déploiement-initial)
- Hardware verification: [KNOWLEDGE_BASE_v1.1.md#partie-a--vision-stratégique](KNOWLEDGE_BASE_v1.1.md#partie-a--vision-stratégique) (Constraints)

#### **Understanding Architecture**
- Overview: [README.md#documentation-structure](../README.md#-documentation-structure)
- Execution flow: [KNOWLEDGE_BASE_v1.1.md#b1---flux-dexécution-global](KNOWLEDGE_BASE_v1.1.md#b1---flux-dexécution-global)
- Directory structure: [KNOWLEDGE_BASE_v1.1.md#b2---architecture-répertoires-src](KNOWLEDGE_BASE_v1.1.md#b2---architecture-répertoires-src)
- Bot lifecycle: [KNOWLEDGE_BASE_v1.1.md#b3---cycle-de-vie-dun-bot-exemple-birthday-bot](KNOWLEDGE_BASE_v1.1.md#b3---cycle-de-vie-dun-bot-exemple-birthday-bot)

#### **Memory & Performance**
- Memory management: [KNOWLEDGE_BASE_v1.1.md#b4---memory-management-critical-for-rpi4](KNOWLEDGE_BASE_v1.1.md#b4---memory-management-critical-for-rpi4)
- Database optimization: [KNOWLEDGE_BASE_v1.1.md#b5---database-architecture-sqlite-wal](KNOWLEDGE_BASE_v1.1.md#b5---database-architecture-sqlite-wal)
- Docker optimization: [KNOWLEDGE_BASE_v1.1.md#b6---docker-architecture](KNOWLEDGE_BASE_v1.1.md#b6---docker-architecture)
- Performance metrics: [README.md#performance-metrics](../README.md#-performance-metrics)

#### **Daily Operations**
- Common operations: [README.md#common-operations](../README.md#-common-operations)
- Weekly maintenance: [KNOWLEDGE_BASE_v1.1.md#d2---protocole-de-maintenance-hebdomadaire](KNOWLEDGE_BASE_v1.1.md#d2---protocole-de-maintenance-hebdomadaire)
- Backup & recovery: [KNOWLEDGE_BASE_v1.1.md#d3---protocole-durgence-troubleshooting](KNOWLEDGE_BASE_v1.1.md#d3---protocole-durgence-troubleshooting)

#### **Troubleshooting**
- Quick fixes: [README.md#troubleshooting](../README.md#-troubleshooting)
- Emergency procedures: [KNOWLEDGE_BASE_v1.1.md#d3---protocole-durgence-troubleshooting](KNOWLEDGE_BASE_v1.1.md#d3---protocole-durgence-troubleshooting)
- Memory issues: [KNOWLEDGE_BASE_v1.1.md#symptôme-mémoire-full-out-of-memory](KNOWLEDGE_BASE_v1.1.md#symptôme-mémoire-full-out-of-memory)

#### **Security**
- Security standards: [KNOWLEDGE_BASE_v1.1.md#e4---normes-de-sécurité](KNOWLEDGE_BASE_v1.1.md#e4---normes-de-sécurité)
- Best practices: [README.md#security-best-practices](../README.md#-security-best-practices)
- Security protocols: [KNOWLEDGE_BASE_v1.1.md#d4---protocole-de-sécurité](KNOWLEDGE_BASE_v1.1.md#d4---protocole-de-sécurité)

#### **Configuration**
- Environment variables: [KNOWLEDGE_BASE_v1.1.md#e2---normes-de-configuration](KNOWLEDGE_BASE_v1.1.md#e2---normes-de-configuration)
- YAML config: [README.md#bot-scheduling](../README.md#bot-scheduling)
- Browser settings: [README.md#browser-configuration](../README.md#browser-configuration)

---

## 📚 Document Descriptions

### KNOWLEDGE_BASE_v1.1.md (THE SOURCE OF TRUTH)

**16,000+ words** organized in 5 parts:

- **Part A: Strategic Vision**
  - Why the project exists
  - Non-negotiable constraints (RPi4 limits)
  - Technology decisions and justifications
  - Stack definition

- **Part B: Architecture**
  - Execution flow diagram
  - Directory structure with explanations
  - Bot lifecycle (setup → run → teardown)
  - Memory management strategy
  - Database (SQLite WAL) deep dive
  - Docker optimization

- **Part C: Script Index**
  - All scripts documented with "Raison d'Être"
  - Memory strategies explained
  - Usage examples and schedules

- **Part D: Procedures (SOP)**
  - Initial deployment protocol
  - Weekly maintenance routine
  - Emergency troubleshooting procedures
  - Security protocols

- **Part E: Standards**
  - Code style rules
  - Configuration standards
  - Performance limits
  - Security requirements
  - Exception hierarchy
  - Deployment checklist

### README.md (QUICK START)

**Essential information** for all users:
- Feature overview
- Installation steps (6 phases)
- Common operations
- Configuration examples
- Troubleshooting flowchart
- FAQ
- Contributing guidelines

### AUDIT_REPORT.md

**Technical audit** of code quality:
- Architecture review (all green ✅)
- Database optimization (WAL confirmed)
- Memory management (GC active)
- Docker configuration (optimized)
- Security assessment (strong)
- Performance metrics
- Checklist items

### AUDIT_REFACTORING_2025-12-18.md

**Recent changes** applied to codebase:
- Logging standardization (structlog)
- Garbage collection additions
- Docker cleanup improvements
- ZRAM configuration
- Chromium zombie cleanup script
- Change justifications and impact

---

## 🔄 Documentation Update Schedule

| Document | Frequency | Trigger |
|----------|-----------|---------|
| KNOWLEDGE_BASE_v1.1.md | Quarterly | Major architecture change |
| README.md | Bi-annual | New features or changed setup |
| AUDIT_*.md | Bi-annual | Code changes or security findings |
| This INDEX.md | Ad-hoc | Documentation reorganization |

---

## 🚨 Important Notes

1. **KNOWLEDGE_BASE_v1.1.md is authoritative** - If it contradicts other docs, KB is correct
2. **All paths are relative to project root** - Adjust when reading from different locations
3. **"Part D" (SOP) is step-by-step** - Follow exactly for deployment/troubleshooting
4. **Code standards in "Part E" are non-negotiable** - Enforce in PR reviews

---

## ✅ Verification Checklist

Use this to validate documentation completeness:

- [ ] Have read Part A (Vision) if architect
- [ ] Understand Part B (Architecture) for your role
- [ ] Know which Part C (Script) applies to your work
- [ ] Can follow Part D (SOP) procedures
- [ ] Comply with Part E (Standards) when contributing
- [ ] Know where to find [FAQ](../README.md#-faq)
- [ ] Can troubleshoot using [README troubleshooting](../README.md#-troubleshooting)

---

## 🔗 Quick Links

**Setup:**
```
Step 1: README.md → Installation section
Step 2: KNOWLEDGE_BASE_v1.1.md → Part D1 (Deployment Protocol)
Step 3: Verify with scripts/validate_rpi4_config.sh
```

**Daily Use:**
```
Start Bot: README.md → Common Operations
Check Status: README.md → Performance Metrics
Fix Issues: README.md → Troubleshooting OR KNOWLEDGE_BASE_v1.1.md → Part D3
```

**Development:**
```
Understand Code: KNOWLEDGE_BASE_v1.1.md → Part B2 (Structure)
Follow Standards: KNOWLEDGE_BASE_v1.1.md → Part E
Submit PR: README.md → Contributing

---

## 📞 Where to Get Help

| Question | Answer Location |
|----------|-----------------|
| "How do I install?" | README.md § Installation |
| "How does it work?" | KNOWLEDGE_BASE_v1.1.md § Part B |
| "Why was this chosen?" | KNOWLEDGE_BASE_v1.1.md § Part A |
| "My bot is timing out" | README.md § Troubleshooting |
| "Dashboard won't start" | KNOWLEDGE_BASE_v1.1.md § D3 |
| "Need to backup DB" | KNOWLEDGE_BASE_v1.1.md § D2 |
| "Security question" | KNOWLEDGE_BASE_v1.1.md § E4 |
| "Code standard question" | KNOWLEDGE_BASE_v1.1.md § E1-E3 |

---

**Last Verified:** 2025-12-18
**Maintainer:** Claude (DevOps & Lead Developer)
**Status:** ✅ Complete & Current
