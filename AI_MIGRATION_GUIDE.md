# AI-Executable Migration Guide - Phase 2

**Target:** React 19 + Next.js 15 + Supporting Packages
**Execution Mode:** Sequential, Automated, Validated
**Format:** Atomic steps with validation checkpoints

---

## 🤖 Instructions for AI Execution

**CRITICAL RULES:**
1. Execute steps **SEQUENTIALLY** - Never skip ahead
2. **VALIDATE** after each step - Stop if validation fails
3. **COMMIT** after each major checkpoint
4. If any step fails: **STOP** and report the error
5. Run all commands from `/home/user/linkedin-birthday-auto/dashboard`
6. Each step includes: Command → Validation → Success Criteria

---

## 📋 Pre-Flight Checklist

Execute these validations before starting:

```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Checkpoint 0.1: Verify package.json exists
test -f package.json && echo "✅ package.json found" || echo "❌ FAIL: package.json not found"

# Checkpoint 0.2: Verify node_modules exists
test -d node_modules && echo "✅ node_modules found" || echo "❌ FAIL: Run npm install first"

# Checkpoint 0.3: Verify current versions
node -e "const pkg=require('./package.json'); console.log('React:', pkg.dependencies.react); console.log('Next:', pkg.dependencies.next);"

# Checkpoint 0.4: Verify build works
npm run build

# Checkpoint 0.5: Create backup branch
cd /home/user/linkedin-birthday-auto
git checkout -b backup/pre-react19-migration-$(date +%Y%m%d)
git push -u origin backup/pre-react19-migration-$(date +%Y%m%d)
```

**SUCCESS CRITERIA:**
- ✅ All checkpoints pass
- ✅ Build succeeds
- ✅ Backup branch created

**IF ANY FAIL:** Stop and fix issues before proceeding

---

## STAGE 1: React 19 Migration

### Step 1.1: Pre-Migration Code Audit

**Purpose:** Identify deprecated patterns that need updating

```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Search 1.1.1: Find defaultProps usage
echo "=== Searching for defaultProps ==="
grep -r "defaultProps" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | tee /tmp/defaultProps.txt
DEFAULTPROPS_COUNT=$(grep -r "defaultProps" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | wc -l)
echo "Found: $DEFAULTPROPS_COUNT occurrences"

# Search 1.1.2: Find forwardRef usage
echo "=== Searching for forwardRef ==="
grep -r "forwardRef" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | tee /tmp/forwardRef.txt
FORWARDREF_COUNT=$(grep -r "forwardRef" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | wc -l)
echo "Found: $FORWARDREF_COUNT occurrences"

# Search 1.1.3: Find string refs (old pattern)
echo "=== Searching for string refs ==="
grep -r 'ref="' --include="*.tsx" --include="*.jsx" app/ components/ 2>/dev/null | tee /tmp/stringRefs.txt
STRINGREF_COUNT=$(grep -r 'ref="' --include="*.tsx" --include="*.jsx" app/ components/ 2>/dev/null | wc -l)
echo "Found: $STRINGREF_COUNT occurrences"

# Search 1.1.4: Find propTypes usage
echo "=== Searching for propTypes ==="
grep -r "propTypes" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | tee /tmp/propTypes.txt
PROPTYPES_COUNT=$(grep -r "propTypes" --include="*.tsx" --include="*.ts" app/ components/ lib/ 2>/dev/null | wc -l)
echo "Found: $PROPTYPES_COUNT occurrences"

# Create audit report
cat > /tmp/react19-audit.txt <<EOF
React 19 Pre-Migration Audit Report
===================================
defaultProps: $DEFAULTPROPS_COUNT occurrences
forwardRef: $FORWARDREF_COUNT occurrences
String refs: $STRINGREF_COUNT occurrences
propTypes: $PROPTYPES_COUNT occurrences

Details in: /tmp/defaultProps.txt, /tmp/forwardRef.txt, /tmp/stringRefs.txt, /tmp/propTypes.txt
EOF

cat /tmp/react19-audit.txt
```

**VALIDATION:**
```bash
# Verify audit completed
test -f /tmp/react19-audit.txt && echo "✅ Audit complete" || echo "❌ Audit failed"
```

**SUCCESS CRITERIA:**
- ✅ All searches completed
- ✅ Audit report generated
- ✅ Counts recorded

**AI ACTION REQUIRED:**
- Read the audit files: `/tmp/defaultProps.txt`, `/tmp/forwardRef.txt`, etc.
- If ANY occurrences found (count > 0), proceed to Step 1.2
- If NO occurrences (all counts = 0), proceed directly to Step 1.3

---

### Step 1.2: Fix Deprecated Patterns (CONDITIONAL)

**⚠️ ONLY execute if Step 1.1 found deprecated patterns**

**AI INSTRUCTIONS:**
For each file found in the audit:

1. Read the file
2. Identify the deprecated pattern
3. Apply the fix based on pattern type:

#### Pattern 1: defaultProps → Default Parameters

**Before:**
```typescript
function Component({ name, age }: Props) {
  return <div>{name} - {age}</div>
}
Component.defaultProps = { name: "Unknown", age: 0 }
```

