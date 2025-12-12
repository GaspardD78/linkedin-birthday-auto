# Phase 2 Migration Plan - Major Version Updates

**Date:** 2025-12-11
**Status:** 📋 Planning
**Estimated Total Time:** 3-5 days
**Risk Level:** 🔴 High (Breaking Changes)

---

## Overview

Phase 2 addresses major version updates that contain breaking changes and require:
- Careful migration planning
- Comprehensive testing
- Code modifications
- Potential architecture changes

**Prerequisites:**
- ✅ Phase 1 updates completed (safe updates)
- ✅ All tests passing
- ✅ Application stable in production

---

## 🎯 Migration Priorities

### Priority 1: React 19 Migration
**Impact:** HIGH - Core framework affecting all components
**Estimated Time:** 1-2 days
**Dependencies:** Must be done before Next.js 15/16

### Priority 2: Next.js 15/16 Migration
**Impact:** HIGH - Framework upgrade with significant changes
**Estimated Time:** 2-3 days
**Dependencies:** Requires React 19

### Priority 3: Supporting Package Updates
**Impact:** MEDIUM - Individual package updates
**Estimated Time:** 4-8 hours
**Dependencies:** Should follow React/Next.js updates

---

## 📦 Package Update Matrix

| Package | Current | Target | Breaking Changes | Risk | Priority |
|---------|---------|--------|------------------|------|----------|
| react | 18.3.1 | 19.2.1 | Yes | High | 1 |
| react-dom | 18.3.1 | 19.2.1 | Yes | High | 1 |
| next | 14.2.33 | 15.x or 16.0.8 | Yes | High | 2 |
| bcryptjs | 2.4.3 | 3.0.3 | Yes | Medium | 3 |
| jose | 5.10.0 | 6.1.3 | Yes | Medium | 3 |
| zustand | 4.5.7 | 5.0.9 | Minimal | Low | 3 |
| recharts | 2.12.7 | 3.5.1 | Yes | Medium | 3 |
| sonner | 1.7.4 | 2.0.7 | Minimal | Low | 3 |
| tailwind-merge | 2.6.0 | 3.4.0 | Minimal | Low | 3 |

---

## 🔴 Priority 1: React 19 Migration

### What's New in React 19

**Major Features:**
- React Compiler (automatic optimization)
- Actions (form handling improvements)
- Document metadata support
- Asset loading improvements
- Better hydration error messages
- `use` hook for promises and context
- `ref` as a prop (no more forwardRef)

**Breaking Changes:**
1. **Removed Deprecated APIs:**
   - `defaultProps` for function components (use default params)
   - `propTypes` (use TypeScript)
   - Legacy Context API (`contextTypes`)
   - String refs (use `useRef`)
   - Module pattern factories
   - `ReactDOM.render` (use `ReactDOM.createRoot`)

2. **Behavior Changes:**
   - Errors in `ref` cleanup functions now surface
   - `useReducer` state must be immutable
   - Stricter Strict Mode
   - Changes to `useMemo`/`useCallback` timing

3. **TypeScript Changes:**
   - `ref` prop types updated
   - `children` no longer implicit in props
   - Changes to event handler types

### Migration Steps

#### Step 1: Pre-Migration Audit (2 hours)

```bash
# Search for deprecated patterns
cd dashboard

# Check for defaultProps usage
grep -r "defaultProps" --include="*.tsx" --include="*.ts" .

# Check for propTypes
grep -r "propTypes" --include="*.tsx" --include="*.ts" .

# Check for string refs
grep -r "ref=\"" --include="*.tsx" .

# Check for forwardRef
grep -r "forwardRef" --include="*.tsx" .

# Check for legacy context
grep -r "contextTypes\|childContextTypes" --include="*.tsx" --include="*.ts" .
```

#### Step 2: Code Modifications (4-6 hours)

**A. Update Component Props**

Before:
```typescript
function MyComponent({ title, children }: { title: string }) {
  return <div>{title}{children}</div>
}
MyComponent.defaultProps = { title: "Default" }
```

After:
```typescript
function MyComponent({
  title = "Default",
  children
}: {
  title?: string
  children?: React.ReactNode
}) {
  return <div>{title}{children}</div>
}
```

