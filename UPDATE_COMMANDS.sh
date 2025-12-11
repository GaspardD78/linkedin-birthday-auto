#!/bin/bash
# Dependency Update Script for linkedin-bot-dashboard
# Generated: 2025-12-11

cd dashboard || exit 1

echo "========================================="
echo "LinkedIn Bot Dashboard - Dependency Updates"
echo "========================================="
echo ""

# Phase 1: Remove Bloat
echo "Phase 1: Removing unused 'redis' package (using ioredis)..."
npm uninstall redis
echo "✓ Removed redis package"
echo ""

# Phase 2: Safe Updates (Low Risk)
echo "Phase 2: Updating safe packages (low risk)..."

# Update Radix UI components
echo "→ Updating Radix UI components..."
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

# Update other safe packages
echo "→ Updating TanStack Query, Lucide, ioredis, socket.io..."
npm install \
  @tanstack/react-query@latest \
  lucide-react@latest \
  ioredis@latest \
  socket.io-client@latest \
  class-variance-authority@latest \
  clsx@latest \
  react-dropzone@latest

# Update jose to latest 5.x
echo "→ Updating jose to latest 5.x..."
npm install jose@^5.10.0

echo "✓ Phase 2 complete"
echo ""

# Phase 3: Medium Risk Updates
echo "Phase 3: Medium risk updates (requires testing)..."

# Update Next.js within v14
echo "→ Updating Next.js to latest 14.x..."
npm install next@^14.2.33 eslint-config-next@14.2.33

# Update zustand
echo "→ Updating zustand..."
npm install zustand@^4.5.7

# Update next-themes
echo "→ Updating next-themes..."
npm install next-themes@^0.4.6

echo "✓ Phase 3 complete"
echo ""

# Phase 4: Dev Dependencies
echo "Phase 4: Updating development dependencies..."
npm install -D \
  typescript@latest \
  @types/node@^20 \
  @types/react@^18 \
  @types/react-dom@^18 \
  tailwindcss@latest \
  autoprefixer@latest \
  postcss@latest

echo "✓ Phase 4 complete"
echo ""

# Audit and cleanup
echo "Running npm audit and cleanup..."
npm audit fix
npm dedupe

echo ""
echo "========================================="
echo "✓ All safe updates complete!"
echo "========================================="
echo ""
echo "Next steps (requires testing):"
echo "1. Test the application thoroughly"
echo "2. Consider major updates (see DEPENDENCY_AUDIT.md Phase 3)"
echo "   - bcryptjs@^3.0.3"
echo "   - recharts@^3.5.1"
echo "   - sonner@^2.0.7"
echo "   - tailwind-merge@^3.4.0"
echo "3. Plan React 19 migration if needed"
echo "4. Plan Next.js 15/16 migration if needed"