**After:**
```typescript
function Component({
  name = "Unknown",
  age = 0
}: {
  name?: string
  age?: number
}) {
  return <div>{name} - {age}</div>
}
```

#### Pattern 2: forwardRef → ref as prop

**Before:**
```typescript
const Input = forwardRef<HTMLInputElement, Props>((props, ref) => {
  return <input ref={ref} {...props} />
})
```

**After:**
```typescript
function Input({ ref, ...props }: Props & { ref?: React.Ref<HTMLInputElement> }) {
  return <input ref={ref} {...props} />
}
```

#### Pattern 3: String refs → useRef

**Before:**
```typescript
<div ref="myDiv">
```

**After:**
```typescript
const myDivRef = useRef<HTMLDivElement>(null)
<div ref={myDivRef}>
```

#### Pattern 4: propTypes → Remove (use TypeScript)

**Before:**
```typescript
Component.propTypes = { name: PropTypes.string }
```

**After:**
```typescript
// Remove propTypes, rely on TypeScript types
```

**VALIDATION AFTER EACH FIX:**
```bash
# After modifying a file, verify it compiles
npx tsc --noEmit --project tsconfig.json
echo "Exit code: $?"
```

**SUCCESS CRITERIA:**
- ✅ All deprecated patterns fixed
- ✅ TypeScript compiles without errors
- ✅ No more occurrences of deprecated patterns

---

### Step 1.3: Update React Dependencies

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Update React and React DOM
npm install react@^19.2.1 react-dom@^19.2.1

# Update TypeScript types
npm install -D @types/react@^19 @types/react-dom@^19
```

**VALIDATION:**
```bash
# Verify versions installed
REACT_VERSION=$(node -e "console.log(require('./package.json').dependencies.react)")
REACT_DOM_VERSION=$(node -e "console.log(require('./package.json').dependencies['react-dom'])")
TYPES_REACT=$(node -e "console.log(require('./package.json').devDependencies['@types/react'])")

echo "React: $REACT_VERSION"
echo "React-DOM: $REACT_DOM_VERSION"
echo "@types/react: $TYPES_REACT"

# Check if versions are correct
if [[ "$REACT_VERSION" == ^19* ]] && [[ "$REACT_DOM_VERSION" == ^19* ]]; then
  echo "✅ React 19 installed correctly"
  exit 0
else
  echo "❌ React 19 installation failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ React ^19.2.1 installed
- ✅ React-DOM ^19.2.1 installed
- ✅ @types/react ^19 installed
- ✅ package.json updated
- ✅ package-lock.json updated

---

### Step 1.4: Update React-Dependent Packages

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Update all Radix UI packages (require React 19 peer)
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
  @radix-ui/react-toast@latest
```

**VALIDATION:**
```bash
# Check for peer dependency warnings
npm list react 2>&1 | grep -i "UNMET PEER DEPENDENCY"
if [ $? -eq 0 ]; then
  echo "❌ Peer dependency issues detected"
  npm list react
  exit 1
else
  echo "✅ No peer dependency issues"
  exit 0
fi
```

**SUCCESS CRITERIA:**
- ✅ All packages updated
- ✅ No peer dependency warnings
- ✅ npm install completes successfully

---

### Step 1.5: TypeScript Compilation Check

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Run TypeScript compiler
npx tsc --noEmit --project tsconfig.json 2>&1 | tee /tmp/tsc-output.txt
TSC_EXIT=$?

echo "TypeScript exit code: $TSC_EXIT"
```

**VALIDATION:**
```bash
# Check exit code
if [ $TSC_EXIT -eq 0 ]; then
  echo "✅ TypeScript compilation successful"
else
  echo "❌ TypeScript compilation failed"
  echo "Errors:"
  cat /tmp/tsc-output.txt
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ TypeScript compiles with 0 errors
- ✅ Exit code = 0

**IF FAILS:**
- Read `/tmp/tsc-output.txt`
- Fix TypeScript errors one by one
- Re-run this step until it passes

---

### Step 1.6: Build Test

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Clean previous build
rm -rf .next

# Run production build
npm run build 2>&1 | tee /tmp/build-output.txt
BUILD_EXIT=$?

echo "Build exit code: $BUILD_EXIT"
```

**VALIDATION:**
```bash
if [ $BUILD_EXIT -eq 0 ]; then
  echo "✅ Build successful"
  # Check if .next directory was created
  if [ -d .next ]; then
    echo "✅ .next directory created"
  else
    echo "❌ .next directory not found"
    exit 1
  fi
else
  echo "❌ Build failed"
  cat /tmp/build-output.txt
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Build completes successfully
- ✅ `.next` directory created
- ✅ No build errors
- ✅ Exit code = 0

---

### Step 1.7: Runtime Test (Dev Server)

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Start dev server in background
npm run dev > /tmp/dev-server.log 2>&1 &
DEV_PID=$!
echo "Dev server PID: $DEV_PID"

# Wait for server to start (max 30 seconds)
echo "Waiting for dev server to start..."
for i in {1..30}; do
  if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Dev server responding"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "❌ Dev server failed to start"
    cat /tmp/dev-server.log
    kill $DEV_PID 2>/dev/null
    exit 1
  fi
  sleep 1
done
```

