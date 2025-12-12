#!/bin/bash
# Stage 1: React 19 Migration - Automated Script
# This script executes all steps for React 19 migration with validation

set -e  # Exit on error

DASHBOARD_DIR="/home/user/linkedin-birthday-auto/dashboard"
LOG_DIR="/tmp/migration-logs"
mkdir -p "$LOG_DIR"

echo "=================================="
echo "STAGE 1: React 19 Migration"
echo "=================================="
echo ""

# Change to dashboard directory
cd "$DASHBOARD_DIR"

# Step 1.1: Pre-Migration Audit
echo "Step 1.1: Pre-Migration Code Audit"
echo "-----------------------------------"

echo "Searching for defaultProps..."
grep -r "defaultProps" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | tee "$LOG_DIR/defaultProps.txt" || true
DEFAULTPROPS_COUNT=$(grep -r "defaultProps" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | wc -l)

echo "Searching for forwardRef..."
grep -r "forwardRef" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | tee "$LOG_DIR/forwardRef.txt" || true
FORWARDREF_COUNT=$(grep -r "forwardRef" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | wc -l)

echo "Searching for string refs..."
grep -r 'ref="' --include="*.tsx" --include="*.jsx" app/ components/ 2>/dev/null | tee "$LOG_DIR/stringRefs.txt" || true
STRINGREF_COUNT=$(grep -r 'ref="' --include="*.tsx" --include="*.jsx" app/ components/ 2>/dev/null | wc -l)

echo "Searching for propTypes..."
grep -r "propTypes" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | tee "$LOG_DIR/propTypes.txt" || true
PROPTYPES_COUNT=$(grep -r "propTypes" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | wc -l)

cat > "$LOG_DIR/react19-audit.txt" <<EOF
React 19 Pre-Migration Audit Report
===================================
defaultProps: $DEFAULTPROPS_COUNT occurrences
forwardRef: $FORWARDREF_COUNT occurrences
String refs: $STRINGREF_COUNT occurrences
propTypes: $PROPTYPES_COUNT occurrences
EOF

cat "$LOG_DIR/react19-audit.txt"
echo ""

if [ $DEFAULTPROPS_COUNT -gt 0 ] || [ $FORWARDREF_COUNT -gt 0 ] || [ $STRINGREF_COUNT -gt 0 ] || [ $PROPTYPES_COUNT -gt 0 ]; then
    echo "⚠️  Deprecated patterns found!"
    echo "⚠️  Manual fixes required before continuing"
    echo "⚠️  See logs in: $LOG_DIR/"
    echo ""
    echo "Please fix these patterns and re-run this script."
    exit 1
else
    echo "✅ No deprecated patterns found"
fi

echo ""

# Step 1.3: Update React Dependencies
echo "Step 1.3: Update React Dependencies"
echo "------------------------------------"

echo "Installing React 19..."
npm install react@^19.2.1 react-dom@^19.2.1 2>&1 | tee "$LOG_DIR/npm-install-react.log"

echo "Installing TypeScript types..."
npm install -D @types/react@^19 @types/react-dom@^19 2>&1 | tee -a "$LOG_DIR/npm-install-react.log"

# Verify versions
REACT_VERSION=$(node -e "console.log(require('./package.json').dependencies.react)")
REACT_DOM_VERSION=$(node -e "console.log(require('./package.json').dependencies['react-dom'])")

echo ""
echo "Installed versions:"
echo "  React: $REACT_VERSION"
echo "  React-DOM: $REACT_DOM_VERSION"

if [[ "$REACT_VERSION" == ^19* ]] && [[ "$REACT_DOM_VERSION" == ^19* ]]; then
    echo "✅ React 19 installed successfully"
else
    echo "❌ React 19 installation failed"
    exit 1
fi

echo ""

# Step 1.4: Update React-Dependent Packages
echo "Step 1.4: Update React-Dependent Packages"
echo "------------------------------------------"

