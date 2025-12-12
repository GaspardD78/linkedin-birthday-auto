# AI Migration Guide - Quick Start

**For AI Agents:** This guide tells you how to execute the Phase 2 migration reliably and automatically.

---

## 🎯 What You Need to Know

**Goal:** Migrate the dashboard from React 18 + Next.js 14 to React 19 + Next.js 15

**Approach:** Sequential, automated, validated execution with checkpoints

**Time Estimate:** 2-4 hours of execution (mostly automated)

---

## 📁 Files Created for You

### 1. **AI_MIGRATION_GUIDE.md** (Main Guide)
   - Complete step-by-step instructions
   - Every command with validation
   - Success criteria for each step
   - Error recovery procedures
   - **READ THIS FIRST**

### 2. **Automation Scripts**
   - `migration-stage1-react19.sh` - Automates React 19 migration
   - `migration-stage2-nextjs15.sh` - Automates Next.js 15 migration
   - `migration-stage3-packages.sh` - Automates package updates
   - **Use these to speed up execution**

### 3. **Reference Documents**
   - `PHASE2_MIGRATION_PLAN.md` - Human-readable migration plan
   - `DEPENDENCY_AUDIT.md` - Full dependency analysis
   - `AUDIT_SUMMARY.md` - Quick reference

---

## 🤖 Execution Modes

### Mode 1: Fully Automated (Recommended for Simple Cases)

If no deprecated patterns exist, run the automation scripts:

```bash
cd /home/user/linkedin-birthday-auto

# Stage 1: React 19
./migration-stage1-react19.sh

# If successful, commit
git add dashboard/package.json dashboard/package-lock.json
git commit -m "feat: migrate to React 19"

# Stage 2: Next.js 15 (requires manual file updates first)
./migration-stage2-nextjs15.sh

# If successful, commit
git add dashboard/
git commit -m "feat: migrate to Next.js 15"

# Stage 3: Supporting packages
./migration-stage3-packages.sh

# If successful, commit
git add dashboard/package.json dashboard/package-lock.json
git commit -m "feat: update supporting packages"

# Push everything
git push
```

### Mode 2: AI-Guided Manual Execution (Recommended for Complex Cases)

Follow **AI_MIGRATION_GUIDE.md** step-by-step:

1. Open `AI_MIGRATION_GUIDE.md`
2. Execute each step sequentially
3. Validate after each step
4. Fix issues before proceeding
5. Commit at checkpoints

---

## 🔍 Pre-Flight Check

Before starting, verify:

```bash
cd /home/user/linkedin-birthday-auto/dashboard

# 1. Verify you have package.json
test -f package.json && echo "✅ package.json found" || echo "❌ STOP: No package.json"

# 2. Verify node_modules exists (run npm install if not)
test -d node_modules && echo "✅ node_modules found" || echo "⚠️ Run: npm install"

# 3. Verify build works
npm run build && echo "✅ Build works" || echo "❌ STOP: Fix build first"

# 4. Create backup branch
cd ..
BACKUP_BRANCH="backup/pre-migration-$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BACKUP_BRANCH"
git push -u origin "$BACKUP_BRANCH"
git checkout -
echo "✅ Backup created: $BACKUP_BRANCH"
```

---

## 📊 Decision Tree

```
START
  │
  ├─ Run Stage 1 script (React 19)
  │    │
  │    ├─ SUCCESS → Commit → Continue
  │    │
  │    └─ FAIL (deprecated patterns found)
  │         │
  │         └─ Read AI_MIGRATION_GUIDE.md Step 1.2
  │              │
  │              └─ Fix patterns manually → Re-run script
  │
  ├─ Audit files for Next.js 15 changes
  │    │
  │    ├─ Files need updates?
  │    │    │
  │    │    ├─ YES → Follow AI_MIGRATION_GUIDE.md Step 2.2
  │    │    │         (Update each file) → Run Stage 2 script
  │    │    │
  │    │    └─ NO → Run Stage 2 script directly
  │    │
  │    └─ SUCCESS → Commit → Continue
  │
  ├─ Run Stage 3 script (Supporting packages)
  │    │
  │    └─ SUCCESS → Commit → Push
  │
  └─ DONE → Manual testing required
```

---

## 🚨 Critical Rules for AI Execution

1. **NEVER skip validation steps**
   - Every step has a validation command
   - If validation fails, STOP and fix

2. **NEVER proceed on errors**
   - Exit code != 0 → STOP
   - TypeScript errors → STOP and fix
   - Build fails → STOP and fix

3. **ALWAYS commit at checkpoints**
   - After React 19 → Commit
   - After Next.js 15 → Commit
   - After package updates → Commit

4. **READ error messages carefully**
   - Errors contain the solution
   - Check log files in `/tmp/migration-logs/`

5. **FOLLOW the sequence**
   - React 19 FIRST
   - Next.js 15 SECOND
   - Other packages THIRD
   - Do NOT reorder

---

## 📋 Expected File Changes

### Stage 1 (React 19)
Files modified:
- `dashboard/package.json` (React versions)
- `dashboard/package-lock.json`
- Possibly component files if deprecated patterns found