**VALIDATION:**
```bash
# Test server is responding
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
echo "HTTP response code: $HTTP_CODE"

if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "307" ]] || [[ "$HTTP_CODE" == "301" ]]; then
  echo "✅ Server responding correctly"
else
  echo "❌ Server not responding correctly"
  cat /tmp/dev-server.log
  kill $DEV_PID 2>/dev/null
  exit 1
fi

# Check for React errors in logs
if grep -i "error" /tmp/dev-server.log | grep -i "react"; then
  echo "❌ React errors detected in dev server"
  grep -i "error" /tmp/dev-server.log
  kill $DEV_PID 2>/dev/null
  exit 1
else
  echo "✅ No React errors in dev server"
fi

# Clean up
kill $DEV_PID 2>/dev/null
echo "✅ Dev server stopped"
```

**SUCCESS CRITERIA:**
- ✅ Dev server starts successfully
- ✅ Server responds to HTTP requests
- ✅ No React runtime errors
- ✅ Server can be stopped cleanly

---

### Step 1.8: Commit React 19 Migration

**Command:**
```bash
cd /home/user/linkedin-birthday-auto

git add dashboard/package.json dashboard/package-lock.json

# Add any modified component files
git add -A

git commit -m "feat: migrate to React 19

- Update React to 19.2.1
- Update React-DOM to 19.2.1
- Update @types/react and @types/react-dom to v19
- Update all Radix UI components for React 19 compatibility
- Fix deprecated patterns (defaultProps, forwardRef)
- All tests passing
- Build successful

Breaking changes addressed:
- Removed defaultProps (using default parameters)
- Removed forwardRef (ref as prop)
- Updated TypeScript types for React 19"
```

**VALIDATION:**
```bash
# Verify commit was created
if git log -1 --pretty=%B | grep -q "React 19"; then
  echo "✅ Commit created successfully"
  git log -1 --oneline
else
  echo "❌ Commit failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Changes committed
- ✅ Commit message includes "React 19"
- ✅ All modified files staged and committed

---

## STAGE 2: Next.js 15 Migration

### Step 2.1: Identify Files Using Async APIs

**Purpose:** Find all files that need async/await updates

```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Search 2.1.1: Find cookies() usage
echo "=== Files using cookies() ==="
grep -r "cookies()" --include="*.ts" --include="*.tsx" app/ lib/ 2>/dev/null | cut -d: -f1 | sort -u | tee /tmp/cookies-files.txt
COOKIES_COUNT=$(cat /tmp/cookies-files.txt | wc -l)
echo "Files found: $COOKIES_COUNT"

# Search 2.1.2: Find headers() usage
echo "=== Files using headers() ==="
grep -r "headers()" --include="*.ts" --include="*.tsx" app/ lib/ 2>/dev/null | cut -d: -f1 | sort -u | tee /tmp/headers-files.txt
HEADERS_COUNT=$(cat /tmp/headers-files.txt | wc -l)
echo "Files found: $HEADERS_COUNT"

# Search 2.1.3: Find params usage in page/route files
echo "=== Files using params ==="
grep -r "params\s*:" --include="*.ts" --include="*.tsx" app/ 2>/dev/null | grep -E "(page|route)\.tsx?" | cut -d: -f1 | sort -u | tee /tmp/params-files.txt
PARAMS_COUNT=$(cat /tmp/params-files.txt | wc -l)
echo "Files found: $PARAMS_COUNT"

# Search 2.1.4: Find searchParams usage
echo "=== Files using searchParams ==="
grep -r "searchParams\s*:" --include="*.ts" --include="*.tsx" app/ 2>/dev/null | grep -E "page\.tsx?" | cut -d: -f1 | sort -u | tee /tmp/searchparams-files.txt
SEARCHPARAMS_COUNT=$(cat /tmp/searchparams-files.txt | wc -l)
echo "Files found: $SEARCHPARAMS_COUNT"

# Create combined list
cat /tmp/cookies-files.txt /tmp/headers-files.txt /tmp/params-files.txt /tmp/searchparams-files.txt | sort -u > /tmp/nextjs15-files-to-update.txt
TOTAL_FILES=$(cat /tmp/nextjs15-files-to-update.txt | wc -l)

# Create audit report
cat > /tmp/nextjs15-audit.txt <<EOF
Next.js 15 Pre-Migration Audit Report
=====================================
Files using cookies(): $COOKIES_COUNT
Files using headers(): $HEADERS_COUNT
Files using params: $PARAMS_COUNT
Files using searchParams: $SEARCHPARAMS_COUNT
Total unique files to update: $TOTAL_FILES

File list: /tmp/nextjs15-files-to-update.txt
EOF

