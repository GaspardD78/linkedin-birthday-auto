#!/bin/bash
# Stage 2: Next.js 15 Migration - Automated Script
# This script executes all steps for Next.js 15 migration with validation

set -e  # Exit on error

DASHBOARD_DIR="/home/user/linkedin-birthday-auto/dashboard"
LOG_DIR="/tmp/migration-logs"
mkdir -p "$LOG_DIR"

echo "=================================="
echo "STAGE 2: Next.js 15 Migration"
echo "=================================="
echo ""

# Change to dashboard directory
cd "$DASHBOARD_DIR"

# Step 2.1: Identify Files Using Async APIs
echo "Step 2.1: Identify Files Using Async APIs"
echo "------------------------------------------"

echo "Searching for cookies() usage..."
grep -r "cookies()" --include="*.ts" --include="*.tsx" app/ lib/ 2>/dev/null | cut -d: -f1 | sort -u | tee "$LOG_DIR/cookies-files.txt" || true
COOKIES_COUNT=$(cat "$LOG_DIR/cookies-files.txt" 2>/dev/null | wc -l)

echo "Searching for headers() usage..."
grep -r "headers()" --include="*.ts" --include="*.tsx" app/ lib/ 2>/dev/null | cut -d: -f1 | sort -u | tee "$LOG_DIR/headers-files.txt" || true
HEADERS_COUNT=$(cat "$LOG_DIR/headers-files.txt" 2>/dev/null | wc -l)

echo "Searching for params usage..."
grep -r "params\s*:" --include="*.ts" --include="*.tsx" app/ 2>/dev/null | grep -E "(page|route)\.tsx?" | cut -d: -f1 | sort -u | tee "$LOG_DIR/params-files.txt" || true
PARAMS_COUNT=$(cat "$LOG_DIR/params-files.txt" 2>/dev/null | wc -l)

echo "Searching for searchParams usage..."
grep -r "searchParams\s*:" --include="*.ts" --include="*.tsx" app/ 2>/dev/null | grep -E "page\.tsx?" | cut -d: -f1 | sort -u | tee "$LOG_DIR/searchparams-files.txt" || true
SEARCHPARAMS_COUNT=$(cat "$LOG_DIR/searchparams-files.txt" 2>/dev/null | wc -l)

# Create combined list
cat "$LOG_DIR/cookies-files.txt" "$LOG_DIR/headers-files.txt" "$LOG_DIR/params-files.txt" "$LOG_DIR/searchparams-files.txt" 2>/dev/null | sort -u > "$LOG_DIR/nextjs15-files-to-update.txt"
TOTAL_FILES=$(cat "$LOG_DIR/nextjs15-files-to-update.txt" | wc -l)

cat > "$LOG_DIR/nextjs15-audit.txt" <<EOF
Next.js 15 Pre-Migration Audit Report
=====================================
Files using cookies(): $COOKIES_COUNT
Files using headers(): $HEADERS_COUNT
Files using params: $PARAMS_COUNT
Files using searchParams: $SEARCHPARAMS_COUNT
Total unique files to update: $TOTAL_FILES
EOF

cat "$LOG_DIR/nextjs15-audit.txt"
echo ""
echo "Files to update:"
cat "$LOG_DIR/nextjs15-files-to-update.txt"
echo ""

if [ $TOTAL_FILES -gt 0 ]; then
    echo "⚠️  $TOTAL_FILES files require async API updates"
    echo "⚠️  These must be updated manually or by AI before continuing"
    echo ""
    echo "Pattern to apply:"
    echo "  - Add 'await' before cookies(), headers()"
    echo "  - Change params type to Promise<{ ... }>"
    echo "  - Change searchParams type to Promise<{ ... }>"
    echo "  - Make component/function async if needed"
    echo ""
    read -p "Have you updated all files? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please update the files and re-run this script"
        exit 1
    fi
fi

echo ""

# Step 2.3: Update Next.js Dependencies
echo "Step 2.3: Update Next.js Dependencies"
echo "--------------------------------------"