**B. Replace forwardRef**

Before:
```typescript
const Input = forwardRef<HTMLInputElement, Props>((props, ref) => {
  return <input ref={ref} {...props} />
})
```

After:
```typescript
function Input({ ref, ...props }: Props & { ref?: React.Ref<HTMLInputElement> }) {
  return <input ref={ref} {...props} />
}
```

**C. Update Type Definitions**

Check and update:
- `@types/react` to ^19.0.0
- `@types/react-dom` to ^19.0.0
- Any custom type definitions

#### Step 3: Update Dependencies (1 hour)

```bash
# Update React ecosystem
npm install react@^19.2.1 react-dom@^19.2.1

# Update type definitions
npm install -D @types/react@^19 @types/react-dom@^19

# Update peer dependencies that need React 19
npm install \
  @radix-ui/react-dialog@latest \
  @radix-ui/react-dropdown-menu@latest \
  @radix-ui/react-select@latest \
  @radix-ui/react-tabs@latest \
  @radix-ui/react-toast@latest \
  @radix-ui/react-switch@latest
```

#### Step 4: Testing (3-4 hours)

Create test checklist:
- [ ] Application builds without errors
- [ ] All pages render correctly
- [ ] Forms work properly
- [ ] State management (zustand) works
- [ ] Data fetching (@tanstack/react-query) works
- [ ] All Radix UI components function
- [ ] Theme switching works
- [ ] Toast notifications work
- [ ] WebSocket connections work
- [ ] No console errors or warnings

#### Step 5: Performance Testing (1 hour)

- [ ] Check bundle size changes
- [ ] Monitor initial load time
- [ ] Test React Compiler benefits (optional)
- [ ] Verify no hydration errors

### Rollback Plan

If critical issues arise:
```bash
# Revert to React 18
npm install react@^18.3.1 react-dom@^18.3.1
npm install -D @types/react@^18.3.3 @types/react-dom@^18.3.0

# Rebuild
npm run build
```

### Resources