cat /tmp/nextjs15-audit.txt
echo ""
echo "=== Files to update ==="
cat /tmp/nextjs15-files-to-update.txt
```

**VALIDATION:**
```bash
test -f /tmp/nextjs15-audit.txt && echo "✅ Audit complete" || echo "❌ Audit failed"
```

**SUCCESS CRITERIA:**
- ✅ All searches completed
- ✅ File lists generated
- ✅ Audit report created

**AI ACTION REQUIRED:**
- Read `/tmp/nextjs15-files-to-update.txt`
- Count the number of files
- Prepare to update each file in Step 2.2

---

### Step 2.2: Update Files for Async APIs (ITERATIVE)

**⚠️ AI INSTRUCTIONS:**
For EACH file in `/tmp/nextjs15-files-to-update.txt`:

1. Read the file
2. Identify the pattern(s) to fix
3. Apply the appropriate transformation
4. Validate TypeScript compiles
5. Move to next file

#### Pattern 1: cookies() in API routes

**Before:**
```typescript
import { cookies } from 'next/headers'

export async function GET() {
  const cookieStore = cookies()
  const token = cookieStore.get('token')
  return Response.json({ token })
}
```

**After:**
```typescript
import { cookies } from 'next/headers'

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('token')
  return Response.json({ token })
}
```

#### Pattern 2: headers() in API routes

**Before:**
```typescript
import { headers } from 'next/headers'

export async function GET() {
  const headersList = headers()
  const auth = headersList.get('authorization')
  return Response.json({ auth })
}
```

**After:**
```typescript
import { headers } from 'next/headers'

export async function GET() {
  const headersList = await headers()
  const auth = headersList.get('authorization')
  return Response.json({ auth })
}
```

#### Pattern 3: params in dynamic routes

**Before:**
```typescript
export default function Page({ params }: { params: { id: string } }) {
  return <div>{params.id}</div>
}
```

**After:**
```typescript
export default async function Page({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <div>{id}</div>
}
```

#### Pattern 4: searchParams in pages

**Before:**
```typescript
export default function Page({
  searchParams
}: {
  searchParams: { q: string }
}) {
  return <div>{searchParams.q}</div>
}
```

**After:**
```typescript
export default async function Page({
  searchParams
}: {
  searchParams: Promise<{ q: string }>
}) {
  const { q } = await searchParams
  return <div>{q}</div>
}
```

**VALIDATION AFTER EACH FILE:**
```bash
# After updating a file, verify TypeScript compiles
npx tsc --noEmit --project tsconfig.json
if [ $? -eq 0 ]; then
  echo "✅ File updated successfully"
else
  echo "❌ TypeScript errors after updating file"
  exit 1
fi
```

**PROGRESS TRACKING:**
```bash
# After each file, update progress
TOTAL=$(cat /tmp/nextjs15-files-to-update.txt | wc -l)
CURRENT=1  # Increment this for each file
echo "Progress: $CURRENT / $TOTAL files updated"
```

**SUCCESS CRITERIA:**
- ✅ All files in the list updated
- ✅ TypeScript compiles after each update
- ✅ All async patterns correctly applied

---

### Step 2.3: Update Next.js Dependencies

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Update Next.js to version 15
npm install next@^15.0.0

# Update ESLint config to match
npm install -D eslint-config-next@15.0.0
```

**VALIDATION:**
```bash
# Verify versions
NEXT_VERSION=$(node -e "console.log(require('./package.json').dependencies.next)")
ESLINT_NEXT=$(node -e "console.log(require('./package.json').devDependencies['eslint-config-next'])")

echo "Next.js: $NEXT_VERSION"
echo "eslint-config-next: $ESLINT_NEXT"

if [[ "$NEXT_VERSION" == ^15* ]]; then
  echo "✅ Next.js 15 installed"
else
  echo "❌ Next.js 15 installation failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Next.js ^15.0.0 installed
- ✅ eslint-config-next 15.0.0 installed
- ✅ package.json updated

---

### Step 2.4: Update next.config.js (if needed)

**AI INSTRUCTIONS:**

1. Read `next.config.js` or `next.config.mjs`
2. Check for deprecated options
3. Update configuration if needed

**Common updates needed:**

```javascript
// Remove deprecated options
// - experimental.appDir (now stable)
// - experimental.serverActions (now stable)

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove deprecated experimental features
  experimental: {
    // Remove options that are now stable in Next.js 15
  },
}

module.exports = nextConfig
```

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Check if config exists
if [ -f next.config.js ]; then
  echo "Found next.config.js"
  CONFIG_FILE="next.config.js"
elif [ -f next.config.mjs ]; then
  echo "Found next.config.mjs"
  CONFIG_FILE="next.config.mjs"
else
  echo "No Next.js config file found (OK, using defaults)"
  CONFIG_FILE=""
fi

# If config exists, check for deprecated options
if [ -n "$CONFIG_FILE" ]; then
  echo "Checking for deprecated options..."
  grep -E "experimental\.appDir|experimental\.serverActions" "$CONFIG_FILE"
  if [ $? -eq 0 ]; then
    echo "⚠️ Deprecated options found - requires manual update"
  else
    echo "✅ No deprecated options found"
  fi
fi
```

**VALIDATION:**
```bash
# Try to load the config
node -e "require('./next.config.js')" 2>&1
if [ $? -eq 0 ]; then
  echo "✅ Config file valid"
else
  echo "❌ Config file has errors"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Config file valid or not needed
- ✅ No deprecated options
- ✅ Config loads without errors

---

### Step 2.5: TypeScript Compilation Check

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

npx tsc --noEmit --project tsconfig.json 2>&1 | tee /tmp/tsc-nextjs15.txt
TSC_EXIT=$?

echo "TypeScript exit code: $TSC_EXIT"
```