echo "Installing Next.js 15..."
npm install next@^15.0.0 2>&1 | tee "$LOG_DIR/npm-install-next.log"

echo "Installing ESLint config..."
npm install -D eslint-config-next@15.0.0 2>&1 | tee -a "$LOG_DIR/npm-install-next.log"

# Verify versions
NEXT_VERSION=$(node -e "console.log(require('./package.json').dependencies.next)")
echo ""
echo "Installed version: Next.js $NEXT_VERSION"

if [[ "$NEXT_VERSION" == ^15* ]]; then
    echo "✅ Next.js 15 installed successfully"
else
    echo "❌ Next.js 15 installation failed"
    exit 1
fi

echo ""

# Step 2.5: TypeScript Compilation Check
echo "Step 2.5: TypeScript Compilation Check"
echo "---------------------------------------"

npx tsc --noEmit --project tsconfig.json 2>&1 | tee "$LOG_DIR/tsc-nextjs15.log"
TSC_EXIT=${PIPESTATUS[0]}

if [ $TSC_EXIT -eq 0 ]; then
    echo "✅ TypeScript compilation successful"
else
    echo "❌ TypeScript compilation failed"
    echo "See errors in: $LOG_DIR/tsc-nextjs15.log"
    exit 1
fi

echo ""

# Step 2.6: Build Test
echo "Step 2.6: Build Test"
echo "--------------------"

echo "Cleaning previous build..."
rm -rf .next

echo "Running production build..."
npm run build 2>&1 | tee "$LOG_DIR/build-nextjs15.log"
BUILD_EXIT=${PIPESTATUS[0]}

if [ $BUILD_EXIT -eq 0 ]; then
    echo "✅ Build successful"
    if [ -d .next ]; then
        echo "✅ .next directory created"
        BUILD_SIZE=$(du -sh .next | cut -f1)
        echo "Build size: $BUILD_SIZE"
    else
        echo "❌ .next directory not found"
        exit 1
    fi
else
    echo "❌ Build failed"
    echo "See errors in: $LOG_DIR/build-nextjs15.log"
    exit 1
fi

echo ""

# Step 2.7: Runtime Test
echo "Step 2.7: Runtime Test (Dev Server)"
echo "------------------------------------"

echo "Starting dev server..."
npm run dev > "$LOG_DIR/dev-nextjs15.log" 2>&1 &
DEV_PID=$!

echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Server started"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Server failed to start"
        cat "$LOG_DIR/dev-nextjs15.log"
        kill $DEV_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Test main page
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
echo "HTTP response code: $HTTP_CODE"

if [[ "$HTTP_CODE" =~ ^(200|307|301)$ ]]; then
    echo "✅ Main page accessible"
else
    echo "❌ Main page not accessible"
    cat "$LOG_DIR/dev-nextjs15.log"
    kill $DEV_PID 2>/dev/null
    exit 1
fi

# Check for critical errors in logs
if grep -i "error" "$LOG_DIR/dev-nextjs15.log" | grep -v "webpack" > /dev/null; then
    echo "⚠️  Errors detected in logs"
    grep -i "error" "$LOG_DIR/dev-nextjs15.log" | grep -v "webpack"
else
    echo "✅ No critical errors in logs"
fi

# Stop server
kill $DEV_PID 2>/dev/null
sleep 2
echo "✅ Server stopped"

echo ""

# Success summary
echo "=================================="
echo "✅ STAGE 2 COMPLETE: Next.js 15"
echo "=================================="
echo ""
echo "Summary:"
echo "  - Next.js 15.0.0 installed"
echo "  - Files updated: $TOTAL_FILES"
echo "  - TypeScript compilation: PASS"
echo "  - Production build: PASS"
echo "  - Dev server test: PASS"
echo ""
echo "Logs saved in: $LOG_DIR/"
echo ""
echo "Next step: Commit these changes"
echo "  cd /home/user/linkedin-birthday-auto"
echo "  git add dashboard/"
echo "  git commit -m 'feat: migrate to Next.js 15'"
echo ""
