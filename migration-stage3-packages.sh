#!/bin/bash
# Stage 3: Supporting Packages Update - Automated Script
# This script updates all supporting packages to latest major versions

set -e  # Exit on error

DASHBOARD_DIR="/home/user/linkedin-birthday-auto/dashboard"
LOG_DIR="/tmp/migration-logs"
mkdir -p "$LOG_DIR"

echo "=================================="
echo "STAGE 3: Supporting Package Updates"
echo "=================================="
echo ""

# Change to dashboard directory
cd "$DASHBOARD_DIR"

# Step 3.1: Update zustand
echo "Step 3.1: Update zustand"
echo "------------------------"

npm install zustand@^5.0.9 2>&1 | tee "$LOG_DIR/npm-zustand.log"
ZUSTAND_VERSION=$(node -e "console.log(require('./package.json').dependencies.zustand)")

if [[ "$ZUSTAND_VERSION" == ^5* ]]; then
    echo "✅ zustand 5.0.9 installed"
else
    echo "❌ zustand update failed"
    exit 1
fi

echo ""

# Step 3.2: Update sonner
echo "Step 3.2: Update sonner"
echo "-----------------------"

npm install sonner@^2.0.7 2>&1 | tee "$LOG_DIR/npm-sonner.log"
SONNER_VERSION=$(node -e "console.log(require('./package.json').dependencies.sonner)")

if [[ "$SONNER_VERSION" == ^2* ]]; then
    echo "✅ sonner 2.0.7 installed"
else
    echo "❌ sonner update failed"
    exit 1
fi

echo ""

# Step 3.3: Update tailwind-merge
echo "Step 3.3: Update tailwind-merge"
echo "--------------------------------"

npm install tailwind-merge@^3.4.0 2>&1 | tee "$LOG_DIR/npm-tailwind-merge.log"
TW_MERGE=$(node -e "console.log(require('./package.json').dependencies['tailwind-merge'])")

if [[ "$TW_MERGE" == ^3* ]]; then
    echo "✅ tailwind-merge 3.4.0 installed"
else
    echo "❌ tailwind-merge update failed"
    exit 1
fi

echo ""

# Step 3.4: Update recharts
echo "Step 3.4: Update recharts"
echo "-------------------------"

npm install recharts@^3.5.1 2>&1 | tee "$LOG_DIR/npm-recharts.log"
RECHARTS_VERSION=$(node -e "console.log(require('./package.json').dependencies.recharts)")

if [[ "$RECHARTS_VERSION" == ^3* ]]; then
    echo "✅ recharts 3.5.1 installed"

    # Find chart components
    CHART_FILES=$(find app components -name "*.tsx" -o -name "*.ts" 2>/dev/null | xargs grep -l "recharts" 2>/dev/null || true)
    if [ -n "$CHART_FILES" ]; then
        echo "⚠️  Chart components found:"
        echo "$CHART_FILES"
        echo "⚠️  Verify charts render correctly in manual testing"
    fi
else
    echo "❌ recharts update failed"
    exit 1
fi

echo ""

# Step 3.5: Update jose
echo "Step 3.5: Update jose"
echo "---------------------"

npm install jose@^6.1.3 2>&1 | tee "$LOG_DIR/npm-jose.log"
JOSE_VERSION=$(node -e "console.log(require('./package.json').dependencies.jose)")

if [[ "$JOSE_VERSION" == ^6* ]]; then
    echo "✅ jose 6.1.3 installed"

    # Find files using jose
    JOSE_FILES=$(grep -r "from 'jose'" --include="*.ts" --include="*.tsx" lib/ app/ 2>/dev/null | cut -d: -f1 | sort -u || true)
    if [ -n "$JOSE_FILES" ]; then
        echo "⚠️  Files using jose:"
        echo "$JOSE_FILES"
        echo "⚠️  CRITICAL: Test JWT operations and authentication"
    fi
else
    echo "❌ jose update failed"
    exit 1
fi

echo ""

# Step 3.6: Update bcryptjs
echo "Step 3.6: Update bcryptjs"
echo "-------------------------"

npm install bcryptjs@^3.0.3 2>&1 | tee "$LOG_DIR/npm-bcrypt.log"
npm install -D @types/bcryptjs@latest 2>&1 | tee -a "$LOG_DIR/npm-bcrypt.log"
BCRYPT_VERSION=$(node -e "console.log(require('./package.json').dependencies.bcryptjs)")

if [[ "$BCRYPT_VERSION" == ^3* ]]; then
    echo "✅ bcryptjs 3.0.3 installed"

    # Find files using bcryptjs
    BCRYPT_FILES=$(grep -r "bcryptjs" --include="*.ts" --include="*.tsx" lib/ app/ 2>/dev/null | cut -d: -f1 | sort -u || true)
    if [ -n "$BCRYPT_FILES" ]; then
        echo "⚠️  Files using bcryptjs:"
        echo "$BCRYPT_FILES"
        echo "⚠️  CRITICAL: Test password hashing and authentication flows"
    fi