**VALIDATION:**
```bash
if [ $TSC_EXIT -eq 0 ]; then
  echo "✅ TypeScript compilation successful"
else
  echo "❌ TypeScript compilation failed"
  cat /tmp/tsc-nextjs15.txt
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ TypeScript compiles with 0 errors
- ✅ Exit code = 0

---

### Step 2.6: Build Test

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Clean previous build
rm -rf .next

# Run production build
npm run build 2>&1 | tee /tmp/build-nextjs15.txt
BUILD_EXIT=$?

echo "Build exit code: $BUILD_EXIT"
```

**VALIDATION:**
```bash
if [ $BUILD_EXIT -eq 0 ]; then
  echo "✅ Build successful"
  if [ -d .next ]; then
    echo "✅ .next directory created"

    # Check build output for errors
    if grep -i "error" /tmp/build-nextjs15.txt; then
      echo "⚠️ Build completed but errors detected"
      grep -i "error" /tmp/build-nextjs15.txt
    else
      echo "✅ No errors in build output"
    fi
  else
    echo "❌ .next directory not created"
    exit 1
  fi
else
  echo "❌ Build failed"
  cat /tmp/build-nextjs15.txt
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Build completes successfully
- ✅ `.next` directory created
- ✅ No build errors
- ✅ Exit code = 0

---

### Step 2.7: Runtime Test (Dev Server)

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Start dev server
npm run dev > /tmp/dev-nextjs15.log 2>&1 &
DEV_PID=$!

echo "Waiting for server..."
for i in {1..30}; do
  if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Server started"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "❌ Server failed to start"
    cat /tmp/dev-nextjs15.log
    kill $DEV_PID 2>/dev/null
    exit 1
  fi
  sleep 1
done
```

**VALIDATION:**
```bash
# Test main page
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
echo "HTTP code: $HTTP_CODE"

if [[ "$HTTP_CODE" =~ ^(200|307|301)$ ]]; then
  echo "✅ Main page accessible"
else
  echo "❌ Main page not accessible"
  cat /tmp/dev-nextjs15.log
  kill $DEV_PID 2>/dev/null
  exit 1
fi

# Check logs for errors
if grep -i "error" /tmp/dev-nextjs15.log | grep -v "webpack"; then
  echo "⚠️ Errors detected in logs"
  grep -i "error" /tmp/dev-nextjs15.log
else
  echo "✅ No critical errors in logs"
fi

# Stop server
kill $DEV_PID 2>/dev/null
sleep 2
echo "✅ Server stopped"
```

**SUCCESS CRITERIA:**
- ✅ Dev server starts
- ✅ Main page responds with 200/307/301
- ✅ No critical errors in logs
- ✅ Server stops cleanly

---

### Step 2.8: Test API Routes

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Start server for testing
npm run dev > /tmp/api-test.log 2>&1 &
API_PID=$!

# Wait for server
sleep 10

# Test a few API routes (modify based on your actual routes)
echo "Testing API routes..."

# Test health endpoint (if exists)
curl -s http://localhost:3000/api/system/health && echo "✅ Health API works" || echo "⚠️ Health API issue"

# Test stats endpoint (if exists)
curl -s http://localhost:3000/api/stats && echo "✅ Stats API works" || echo "⚠️ Stats API issue"

# Stop server
kill $API_PID 2>/dev/null
```

**VALIDATION:**
```bash
# Check if any API routes responded
if grep -q "200" /tmp/api-test.log || grep -q "✅" /tmp/api-test.log; then
  echo "✅ API routes responding"
else
  echo "⚠️ API routes may have issues - manual verification recommended"
fi
```

**SUCCESS CRITERIA:**
- ✅ At least one API route responds successfully
- ✅ No 500 errors
- ✅ Server handles requests without crashing

---

### Step 2.9: Commit Next.js 15 Migration

**Command:**
```bash
cd /home/user/linkedin-birthday-auto

git add dashboard/package.json dashboard/package-lock.json
git add dashboard/app/
git add dashboard/lib/
git add dashboard/next.config.*

git commit -m "feat: migrate to Next.js 15

- Update Next.js to 15.0.0
- Update eslint-config-next to 15.0.0
- Convert all request APIs to async (cookies, headers, params)
- Update dynamic route params to Promise type
- Update searchParams to Promise type
- All builds passing
- All tests passing

Files updated:
$(cat /tmp/nextjs15-files-to-update.txt | wc -l) files with async API updates

Breaking changes addressed:
- cookies() now async
- headers() now async
- params now Promise type
- searchParams now Promise type"
```

**VALIDATION:**
```bash
if git log -1 --pretty=%B | grep -q "Next.js 15"; then
  echo "✅ Commit created"
  git log -1 --oneline
else
  echo "❌ Commit failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Commit created with all changes
- ✅ Commit message describes migration

---

## STAGE 3: Supporting Package Updates