### Stage 2 (Next.js 15)
Files modified:
- `dashboard/package.json` (Next.js version)
- `dashboard/package-lock.json`
- `dashboard/app/api/**/route.ts` (multiple files with async APIs)
- `dashboard/app/**/page.tsx` (files with params/searchParams)
- `dashboard/middleware.ts` (if exists)

### Stage 3 (Packages)
Files modified:
- `dashboard/package.json` (all package versions)
- `dashboard/package-lock.json`

---

## 🔧 Common Issues and Solutions

### Issue: "defaultProps found" in Stage 1

**Solution:**
1. Read the file listed in `/tmp/migration-logs/defaultProps.txt`
2. Apply the fix from `AI_MIGRATION_GUIDE.md` Step 1.2
3. Re-run `migration-stage1-react19.sh`

### Issue: "TypeScript compilation failed"

**Solution:**
1. Read errors in `/tmp/migration-logs/tsc-*.log`
2. Fix TypeScript errors one by one
3. Run `npx tsc --noEmit` to verify
4. Re-run the failed script

### Issue: "Build failed"

**Solution:**
1. Read errors in `/tmp/migration-logs/build-*.log`
2. Check for import errors, missing dependencies
3. Run `npm install` if dependencies missing
4. Re-run the failed script

### Issue: "Files need async updates" in Stage 2

**Solution:**
1. Read file list in `/tmp/migration-logs/nextjs15-files-to-update.txt`
2. For EACH file:
   - Read the file
   - Find `cookies()` or `headers()` → Add `await` before it
   - Find `params:` → Change to `params: Promise<...>` and await it
   - Make function async if needed
3. Follow examples in `AI_MIGRATION_GUIDE.md` Step 2.2
4. Re-run `migration-stage2-nextjs15.sh`

---

## 📝 Validation Checklist

After completing all stages, verify:

```bash
cd /home/user/linkedin-birthday-auto/dashboard

# 1. TypeScript compiles
npx tsc --noEmit
echo "Exit code: $?"  # Should be 0

# 2. Lint passes
npm run lint
echo "Exit code: $?"  # Should be 0

# 3. Build succeeds
npm run build
echo "Exit code: $?"  # Should be 0

# 4. Dev server starts
npm run dev &
sleep 10
curl -I http://localhost:3000
kill %1

# 5. Check package versions
echo "React: $(node -e "console.log(require('./package.json').dependencies.react)")"
echo "Next: $(node -e "console.log(require('./package.json').dependencies.next)")"
echo "zustand: $(node -e "console.log(require('./package.json').dependencies.zustand)")"
```

**Expected versions:**
- React: ^19.2.1
- Next.js: ^15.0.0
- zustand: ^5.0.9
- sonner: ^2.0.7
- tailwind-merge: ^3.4.0
- recharts: ^3.5.1
- jose: ^6.1.3
- bcryptjs: ^3.0.3

---

## 🎯 Success Criteria

Migration is successful when:

✅ All scripts run without errors
✅ All validation checks pass
✅ TypeScript compiles (0 errors)
✅ ESLint passes (0 errors)
✅ Production build succeeds
✅ Dev server starts and responds
✅ All changes committed and pushed
✅ Package versions match expected

**After success:**
- Manual testing required (see MANUAL_TESTING.md if created)
- Deploy to staging for verification
- Monitor for runtime errors

---

## 📂 Log Files Location

All logs saved in: `/tmp/migration-logs/`

Files you'll find:
- `defaultProps.txt` - Deprecated pattern occurrences
- `forwardRef.txt` - ForwardRef usage
- `react19-audit.txt` - Pre-migration audit
- `nextjs15-audit.txt` - Files needing updates
- `nextjs15-files-to-update.txt` - File list
- `tsc-*.log` - TypeScript compilation logs
- `build-*.log` - Build logs
- `dev-*.log` - Dev server logs
- `npm-*.log` - NPM install logs

---

## 🆘 When to Stop and Ask for Help

STOP immediately if:

1. Same error occurs 3+ times
2. You don't understand an error message
3. Validation fails after multiple fix attempts
4. Build size increases dramatically (>50%)
5. Server crashes repeatedly
6. Data loss or corruption suspected

**Rollback command:**
```bash
cd /home/user/linkedin-birthday-auto
git checkout $BACKUP_BRANCH
cd dashboard
npm install
npm run build
```

---

## 📖 Further Reading

- **AI_MIGRATION_GUIDE.md** - Complete step-by-step guide
- **PHASE2_MIGRATION_PLAN.md** - Human-readable plan with context
- **DEPENDENCY_AUDIT.md** - Why these updates are needed

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. Backup
cd /home/user/linkedin-birthday-auto
git checkout -b backup/pre-migration-$(date +%Y%m%d)
git push -u origin backup/pre-migration-$(date +%Y%m%d)
git checkout -

# 2. Run migrations
./migration-stage1-react19.sh && git add dashboard/ && git commit -m "feat: React 19"
./migration-stage2-nextjs15.sh && git add dashboard/ && git commit -m "feat: Next.js 15"
./migration-stage3-packages.sh && git add dashboard/ && git commit -m "feat: update packages"

# 3. Push
git push

# 4. Manual testing
cd dashboard
npm run dev
# Test in browser
```

---

**Ready to start?** Begin with `AI_MIGRATION_GUIDE.md` or run `./migration-stage1-react19.sh`
