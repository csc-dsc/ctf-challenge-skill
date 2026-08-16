#!/bin/bash
set -euo pipefail

# === CTF Challenge Creator Skill Installer ===
# Install from GitHub repo to local Claude Code environment
# Usage: bash install.sh

SKILL_NAME="ctf-challenge-creator"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  CTF Challenge Creator Skill Installer  ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# === Step 1: Verify Docker ===
echo "[1/6] Checking Docker..."
if command -v docker &>/dev/null; then
    echo "  Docker: $(docker --version)"
else
    echo "  WARNING: Docker not found. Docker-based challenge testing will not work."
    echo "  Install Docker from https://docs.docker.com/get-docker/"
fi

# === Step 2: Verify Docker Compose ===
echo "[2/6] Checking Docker Compose..."
if docker compose version &>/dev/null; then
    echo "  Docker Compose: available"
else
    echo "  WARNING: docker compose not found."
fi

# === Step 3: Create directories ===
echo "[3/6] Creating directories..."
mkdir -p "${CLAUDE_DIR}/skills"
mkdir -p "${CLAUDE_DIR}/agents"
mkdir -p "${CODEX_DIR}/skills"
echo "  Directories ready"

# === Step 4: Install skill files ===
echo "[4/6] Installing skill links..."
rm -rf "${HOME}/.agents/skills/${SKILL_NAME}"
rm -rf "${CODEX_DIR}/skills/${SKILL_NAME}"
rm -rf "${CLAUDE_DIR}/skills/${SKILL_NAME}"
ln -s "${REPO_DIR}" "${CODEX_DIR}/skills/${SKILL_NAME}"
ln -s "${REPO_DIR}" "${CLAUDE_DIR}/skills/${SKILL_NAME}"

echo "  Skill files installed"

# === Step 5: Install agent ===
echo "[5/6] Installing agent definition..."
for agent_file in "${REPO_DIR}/agents/"*.md; do
    if [ -f "$agent_file" ]; then
        agent_name=$(basename "$agent_file")
        cp "$agent_file" "${CLAUDE_DIR}/agents/${agent_name}"
        echo "  Agent: ${agent_name}"
    fi
done
echo "  Agent definitions installed"

# === Step 6: Verify ===
echo "[6/6] Verifying installation..."
ERRORS=0

if [ -L "${CLAUDE_DIR}/skills/${SKILL_NAME}" ] && [ -L "${CODEX_DIR}/skills/${SKILL_NAME}" ]; then
    echo "  Skill symlinks: OK"
else
    echo "  Skill symlinks: MISSING"
    ERRORS=$((ERRORS + 1))
fi

if ls "${CLAUDE_DIR}/agents/ctf-reviewer.md" &>/dev/null; then
    echo "  ctf-reviewer agent: OK"
else
    echo "  ctf-reviewer agent: MISSING"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "${CODEX_DIR}/skills/${SKILL_NAME}/SKILL.md" ]; then
    echo "  Codex SKILL.md: OK"
else
    echo "  Codex SKILL.md: MISSING"
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "╔═══════════════════════════════╗"
    echo "║  Installation Successful!   ║"
    echo "╚═══════════════════════════════╝"
    echo ""
    echo "Installed components:"
    echo "  Source:  ${REPO_DIR}"
    echo "  Codex:   ${CODEX_DIR}/skills/${SKILL_NAME}/ (symlink)"
    echo "  Claude:  ${CLAUDE_DIR}/skills/${SKILL_NAME}/ (symlink)"
    echo "  Agent:   ctf-reviewer"
    echo "  Templates: ${REPO_DIR}/templates/"
    echo ""
    echo "Usage: Just say 'Create a Web SSTI Easy challenge' to start!"
    echo ""
    echo "To uninstall:"
    echo "  rm ${CODEX_DIR}/skills/${SKILL_NAME}"
    echo "  rm ${CLAUDE_DIR}/skills/${SKILL_NAME}"
    echo "  rm ${CLAUDE_DIR}/agents/ctf-reviewer.md"
else
    echo "Installation completed with ${ERRORS} error(s)."
    echo "Please check the output above and retry."
    exit 1
fi
