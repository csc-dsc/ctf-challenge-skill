#!/bin/bash
# Validate a CTF challenge package against the spec
# Usage: bash scripts/validate-package.sh <challenge_dir>
set -euo pipefail

CHALLENGE_DIR="${1:-}"
if [ -z "$CHALLENGE_DIR" ] || [ ! -d "$CHALLENGE_DIR" ]; then
    echo "Usage: bash validate-package.sh <challenge_dir>"
    exit 1
fi

cd "$CHALLENGE_DIR"
DIR_NAME=$(basename "$PWD")
ERRORS=0
WARNINGS=0

echo "=== Validating: $DIR_NAME ==="
echo ""

# Required files
required_files=("README.md" "statement.md" "writeup.md" "flag-policy.md")
for f in "${required_files[@]}"; do
    if [ -f "$f" ]; then
        echo "  [OK] $f"
    else
        echo "  [MISSING] $f"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check naming convention (category-knowledge-difficulty-version)
if echo "$DIR_NAME" | grep -qiE '^[a-z]+-[a-z]+-[a-z]+-v[0-9]+$'; then
    echo "  [OK] Naming: $DIR_NAME"
else
    echo "  [WARN] Naming doesn't match pattern: category-knowledge-difficulty-vN"
    WARNINGS=$((WARNINGS + 1))
fi

# Statement checks
if [ -f "statement.md" ]; then
    # Check for flag leaks in statement
    if grep -qi 'flag{' statement.md 2>/dev/null; then
        echo "  [WARN] statement.md contains 'flag{' - verify it's not the answer"
        WARNINGS=$((WARNINGS + 1))
    fi
    # Check for vague language
    if grep -qi '自己试试\|懂的都懂' statement.md 2>/dev/null; then
        echo "  [FAIL] statement.md contains vague language"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Docker checks
if [ -d "docker" ]; then
    echo ""
    echo "--- Docker checks ---"

    if [ -f "docker/Dockerfile" ]; then
        # Check 0.0.0.0 binding
        if grep -q '127.0.0.1' docker/Dockerfile 2>/dev/null; then
            echo "  [WARN] Dockerfile references 127.0.0.1"
            WARNINGS=$((WARNINGS + 1))
        fi

        # Check non-root user
        if ! grep -q 'USER ctf' docker/Dockerfile 2>/dev/null; then
            echo "  [FAIL] Dockerfile missing USER ctf directive"
            ERRORS=$((ERRORS + 1))
        else
            echo "  [OK] Non-root user"
        fi

        # Check HEALTHCHECK
        if grep -q 'HEALTHCHECK' docker/Dockerfile 2>/dev/null; then
            echo "  [OK] HEALTHCHECK present"
        else
            echo "  [FAIL] HEALTHCHECK missing"
            ERRORS=$((ERRORS + 1))
        fi

        # Check for gcc without build-essential (PWN common mistake)
        if grep -qE '\bgcc\b|g\+\+' docker/Dockerfile 2>/dev/null && ! grep -q 'build-essential' docker/Dockerfile 2>/dev/null; then
            echo "  [FAIL] Dockerfile uses gcc/g++ without build-essential (libc6-dev headers missing)"
            ERRORS=$((ERRORS + 1))
        fi

        # Check exec CMD
        if grep -q 'CMD \[' docker/Dockerfile 2>/dev/null; then
            echo "  [OK] CMD uses exec form"
        else
            echo "  [WARN] CMD may not use exec form"
            WARNINGS=$((WARNINGS + 1))
        fi

        # Validate COPY paths exist under docker/
        echo "  --- COPY path validation ---"
        while IFS= read -r line; do
            # Skip comments and lines without COPY
            case "$line" in
                ''|'#'*) continue ;;
                *COPY*) ;;
                *) continue ;;
            esac
            # Extract source paths from COPY (handle --chown, --from, multiple sources)
            src_list=$(echo "$line" | sed -n 's/.*COPY[[:space:]]\+\(.*\)[[:space:]]\+[^[:space:]]\+$/\1/p')
            for src in $src_list; do
                # Skip flags (--chown=..., --from=...)
                case "$src" in
                    --*) continue ;;
                    *..*)
                        echo "  [FAIL] COPY uses parent directory reference: $src"
                        ERRORS=$((ERRORS + 1))
                        continue
                        ;;
                esac
                if [ -e "docker/$src" ]; then
                    echo "  [OK] docker/$src"
                else
                    echo "  [FAIL] COPY source not found: docker/$src (from: $line)"
                    ERRORS=$((ERRORS + 1))
                fi
            done
        done < docker/Dockerfile
    else
        echo "  [FAIL] docker/Dockerfile missing"
        ERRORS=$((ERRORS + 1))
    fi

    if [ -f "docker/docker-compose.test.yml" ]; then
        # Check port binding format
        if grep -q '0.0.0.0:' docker/docker-compose.test.yml 2>/dev/null; then
            echo "  [OK] docker-compose uses 0.0.0.0 port binding"
        else
            echo "  [FAIL] docker-compose missing 0.0.0.0 port binding"
            ERRORS=$((ERRORS + 1))
        fi

        # Check GZCTF_FLAG in compose
        if grep -q 'GZCTF_FLAG' docker/docker-compose.test.yml 2>/dev/null; then
            echo "  [OK] GZCTF_FLAG in docker-compose"
        else
            echo "  [FAIL] GZCTF_FLAG missing from docker-compose"
            ERRORS=$((ERRORS + 1))
        fi
    fi

    if [ -f "docker/healthcheck.sh" ]; then
        if [ -x "docker/healthcheck.sh" ]; then
            echo "  [OK] healthcheck.sh is executable"
        else
            echo "  [FAIL] healthcheck.sh is not executable"
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

# Source checks
if [ -d "source" ] && [ "$(ls -A source 2>/dev/null)" ]; then
    echo ""
    echo "--- Source checks ---"
    # Check for hardcoded secrets
    if grep -r 'sk-' source/ 2>/dev/null | grep -v '.gitkeep'; then
        echo "  [WARN] Possible API key in source/"
        WARNINGS=$((WARNINGS + 1))
    fi
    # Check for pyc files
    pyc_count=$(find source/ -name '*.pyc' 2>/dev/null | wc -l)
    if [ "$pyc_count" -gt 0 ]; then
        echo "  [FAIL] Found $pyc_count .pyc files in source/"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Attachment checks
if [ -d "attachments" ] && [ "$(ls -A attachments 2>/dev/null)" ]; then
    echo ""
    echo "--- Attachment checks ---"
    # Check for macOS metadata
    if find attachments/ -name '.DS_Store' 2>/dev/null | grep -q .; then
        echo "  [FAIL] .DS_Store found in attachments/"
        ERRORS=$((ERRORS + 1))
    else
        echo "  [OK] No macOS metadata files"
    fi
fi

echo ""
echo "=== Validation Result ==="
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ "$ERRORS" -gt 0 ]; then
    echo "VERDICT: FAIL - $ERRORS error(s) must be fixed"
    exit 1
else
    echo "VERDICT: PASS"
    exit 0
fi