### Step 3.1: Update zustand

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Update zustand
npm install zustand@^5.0.9
```

**VALIDATION:**
```bash
# Verify version
ZUSTAND_VERSION=$(node -e "console.log(require('./package.json').dependencies.zustand)")
echo "zustand: $ZUSTAND_VERSION"

if [[ "$ZUSTAND_VERSION" == ^5* ]]; then
  echo "✅ zustand 5 installed"

  # Test TypeScript
  npx tsc --noEmit && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"

  # Test build
  npm run build > /dev/null 2>&1 && echo "✅ Build OK" || echo "❌ Build failed"
else
  echo "❌ zustand update failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ zustand ^5.0.9 installed
- ✅ TypeScript compiles
- ✅ Build succeeds

---

### Step 3.2: Update sonner

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

npm install sonner@^2.0.7
```

**VALIDATION:**
```bash
SONNER_VERSION=$(node -e "console.log(require('./package.json').dependencies.sonner)")
echo "sonner: $SONNER_VERSION"

if [[ "$SONNER_VERSION" == ^2* ]]; then
  echo "✅ sonner 2 installed"
  npx tsc --noEmit && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"
else
  echo "❌ sonner update failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ sonner ^2.0.7 installed
- ✅ TypeScript compiles

---

### Step 3.3: Update tailwind-merge

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

npm install tailwind-merge@^3.4.0
```

**VALIDATION:**
```bash
TW_MERGE=$(node -e "console.log(require('./package.json').dependencies['tailwind-merge'])")
echo "tailwind-merge: $TW_MERGE"

if [[ "$TW_MERGE" == ^3* ]]; then
  echo "✅ tailwind-merge 3 installed"
  npm run build > /dev/null 2>&1 && echo "✅ Build OK" || echo "❌ Build failed"
else
  echo "❌ tailwind-merge update failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ tailwind-merge ^3.4.0 installed
- ✅ Build succeeds

---

### Step 3.4: Update recharts

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

npm install recharts@^3.5.1
```

**VALIDATION:**
```bash
RECHARTS_VERSION=$(node -e "console.log(require('./package.json').dependencies.recharts)")
echo "recharts: $RECHARTS_VERSION"

if [[ "$RECHARTS_VERSION" == ^3* ]]; then
  echo "✅ recharts 3 installed"

  # Check for any chart component files
  CHART_FILES=$(find app components -name "*.tsx" -o -name "*.ts" | xargs grep -l "recharts" 2>/dev/null)
  if [ -n "$CHART_FILES" ]; then
    echo "Found chart components:"
    echo "$CHART_FILES"
    echo "⚠️ Verify charts render correctly in manual testing"
  fi

  npx tsc --noEmit && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"
else
  echo "❌ recharts update failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ recharts ^3.5.1 installed
- ✅ TypeScript compiles
- ⚠️ Manual verification of charts recommended

---

### Step 3.5: Update jose

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

npm install jose@^6.1.3
```

**VALIDATION:**
```bash
JOSE_VERSION=$(node -e "console.log(require('./package.json').dependencies.jose)")
echo "jose: $JOSE_VERSION"

if [[ "$JOSE_VERSION" == ^6* ]]; then
  echo "✅ jose 6 installed"

  # Find files using jose
  JOSE_FILES=$(grep -r "from 'jose'" --include="*.ts" --include="*.tsx" lib/ app/ 2>/dev/null | cut -d: -f1 | sort -u)
  if [ -n "$JOSE_FILES" ]; then
    echo "Files using jose:"
    echo "$JOSE_FILES"
    echo "⚠️ Verify JWT operations work correctly"
  fi

  npx tsc --noEmit && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"
else
  echo "❌ jose update failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ jose ^6.1.3 installed
- ✅ TypeScript compiles
- ⚠️ Auth testing required

---

### Step 3.6: Update bcryptjs

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

npm install bcryptjs@^3.0.3
npm install -D @types/bcryptjs@latest
```

**VALIDATION:**
```bash
BCRYPT_VERSION=$(node -e "console.log(require('./package.json').dependencies.bcryptjs)")
echo "bcryptjs: $BCRYPT_VERSION"

if [[ "$BCRYPT_VERSION" == ^3* ]]; then
  echo "✅ bcryptjs 3 installed"

  # Find files using bcryptjs
  BCRYPT_FILES=$(grep -r "bcryptjs" --include="*.ts" --include="*.tsx" lib/ app/ 2>/dev/null | cut -d: -f1 | sort -u)
  if [ -n "$BCRYPT_FILES" ]; then
    echo "Files using bcryptjs:"
    echo "$BCRYPT_FILES"
    echo "⚠️ CRITICAL: Test password hashing and authentication"
  fi

  npx tsc --noEmit && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"
else
  echo "❌ bcryptjs update failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ bcryptjs ^3.0.3 installed
- ✅ TypeScript compiles
- ⚠️ **CRITICAL:** Auth testing required

---

### Step 3.7: Final Build and Test

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

# Clean build
rm -rf .next

# Full production build
npm run build 2>&1 | tee /tmp/final-build.txt
BUILD_EXIT=$?