echo "Updating Radix UI packages..."
npm install \
  @radix-ui/react-dialog@latest \
  @radix-ui/react-dropdown-menu@latest \
  @radix-ui/react-icons@latest \
  @radix-ui/react-label@latest \
  @radix-ui/react-progress@latest \
  @radix-ui/react-select@latest \
  @radix-ui/react-slot@latest \
  @radix-ui/react-switch@latest \
  @radix-ui/react-tabs@latest \
  @radix-ui/react-toast@latest \
  2>&1 | tee "$LOG_DIR/npm-install-radix.log"

# Check for peer dependency issues
echo "Checking for peer dependency issues..."
npm list react 2>&1 | grep -i "UNMET PEER DEPENDENCY" && {
    echo "❌ Peer dependency issues detected"
    npm list react
    exit 1
} || {
    echo "✅ No peer dependency issues"
}

echo ""

# Step 1.5: TypeScript Compilation Check
echo "Step 1.5: TypeScript Compilation Check"
echo "---------------------------------------"

npx tsc --noEmit --project tsconfig.json 2>&1 | tee "$LOG_DIR/tsc-react19.log"
TSC_EXIT=${PIPESTATUS[0]}

if [ $TSC_EXIT -eq 0 ]; then
    echo "✅ TypeScript compilation successful"
else
    echo "❌ TypeScript compilation failed"
    echo "See errors in: $LOG_DIR/tsc-react19.log"
    exit 1
fi

echo ""

# Step 1.6: Build Test
echo "Step 1.6: Build Test"
echo "--------------------"

echo "Cleaning previous build..."
rm -rf .next

echo "Running production build..."
npm run build 2>&1 | tee "$LOG_DIR/build-react19.log"
BUILD_EXIT=${PIPESTATUS[0]}

if [ $BUILD_EXIT -eq 0 ]; then
    echo "✅ Build successful"
    if [ -d .next ]; then
        echo "✅ .next directory created"
    else
        echo "❌ .next directory not found"
        exit 1
    fi
else
    echo "❌ Build failed"
    echo "See errors in: $LOG_DIR/build-react19.log"
    exit 1
fi

echo ""

# Step 1.7: Runtime Test
echo "Step 1.7: Runtime Test (Dev Server)"
echo "------------------------------------"

echo "Starting dev server..."
npm run dev > "$LOG_DIR/dev-server-react19.log" 2>&1 &
DEV_PID=$!

echo "Waiting for dev server to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Dev server responding"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Dev server failed to start"
        cat "$LOG_DIR/dev-server-react19.log"
        kill $DEV_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Test server response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
echo "HTTP response code: $HTTP_CODE"

if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "307" ]] || [[ "$HTTP_CODE" == "301" ]]; then
    echo "✅ Server responding correctly"
else
    echo "❌ Server not responding correctly"
    cat "$LOG_DIR/dev-server-react19.log"
    kill $DEV_PID 2>/dev/null
    exit 1
fi

# Check for React errors
if grep -i "error" "$LOG_DIR/dev-server-react19.log" | grep -i "react" > /dev/null; then
    echo "❌ React errors detected"
    grep -i "error" "$LOG_DIR/dev-server-react19.log"
    kill $DEV_PID 2>/dev/null
    exit 1
else
    echo "✅ No React errors detected"
fi

# Stop dev server
kill $DEV_PID 2>/dev/null
sleep 2
echo "✅ Dev server stopped"

echo ""

# Success summary
echo "=================================="
echo "✅ STAGE 1 COMPLETE: React 19"
echo "=================================="
echo ""
echo "Summary:"
echo "  - React 19.2.1 installed"
echo "  - All dependencies updated"
echo "  - TypeScript compilation: PASS"
echo "  - Production build: PASS"
echo "  - Dev server test: PASS"
echo ""
echo "Logs saved in: $LOG_DIR/"
echo ""
echo "Next step: Commit these changes"
echo "  cd /home/user/linkedin-birthday-auto"
echo "  git add dashboard/package.json dashboard/package-lock.json"
echo "  git commit -m 'feat: migrate to React 19'"
echo ""