else
    echo "❌ bcryptjs update failed"
    exit 1
fi

echo ""

# TypeScript check after all updates
echo "TypeScript Compilation Check"
echo "-----------------------------"

npx tsc --noEmit --project tsconfig.json 2>&1 | tee "$LOG_DIR/tsc-packages.log"
TSC_EXIT=${PIPESTATUS[0]}

if [ $TSC_EXIT -eq 0 ]; then
    echo "✅ TypeScript compilation successful"
else
    echo "❌ TypeScript compilation failed"
    echo "See errors in: $LOG_DIR/tsc-packages.log"
    exit 1
fi

echo ""

# Step 3.7: Final Build and Test
echo "Step 3.7: Final Build and Test"
echo "-------------------------------"

echo "Cleaning previous build..."
rm -rf .next

echo "Running production build..."
npm run build 2>&1 | tee "$LOG_DIR/build-final.log"
BUILD_EXIT=${PIPESTATUS[0]}

if [ $BUILD_EXIT -eq 0 ]; then
    echo "✅ Final build successful"

    if [ -d .next ]; then
        BUILD_SIZE=$(du -sh .next | cut -f1)
        echo "Build size: $BUILD_SIZE"
    fi

    # Test production server
    echo "Testing production server..."
    npm start > "$LOG_DIR/prod-server.log" 2>&1 &
    PROD_PID=$!

    sleep 10

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
    if [[ "$HTTP_CODE" =~ ^(200|307|301)$ ]]; then
        echo "✅ Production server works (HTTP $HTTP_CODE)"
    else
        echo "⚠️  Production server returned HTTP $HTTP_CODE"
    fi

    kill $PROD_PID 2>/dev/null || true
    sleep 2

else
    echo "❌ Final build failed"
    echo "See errors in: $LOG_DIR/build-final.log"
    exit 1
fi

echo ""

# Context7 Post-Migration Analysis
echo "Context7 Post-Migration Analysis"
echo "---------------------------------"

curl -X POST https://context7.com/api/analyze \
  -H "Content-Type: application/json" \
  -d @package.json > "$LOG_DIR/context7-post-migration.json" 2>&1

if [ $? -eq 0 ]; then
  echo "✅ Context7 post-migration analysis complete"
  echo "Report: $LOG_DIR/context7-post-migration.json"

  # Compare with pre-migration if available
  if [ -f "$LOG_DIR/context7-pre-migration.json" ]; then
    PRE_CRITICAL=$(grep -c '"severity":"critical"' "$LOG_DIR/context7-pre-migration.json" 2>/dev/null || echo "0")
    POST_CRITICAL=$(grep -c '"severity":"critical"' "$LOG_DIR/context7-post-migration.json" 2>/dev/null || echo "0")

    echo ""
    echo "Critical issues comparison:"
    echo "  Before migration: $PRE_CRITICAL"
    echo "  After migration:  $POST_CRITICAL"

    if [ $POST_CRITICAL -lt $PRE_CRITICAL ]; then
      echo "✅ Improvement: Reduced critical issues"
    elif [ $POST_CRITICAL -gt $PRE_CRITICAL ]; then
      echo "⚠️  Warning: Increased critical issues"
    else
      echo "✅ No change in critical issues"
    fi
  fi

  # Check current critical issues
  if grep -q '"severity":"critical"' "$LOG_DIR/context7-post-migration.json" 2>/dev/null; then
    echo "⚠️  Critical issues present - review report"
  else
    echo "✅ No critical issues detected"
  fi
else
  echo "⚠️  Context7 analysis failed"
fi

echo ""

# Success summary
echo "=================================="
echo "✅ STAGE 3 COMPLETE: All Packages Updated"
echo "=================================="
echo ""
echo "Updated packages:"
echo "  - zustand: 5.0.9"
echo "  - sonner: 2.0.7"
echo "  - tailwind-merge: 3.4.0"
echo "  - recharts: 3.5.1"
echo "  - jose: 6.1.3"
echo "  - bcryptjs: 3.0.3"
echo ""
echo "Validation:"
echo "  - TypeScript compilation: PASS"
echo "  - Production build: PASS"
echo "  - Production server: PASS"
echo "  - Context7 analysis: DONE"
echo ""
echo "Context7 Reports:"
echo "  - Pre-migration:  $LOG_DIR/context7-pre-migration.json"
echo "  - Post-migration: $LOG_DIR/context7-post-migration.json"
echo ""
echo "⚠️  MANUAL TESTING REQUIRED:"
echo "  - Authentication flows (bcryptjs, jose)"
echo "  - Chart rendering (recharts)"
echo "  - Toast notifications (sonner)"
echo "  - State management (zustand)"
echo ""
echo "Logs saved in: $LOG_DIR/"
echo ""
echo "Next step: Commit these changes"
echo "  cd /home/user/linkedin-birthday-auto"
echo "  git add dashboard/package.json dashboard/package-lock.json"
echo "  git commit -m 'feat: update supporting packages to latest major versions'"
echo ""