- [React 19 Upgrade Guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [React 19 Release Notes](https://react.dev/blog/2024/12/05/react-19)
- [Codemod Tool](https://github.com/reactjs/react-codemod)

---

## 🔴 Priority 2: Next.js 15/16 Migration

### Decision Point: Next.js 15 vs 16

**Next.js 15.x (Stable)**
- ✅ More stable, better documented
- ✅ Requires React 19 RC (now stable)
- ✅ Easier migration path
- ⚠️ Missing latest features

**Next.js 16.x (Latest)**
- ✅ Latest features
- ✅ Better performance
- ⚠️ Recently released, less battle-tested
- ⚠️ May have undiscovered issues

**Recommendation:** Start with Next.js 15.x, upgrade to 16 after stabilization

### What's New in Next.js 15

**Major Changes:**
1. **React 19 Support** (required)
2. **Async Request APIs** (breaking)
   - `cookies()`, `headers()`, `params` are now async
3. **Caching Changes** (breaking)
   - `fetch` requests no longer cached by default
   - Route segments no longer cached by default
4. **Middleware Breaking Changes**
5. **Turbopack Dev** (stable)
6. **Improved Error Messages**
7. **Partial Prerendering** (optional)

### Migration Steps

#### Step 1: Pre-Migration Audit (2 hours)

```bash
cd dashboard

# Find usage of request APIs
grep -r "cookies()" --include="*.ts" --include="*.tsx" .
grep -r "headers()" --include="*.ts" --include="*.tsx" .
grep -r "params\." --include="*.ts" --include="*.tsx" .

# Find fetch calls
grep -r "fetch(" --include="*.ts" --include="*.tsx" .

# Check middleware
find . -name "middleware.ts" -o -name "middleware.js"

# Check for deprecated APIs
grep -r "unstable_" --include="*.ts" --include="*.tsx" .
```

#### Step 2: Code Modifications (6-8 hours)

**A. Update Async Request APIs**

Before:
```typescript
// app/api/example/route.ts
export async function GET() {
  const cookieStore = cookies()
  const token = cookieStore.get('token')
  return NextResponse.json({ token })
}
```

After:
```typescript
// app/api/example/route.ts
export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('token')
  return NextResponse.json({ token })
}
```

**B. Update Page Components with Params**

Before:
```typescript
export default function Page({ params }: { params: { id: string } }) {
  return <div>{params.id}</div>
}
```

After:
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

**C. Update Caching Strategy**

Add explicit caching where needed:
```typescript
// Opt-in to caching
fetch('https://api.example.com/data', {
  cache: 'force-cache'
})

// Or revalidate
fetch('https://api.example.com/data', {
  next: { revalidate: 3600 }
})
```

**D. Update Route Segment Config**

```typescript
// Force dynamic rendering if needed
export const dynamic = 'force-dynamic'

// Or force static
export const dynamic = 'force-static'
```

#### Step 3: Update Dependencies (1 hour)

```bash
# Update Next.js to 15.x
npm install next@^15.0.0

# Update ESLint config
npm install -D eslint-config-next@15.0.0

# Check for peer dependency issues
npm install
```

#### Step 4: Update Configuration (30 minutes)

**next.config.js updates:**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable Turbopack for dev (optional)
  // turbo: {},

  // Update experimental features
  experimental: {
    // Remove deprecated options
    // Add new options as needed
  }
}

module.exports = nextConfig
```

#### Step 5: Testing (4-6 hours)

Comprehensive test checklist:
- [ ] Dev server starts: `npm run dev`
- [ ] Build succeeds: `npm run build`
- [ ] Production build runs: `npm start`
- [ ] All routes accessible
- [ ] API routes work correctly
- [ ] Authentication flows work
- [ ] Cookie handling works
- [ ] Headers are set correctly
- [ ] Middleware functions properly
- [ ] Static pages generate correctly
- [ ] Dynamic pages work
- [ ] Image optimization works
- [ ] Font optimization works
- [ ] No build warnings
- [ ] No runtime errors

#### Step 6: Performance Validation (1 hour)

- [ ] Lighthouse score maintained
- [ ] First Contentful Paint (FCP)
- [ ] Largest Contentful Paint (LCP)
- [ ] Time to Interactive (TTI)
- [ ] Bundle size comparison

### Files to Review

Based on your codebase, these files will need updates:

**API Routes (async cookies/headers):**
- `app/api/auth/login/route.ts`
- `app/api/auth/logout/route.ts`
- `app/api/auth/verify-2fa/route.ts`
- `app/api/auth/validate-cookies/route.ts`
- All other API routes that use `cookies()` or `headers()`

**Middleware:**
- `middleware.ts`

**Dynamic Routes (async params):**
- `app/api/blacklist/[id]/route.ts`
- `app/api/crm/contacts/[name]/route.ts`
- `app/api/nurturing/segments/[type]/route.ts`
- `app/api/automation/[...path]/route.ts`
- `app/api/scheduler/[...path]/route.ts`

### Rollback Plan

```bash
# Revert to Next.js 14
npm install next@^14.2.33 eslint-config-next@14.2.33

# Clear cache
rm -rf .next
npm run build
```

### Resources

- [Next.js 15 Upgrade Guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)
- [Next.js 16 Release Notes](https://nextjs.org/blog/next-16)
- [Codemod CLI](https://nextjs.org/docs/app/building-your-application/upgrading/codemods)

```bash
# Use Next.js codemod tool
npx @next/codemod@latest upgrade latest
```

---

## 🟡 Priority 3: Supporting Package Updates

### 3.1 bcryptjs (2.4.3 → 3.0.3)

**Breaking Changes:** API changes in v3

**Files to Review:**
- `app/api/auth/login/route.ts`
- Any password hashing logic

**Migration:**
```bash
# Check current usage
grep -r "bcryptjs" dashboard/

# Review v3 changelog
# https://github.com/dcodeIO/bcrypt.js/releases/tag/3.0.0

# Update
npm install bcryptjs@^3.0.3
npm install -D @types/bcryptjs@latest

# Test authentication flows
```

**Testing:**
- [ ] User login works
- [ ] Password hashing works
- [ ] Password comparison works
- [ ] Existing hashed passwords still validate

**Time:** 2 hours

---

### 3.2 recharts (2.12.7 → 3.5.1)

**Breaking Changes:** Component API changes, TypeScript improvements

**Files to Review:**
```bash
grep -r "recharts" dashboard/
```

Likely dashboard components with charts.

**Migration:**
```bash
npm install recharts@^3.5.1
```

**Changes to Watch:**
- Component prop types may have changed
- Event handler signatures
- TypeScript types

**Testing:**
- [ ] All charts render correctly
- [ ] Interactions work (tooltips, clicks)
- [ ] Responsive behavior maintained
- [ ] Data updates reflect correctly

**Time:** 2-3 hours

---

### 3.3 zustand (4.5.7 → 5.0.9)

**Breaking Changes:** Minimal, mostly TypeScript improvements

**Files to Review:**
```bash
grep -r "zustand" dashboard/
```

**Migration:**
```bash
npm install zustand@^5.0.9
```

**Key Changes:**
- Better TypeScript inference
- Improved DevTools support
- Simplified middleware API

**Testing:**
- [ ] State management works
- [ ] Store subscriptions work
- [ ] Persist middleware works (if used)

**Time:** 1-2 hours

---

### 3.4 jose (5.10.0 → 6.1.3)

**Breaking Changes:** JWT API changes

**Files to Review:**
- `lib/auth.ts`
- Any JWT token handling

**Migration:**
```bash
# Review changelog first
# https://github.com/panva/jose/releases

npm install jose@^6.1.3
```

**Testing:**
- [ ] JWT creation works
- [ ] JWT verification works
- [ ] Token expiration handled
- [ ] All auth flows work

**Time:** 2-3 hours

---

### 3.5 sonner (1.7.4 → 2.0.7)

**Breaking Changes:** Minimal

**Files to Review:**
```bash
grep -r "sonner" dashboard/
```

**Migration:**
```bash
npm install sonner@^2.0.7
```

**Testing:**
- [ ] Toasts display correctly
- [ ] All toast variants work
- [ ] Positioning correct
- [ ] Dismissal works

**Time:** 1 hour

---

### 3.6 tailwind-merge (2.6.0 → 3.4.0)

**Breaking Changes:** Internal improvements, external API mostly stable

**Migration:**
```bash
npm install tailwind-merge@^3.4.0
```

**Testing:**
- [ ] Class merging works correctly
- [ ] No styling regressions
- [ ] Build succeeds

**Time:** 30 minutes

---

## 📋 Complete Migration Timeline

### Week 1: React 19 Migration
- **Day 1-2:** React 19 upgrade and testing
  - Pre-migration audit (2h)
  - Code modifications (4-6h)
  - Update dependencies (1h)
  - Testing (3-4h)
  - Performance testing (1h)

### Week 2: Next.js 15 Migration
- **Day 3-5:** Next.js 15 upgrade and testing
  - Pre-migration audit (2h)
  - Code modifications (6-8h)
  - Update dependencies (1h)
  - Configuration updates (30min)
  - Testing (4-6h)
  - Performance validation (1h)

### Week 3: Supporting Packages
- **Day 6:** Major package updates
  - bcryptjs (2h)
  - recharts (2-3h)
  - jose (2-3h)

- **Day 7:** Minor package updates + Final testing
  - zustand (1-2h)
  - sonner (1h)
  - tailwind-merge (30min)
  - Full integration testing (2-3h)

---

## 🧪 Testing Strategy

### Automated Testing

```bash
# Run all tests
npm test

# Run type checking
npm run type-check

# Run linting
npm run lint

# Build for production
npm run build

# Test production build
npm start
```

### Manual Testing Checklist

#### Authentication
- [ ] Login with credentials
- [ ] 2FA verification
- [ ] Logout
- [ ] Session persistence
- [ ] Cookie handling

#### Dashboard Features
- [ ] All pages load
- [ ] Navigation works
- [ ] Real-time updates (WebSocket)
- [ ] Charts render correctly
- [ ] Forms submit correctly
- [ ] File uploads work

#### API Endpoints
- [ ] All API routes respond
- [ ] Authentication required endpoints protected
- [ ] Data fetching works
- [ ] Error handling correct

#### Performance
- [ ] Page load times acceptable
- [ ] No memory leaks
- [ ] Bundle size reasonable
- [ ] No console errors

### Test Environments

1. **Local Development**
   - Test all features locally
   - Verify hot reload works
   - Check for warnings

2. **Staging Environment**
   - Deploy to staging
   - Full smoke test
   - Performance testing

3. **Production**
   - Gradual rollout
   - Monitor errors
   - Quick rollback ready

---

## 🚨 Risk Mitigation

### Pre-Migration Backup

```bash
# Create backup branch
git checkout -b backup/pre-phase2-migration
git push -u origin backup/pre-phase2-migration

# Tag current state
git tag -a v-pre-phase2 -m "Before Phase 2 migration"
git push origin v-pre-phase2
```

### Feature Flags (Optional)

Consider implementing feature flags for gradual rollout:

```typescript
// lib/feature-flags.ts
export const FEATURE_FLAGS = {
  useReact19Features: process.env.NEXT_PUBLIC_REACT_19 === 'true',
  useNextJs15Features: process.env.NEXT_PUBLIC_NEXTJS_15 === 'true',
}
```

### Monitoring

Set up monitoring for:
- Error rates
- Performance metrics
- User reports
- Build success/failure

### Rollback Triggers

Immediate rollback if:
- Build fails
- Critical features broken
- Performance degrades >20%
- Error rate increases significantly
- User complaints spike

---

## 📊 Success Criteria

Phase 2 migration is successful when:

✅ **Functionality**
- All features work as before
- No regression bugs
- All tests passing

✅ **Performance**
- Build time same or better
- Bundle size same or smaller
- Page load times maintained
- No performance regressions

✅ **Stability**
- No console errors
- No runtime warnings
- Production stable for 1 week

✅ **Code Quality**
- No TypeScript errors
- Linter passes
- Code follows best practices

---

## 📝 Post-Migration Tasks

After successful migration:

1. **Update Documentation**
   - Update README with new versions
   - Document any breaking changes
   - Update developer setup guide

2. **Team Communication**
   - Notify team of changes
   - Share migration lessons learned
   - Update coding standards if needed

3. **Cleanup**
   - Remove old code/comments
   - Update dependencies fully
   - Remove feature flags if used

4. **Monitoring**
   - Continue monitoring for 2 weeks
   - Gather performance data
   - Collect user feedback

---

## 🔧 Useful Commands

```bash
# Check for deprecated React patterns
npx react-codemod rename-unsafe-lifecycles

# Next.js upgrade helper
npx @next/codemod@latest upgrade latest

# Check bundle size
npm run build
npm run analyze # if configured

# Find all TODO comments (migration tasks)
grep -r "TODO" --include="*.ts" --include="*.tsx" dashboard/

# Check TypeScript errors
npx tsc --noEmit

# Update all package locks
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 Resources

### Documentation
- [React 19 Docs](https://react.dev)
- [Next.js 15 Docs](https://nextjs.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

### Migration Guides
- [React 18 → 19 Migration](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [Next.js 14 → 15 Migration](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)

### Community
- [Next.js GitHub Discussions](https://github.com/vercel/next.js/discussions)
- [React GitHub Issues](https://github.com/facebook/react/issues)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/reactjs+nextjs)

---

## 🎯 Next Steps

1. **Review this plan** with the team
2. **Schedule migration** (allow 1-2 weeks)
3. **Complete Phase 1** if not done
4. **Create backup branch**
5. **Begin React 19 migration**

---

**Status Tracking:**
- [ ] Plan reviewed and approved
- [ ] Team informed
- [ ] Phase 1 completed
- [ ] Backup created
- [ ] React 19 migration started
- [ ] React 19 migration completed
- [ ] Next.js 15 migration started
- [ ] Next.js 15 migration completed
- [ ] Supporting packages updated
- [ ] All tests passing
- [ ] Deployed to staging
- [ ] Deployed to production
- [ ] Monitoring stable for 1 week
- [ ] Phase 2 complete ✅
