#!/bin/bash
# Script to clean sensitive data from git history
# WARNING: This will rewrite git history!

set -e

echo "=== Git History Cleanup Script ==="
echo "WARNING: This script will rewrite git history to remove sensitive data."
echo "This is a destructive operation that will require force-pushing."
echo ""
echo "Sensitive data to remove:"
echo "- User Pool ID: us-east-1_wKpnasV5v"
echo "- App Client ID: 71uqkredjv9aj4icaa2crlvvp3"
echo ""
read -p "Have you backed up your repository? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please backup your repository first:"
    echo "  git clone --mirror https://github.com/yourusername/civicforge.git civicforge-backup"
    exit 1
fi

# Install BFG if not present
if ! command -v bfg &> /dev/null; then
    echo ""
    echo "BFG Repo-Cleaner is not installed."
    echo "Install it using:"
    echo "  brew install bfg  # macOS"
    echo "  # or download from: https://rtyley.github.io/bfg-repo-cleaner/"
    exit 1
fi

# Create replacements file
echo "Creating replacements file..."
cat > bfg-replacements.txt << 'EOF'
us-east-1_wKpnasV5v==>REDACTED_USER_POOL_ID
71uqkredjv9aj4icaa2crlvvp3==>REDACTED_CLIENT_ID
EOF

# Option 1: Using BFG (Recommended)
echo ""
echo "=== Option 1: Using BFG Repo-Cleaner (Recommended) ==="
echo "Run these commands:"
echo ""
echo "# 1. Clone a fresh copy"
echo "git clone --mirror https://github.com/yourusername/civicforge.git civicforge-clean.git"
echo ""
echo "# 2. Run BFG to replace sensitive text"
echo "cd civicforge-clean.git"
echo "bfg --replace-text ../bfg-replacements.txt"
echo ""
echo "# 3. Clean up"
echo "git reflog expire --expire=now --all && git gc --prune=now --aggressive"
echo ""
echo "# 4. Push changes"
echo "git push --force"

# Option 2: Using git filter-branch (Alternative)
echo ""
echo "=== Option 2: Using git filter-branch (Alternative) ==="
echo "Run this command (slower but no additional tools needed):"
echo ""
cat << 'FILTER_SCRIPT'
git filter-branch --tree-filter '
  find . -type f -name "*.md" -o -name "*.env*" -o -name "*.yml" | while read file; do
    if [ -f "$file" ]; then
      sed -i "" "s/us-east-1_wKpnasV5v/REDACTED_USER_POOL_ID/g" "$file"
      sed -i "" "s/71uqkredjv9aj4icaa2crlvvp3/REDACTED_CLIENT_ID/g" "$file"
    fi
  done
' --tag-name-filter cat -- --all
FILTER_SCRIPT

echo ""
echo "=== After Cleanup ==="
echo "1. Verify the cleanup:"
echo "   git grep -i 'us-east-1_wKpnasV5v' \$(git rev-list --all)"
echo "   git grep -i '71uqkredjv9aj4icaa2crlvvp3' \$(git rev-list --all)"
echo ""
echo "2. Force push to all remotes:"
echo "   git push origin --force --all"
echo "   git push origin --force --tags"
echo ""
echo "3. Contact all contributors to re-clone the repository"
echo ""
echo "4. Clean up local references:"
echo "   rm -rf .git/refs/original/"
echo "   git reflog expire --expire=now --all"
echo "   git gc --prune=now --aggressive"
echo ""
echo "=== Security Note ==="
echo "Even after cleaning git history, assume these credentials are compromised."
echo "Always rotate credentials after any potential exposure!"