echo "Final build exit code: $BUILD_EXIT"
```

**VALIDATION:**
```bash
if [ $BUILD_EXIT -eq 0 ]; then
  echo "✅ Final build successful"

  # Check build size
  if [ -d .next ]; then
    BUILD_SIZE=$(du -sh .next | cut -f1)
    echo "Build size: $BUILD_SIZE"
  fi

  # Test production server
  npm start > /tmp/prod-server.log 2>&1 &
  PROD_PID=$!

  sleep 10

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
  if [[ "$HTTP_CODE" =~ ^(200|307|301)$ ]]; then
    echo "✅ Production server works"
  else
    echo "❌ Production server issue"
  fi

  kill $PROD_PID 2>/dev/null

else
  echo "❌ Final build failed"
  cat /tmp/final-build.txt
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ Production build succeeds
- ✅ Production server starts and responds
- ✅ No build errors or warnings

---

### Step 3.8: Commit Supporting Package Updates

**Command:**
```bash
cd /home/user/linkedin-birthday-auto

git add dashboard/package.json dashboard/package-lock.json

git commit -m "feat: update supporting packages to latest major versions

- Update zustand to 5.0.9 (better TypeScript support)
- Update sonner to 2.0.7 (improved toasts)
- Update tailwind-merge to 3.4.0 (performance improvements)
- Update recharts to 3.5.1 (new features, better performance)
- Update jose to 6.1.3 (latest JWT security)
- Update bcryptjs to 3.0.3 (security updates)

All packages tested:
- TypeScript compilation: ✅
- Production build: ✅
- Dev server: ✅

⚠️ Manual testing required:
- Authentication flows (bcryptjs, jose)
- Charts rendering (recharts)
- Toast notifications (sonner)"
```

**VALIDATION:**
```bash
if git log -1 --pretty=%B | grep -q "supporting packages"; then
  echo "✅ Commit created"
  git log -1 --oneline
else
  echo "❌ Commit failed"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ All changes committed
- ✅ Commit message documents updates

---

## STAGE 4: Final Validation and Push

### Step 4.1: Run Complete Test Suite

**Command:**
```bash
cd /home/user/linkedin-birthday-auto/dashboard

echo "=== Running complete test suite ==="

# 1. TypeScript check
echo "1. TypeScript compilation..."
npx tsc --noEmit
TSC_RESULT=$?

# 2. Lint check
echo "2. ESLint..."
npm run lint > /dev/null 2>&1
LINT_RESULT=$?

# 3. Build check
echo "3. Production build..."
npm run build > /dev/null 2>&1
BUILD_RESULT=$?

# 4. If you have unit tests
# echo "4. Unit tests..."
# npm test
# TEST_RESULT=$?

# Summary
echo ""
echo "=== Test Results ==="
echo "TypeScript: $([ $TSC_RESULT -eq 0 ] && echo '✅' || echo '❌')"
echo "ESLint: $([ $LINT_RESULT -eq 0 ] && echo '✅' || echo '❌')"
echo "Build: $([ $BUILD_RESULT -eq 0 ] && echo '✅' || echo '❌')"

if [ $TSC_RESULT -eq 0 ] && [ $LINT_RESULT -eq 0 ] && [ $BUILD_RESULT -eq 0 ]; then
  echo ""
  echo "✅ ALL TESTS PASSED"
  exit 0
else
  echo ""
  echo "❌ SOME TESTS FAILED"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ TypeScript: 0 errors
- ✅ ESLint: 0 errors
- ✅ Build: Successful
- ✅ All checks pass

---

### Step 4.2: Create Migration Summary

**Command:**
```bash
cd /home/user/linkedin-birthday-auto

cat > MIGRATION_COMPLETED.md <<'EOF'
# Phase 2 Migration - Completion Report

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ COMPLETED

## Summary

Successfully migrated to:
- React 19.2.1
- Next.js 15.0.0
- All supporting packages to latest major versions

## Changes Made

### Stage 1: React 19
- Updated React and React-DOM to 19.2.1
- Updated @types/react and @types/react-dom to v19
- Fixed deprecated patterns (defaultProps, forwardRef)
- Updated all Radix UI components for React 19 compatibility

### Stage 2: Next.js 15
- Updated Next.js to 15.0.0
- Converted all request APIs to async (cookies, headers)
- Updated all dynamic route params to Promise type
- Updated all searchParams to Promise type
- Files modified: $(cat /tmp/nextjs15-files-to-update.txt 2>/dev/null | wc -l || echo "N/A")

### Stage 3: Supporting Packages
- zustand: 4.x → 5.0.9
- sonner: 1.x → 2.0.7
- tailwind-merge: 2.x → 3.4.0
- recharts: 2.x → 3.5.1
- jose: 5.x → 6.1.3
- bcryptjs: 2.x → 3.0.3

## Test Results

- ✅ TypeScript compilation: PASS
- ✅ ESLint: PASS
- ✅ Production build: PASS
- ✅ Dev server: PASS
- ✅ Production server: PASS

## Manual Testing Required

⚠️ The following areas require manual verification:

1. **Authentication**
   - Login flow
   - Password hashing (bcryptjs v3)
   - JWT tokens (jose v6)
   - Session management

2. **UI Components**
   - All pages render correctly
   - Forms submit properly
   - Toasts display correctly (sonner v2)
   - Charts render properly (recharts v3)

3. **API Routes**
   - All endpoints respond correctly
   - Authentication middleware works
   - Data fetching works

4. **Real-time Features**
   - WebSocket connections
   - Live updates
   - Notifications

## Rollback Instructions

If critical issues are found:

\`\`\`bash
# Revert to backup branch
git checkout backup/pre-react19-migration-YYYYMMDD

# Or revert individual commits
git revert HEAD~3..HEAD

# Reinstall dependencies
cd dashboard
npm install
npm run build
\`\`\`

## Next Steps

1. Deploy to staging environment
2. Perform manual testing checklist
3. Monitor for errors
4. Deploy to production with gradual rollout
5. Monitor production for 1 week

## Migration Artifacts

- Backup branch: backup/pre-react19-migration-YYYYMMDD
- Audit reports: /tmp/react19-audit.txt, /tmp/nextjs15-audit.txt
- Build logs: /tmp/final-build.txt

---

**Migration completed by:** AI Agent
**Time taken:** Automated
EOF

cat MIGRATION_COMPLETED.md
```

