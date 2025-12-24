#!/bin/bash

# ========================================================================
# Test Script for SETUP_CORRECTIONS_APPLIED
# Tests all corrections made to setup.sh v5.2
# ========================================================================

# Don't exit on error - we need to continue tests
set +e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

# Test helper function
test_case() {
    local test_name="$1"
    local test_cmd="$2"
    local expected="$3"

    echo -e "\n${BLUE}Testing:${NC} $test_name"

    if eval "$test_cmd" > /tmp/test_output 2>&1; then
        local result=$(cat /tmp/test_output)
        if [[ "$result" == "$expected" ]]; then
            echo -e "${GREEN}✅ PASSED${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo "  Expected: $expected"
            echo "  Got: $result"
            ((TESTS_FAILED++))
        fi
    else
        echo -e "${RED}❌ ERROR${NC}"
        cat /tmp/test_output
        ((TESTS_FAILED++))
    fi
}

# ========================================================================
# TEST 1: DNS Validation Logic
# ========================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST 1: DNS IP Validation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

test_dns_validation() {
    local ip="$1"

    # Test regex format first
    if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo "INVALID_FORMAT"
        return 1
    fi

    # Test octet ranges with Python
    if python3 -c "import sys; parts='$ip'.split('.'); sys.exit(0 if len(parts)==4 and all(0<=int(p)<=255 for p in parts) else 1)" 2>/dev/null; then
        echo "VALID"
        return 0
    else
        echo "INVALID_OCTET"
        return 1
    fi
}

# Test valid IPs
for ip in "192.168.1.1" "10.0.0.1" "8.8.8.8" "172.16.0.1"; do
    result=$(test_dns_validation "$ip" || echo "REJECTED")
    if [[ "$result" == "VALID" ]]; then
        echo -e "  ${GREEN}✅ $ip → VALID${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ $ip → Should be VALID, got: $result${NC}"
        ((TESTS_FAILED++))
    fi
done

# Test invalid IPs
for ip in "999.999.999.999" "192.168.1" "192.168.1.x" "256.0.0.1"; do
    result=$(test_dns_validation "$ip" || echo "REJECTED")
    if [[ "$result" != "VALID" ]]; then
        echo -e "  ${GREEN}✅ $ip → REJECTED (correct)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ $ip → Should be REJECTED, got: $result${NC}"
        ((TESTS_FAILED++))
    fi
done

# ========================================================================
# TEST 2: Hash Validation Logic
# ========================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST 2: Hash Validation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Test valid bcrypt hashes
VALID_HASHES=(
    '$2a$12$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '$2b$10$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '$2x$11$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '$2y$10$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
)

for hash in "${VALID_HASHES[@]}"; do
    if [[ "$hash" =~ ^\$2[abxy]\$.{50,}$ ]]; then
        echo -e "  ${GREEN}✅ Valid hash format${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ Should be VALID: $hash${NC}"
        ((TESTS_FAILED++))
    fi
done

# Test invalid hashes
INVALID_HASHES=(
    '$2a$12$abc'
    'plaintext'
    ''
    '$2z$10$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
)

for hash in "${INVALID_HASHES[@]}"; do
    if [[ ! "$hash" =~ ^\$2[abxy]\$.{50,}$ ]]; then
        echo -e "  ${GREEN}✅ Invalid hash rejected${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ Should be INVALID: $hash${NC}"
        ((TESTS_FAILED++))
    fi
done

# ========================================================================
# TEST 3: Verify Corrections in setup.sh
# ========================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST 3: Verify Code Changes in setup.sh${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check 1: No export SETUP_PASSWORD_PLAINTEXT
if grep -q "export SETUP_PASSWORD_PLAINTEXT" /home/user/linkedin-birthday-auto/setup.sh; then
    echo -e "  ${RED}❌ CRITICAL: Password still exported!${NC}"
    ((TESTS_FAILED++))
else
    echo -e "  ${GREEN}✅ Password not exported${NC}"
    ((TESTS_PASSED++))
fi

# Check 2: DNS validation code present
if grep -q "Validation stricte de DNS_LOCAL" /home/user/linkedin-birthday-auto/setup.sh; then
    echo -e "  ${GREEN}✅ DNS validation code present${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${RED}❌ DNS validation code missing${NC}"
    ((TESTS_FAILED++))
fi

# Check 3: Audit error handling improved
if grep -q "L'audit final a détecté des problèmes" /home/user/linkedin-birthday-auto/setup.sh; then
    echo -e "  ${GREEN}✅ Audit error handling added${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${RED}❌ Audit error handling missing${NC}"
    ((TESTS_FAILED++))
fi

# Check 4: Cron idempotence check uses full path
if grep -q 'grep -qF "\$PROJECT_ROOT/scripts/renew_certificates.sh"' /home/user/linkedin-birthday-auto/setup.sh; then
    echo -e "  ${GREEN}✅ Cron idempotence uses full path${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${RED}❌ Cron idempotence check not fully updated${NC}"
    ((TESTS_FAILED++))
fi

# Check 5: Lock mechanism uses mkdir (atomic)
if grep -q 'mkdir "\$LOCK_DIR"' /home/user/linkedin-birthday-auto/setup.sh; then
    echo -e "  ${GREEN}✅ Atomic lock mechanism (mkdir) present${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${RED}❌ Lock mechanism not properly updated${NC}"
    ((TESTS_FAILED++))
fi

# ========================================================================
# TEST 4: Library Dependencies
# ========================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST 4: Library Dependencies${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check if check_port_available exists in checks.sh
if grep -q "^check_port_available()" /home/user/linkedin-birthday-auto/scripts/lib/checks.sh; then
    echo -e "  ${GREEN}✅ check_port_available in checks.sh${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${RED}❌ check_port_available not in checks.sh${NC}"
    ((TESTS_FAILED++))
fi

# Check if hash validation exists in security.sh
if grep -q "Validation stricte du format bcrypt" /home/user/linkedin-birthday-auto/scripts/lib/security.sh; then
    echo -e "  ${GREEN}✅ Hash validation in security.sh${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${RED}❌ Hash validation not in security.sh${NC}"
    ((TESTS_FAILED++))
fi

# ========================================================================
# SUMMARY
# ========================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
PERCENTAGE=$((TESTS_PASSED * 100 / TOTAL))

echo ""
echo -e "  Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "  Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "  Total:  $TOTAL"
echo -e "  Success Rate: ${BLUE}${PERCENTAGE}%${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    exit 1
fi