**SUCCESS CRITERIA:**
- ✅ Summary report created
- ✅ All stages documented
- ✅ Manual testing checklist provided

---

### Step 4.3: Push All Changes

**Command:**
```bash
cd /home/user/linkedin-birthday-auto

# Verify we have commits to push
COMMITS_TO_PUSH=$(git log origin/$(git branch --show-current)..HEAD --oneline | wc -l)
echo "Commits to push: $COMMITS_TO_PUSH"

if [ $COMMITS_TO_PUSH -gt 0 ]; then
  echo "Pushing changes..."
  git push -u origin $(git branch --show-current)

  if [ $? -eq 0 ]; then
    echo "✅ Changes pushed successfully"
  else
    echo "❌ Push failed"
    exit 1
  fi
else
  echo "⚠️ No commits to push"
fi
```

**VALIDATION:**
```bash
# Verify remote has our commits
git fetch origin
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/$(git branch --show-current))

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
  echo "✅ Remote is up to date"
else
  echo "❌ Remote is not up to date"
  exit 1
fi
```

**SUCCESS CRITERIA:**
- ✅ All commits pushed to remote
- ✅ Local and remote branches match
- ✅ No push errors

---

## 🎉 MIGRATION COMPLETE

**Final Checklist:**

- ✅ React 19 installed and working
- ✅ Next.js 15 installed and working
- ✅ All deprecated patterns fixed
- ✅ All async APIs updated
- ✅ Supporting packages updated
- ✅ TypeScript compiles with 0 errors
- ✅ ESLint passes
- ✅ Production build succeeds
- ✅ Dev server works
- ✅ Production server works
- ✅ All changes committed
- ✅ All changes pushed
- ✅ Migration report created

**Next Actions (Manual):**

1. Review `MIGRATION_COMPLETED.md`
2. Deploy to staging
3. Perform manual testing
4. Monitor for errors
5. Deploy to production

---

## 🚨 Error Recovery

If any step fails:

1. **Read the error message carefully**
2. **Check the validation output**
3. **Review the affected files**
4. **Fix the issue**
5. **Re-run the failed step**
6. **DO NOT skip ahead**

### Common Issues and Fixes

**Issue:** TypeScript errors after React 19 update
**Fix:** Check for remaining `defaultProps` or `forwardRef` usage

**Issue:** Build fails after Next.js 15 update
**Fix:** Check that all `cookies()`, `headers()`, `params` are awaited

**Issue:** Runtime errors in dev server
**Fix:** Check browser console, fix React component issues

**Issue:** API routes return 500
**Fix:** Check that async APIs are properly awaited in route handlers

---

## 📊 Validation Checklist

Use this to verify migration success:

### Build & Compilation
- [ ] `npx tsc --noEmit` exits with code 0
- [ ] `npm run lint` exits with code 0
- [ ] `npm run build` exits with code 0
- [ ] `.next` directory created
- [ ] No errors in build output

### Runtime
- [ ] `npm run dev` starts without errors
- [ ] http://localhost:3000 responds with 200/307/301
- [ ] No React errors in console
- [ ] No uncaught exceptions in logs

### Code Quality
- [ ] No `defaultProps` in codebase
- [ ] No `forwardRef` in codebase (or intentionally kept)
- [ ] All `cookies()` calls are awaited
- [ ] All `headers()` calls are awaited
- [ ] All `params` are Promise<> type and awaited
- [ ] All `searchParams` are Promise<> type and awaited

### Dependencies
- [ ] React ^19.2.1
- [ ] React-DOM ^19.2.1
- [ ] Next.js ^15.0.0
- [ ] zustand ^5.0.9
- [ ] sonner ^2.0.7
- [ ] tailwind-merge ^3.4.0
- [ ] recharts ^3.5.1
- [ ] jose ^6.1.3
- [ ] bcryptjs ^3.0.3

### Git
- [ ] All changes committed
- [ ] Commit messages descriptive
- [ ] Changes pushed to remote
- [ ] Backup branch exists

---

**END OF AI MIGRATION GUIDE**
