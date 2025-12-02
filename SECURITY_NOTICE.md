# 🔴 CRITICAL SECURITY NOTICE

**Date**: 2025-11-30
**Severity**: CRITICAL
**Status**: EXPOSED OPENAI API KEY DETECTED

---

## Issue Summary

An OpenAI API key was found committed in the `.env` file in the git repository history. This poses immediate security and financial risks.

**Affected File**: `.env`
**Exposed Credential**: `OPENAI_API_KEY`
**Financial Risk**: Approximately $100-200/month in unauthorized usage if exploited

---

## Immediate Actions Required

### 1. Rotate OpenAI API Key (URGENT - Within 1 Hour)

**Steps**:
1. Visit [OpenAI API Keys Dashboard](https://platform.openai.com/api-keys)
2. Locate the exposed key (starts with `sk-proj-ncWwU9wl...`)
3. Click "Delete" to revoke the compromised key
4. Click "Create new secret key" to generate a replacement
5. Copy the new key immediately (it will only be shown once)
6. Update your local `.env` file with the new key
7. **DO NOT commit the new key to git**

**Verification**:
```bash
# Test that the old key is revoked (should fail)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-proj-ncWwU9wl..."

# Test that the new key works (should succeed)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_NEW_KEY"
```

---

### 2. Check Billing for Unauthorized Usage

1. Visit [OpenAI Usage Dashboard](https://platform.openai.com/usage)
2. Review usage for the past 30 days
3. Look for:
   - Unexpected spikes in API calls
   - Requests from unknown IP addresses
   - Unusual time patterns (e.g., overnight activity)
   - High-cost model usage (GPT-4, embeddings)

**If unauthorized usage detected**:
- Document all suspicious activity with screenshots
- Contact OpenAI support immediately
- Consider disputing charges

**Estimated Risk**: $100-200/month based on typical unauthorized usage patterns

---

### 3. Remove .env from Git History (Within 24 Hours)

The `.env` file exists in git history even though it's now in `.gitignore`. Anyone with access to the repository can retrieve the exposed key.

#### Option A: Using git-filter-repo (Recommended)

**Install git-filter-repo**:
```bash
# macOS
brew install git-filter-repo

# Linux (Debian/Ubuntu)
sudo apt-get install git-filter-repo

# Python (all platforms)
pip install git-filter-repo
```

**Clean History**:
```bash
# IMPORTANT: Make a backup first
cp -r /Users/harshh/Documents/GitHub/ollama_guardrail /Users/harshh/Documents/GitHub/ollama_guardrail_BACKUP

# Navigate to repository
cd /Users/harshh/Documents/GitHub/ollama_guardrail

# Remove .env from all commits
git filter-repo --invert-paths --path .env --force

# Verify .env is gone from history
git log --all --full-history -- .env
# Should return no results

# Force push to remote (if using GitHub/GitLab)
git push origin --force --all
git push origin --force --tags
```

**Warning**: This rewrites git history. All collaborators must re-clone the repository.

#### Option B: Using BFG Repo-Cleaner (Alternative)

```bash
# Install BFG
brew install bfg  # macOS
# Or download from: https://rtyley.github.io/bfg-repo-cleaner/

# Backup first
cp -r ollama_guardrail ollama_guardrail_BACKUP

# Clean repository
cd ollama_guardrail
bfg --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Force push
git push origin --force --all
```

---

### 4. Prevent Future Exposures

#### A. Create .env.example Template

```bash
# Copy template (done automatically in this PR)
cp .env.example .env

# Edit .env with your actual API key
# NEVER commit .env to git!
```

#### B. Install Pre-commit Hooks

**Install pre-commit**:
```bash
pip install pre-commit
```

**Create `.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.63.0
    hooks:
      - id: trufflehog
        name: TruffleHog Secrets Scan
        args: ['--regex', '--entropy=True']

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

**Setup pre-commit**:
```bash
pre-commit install
pre-commit run --all-files  # Test on existing files
```

Now git will automatically scan for secrets before every commit.

#### C. Use Environment Management

**Recommended Pattern**:
```python
# config.py
import os
from typing import Optional

def get_openai_key() -> Optional[str]:
    """Retrieve OpenAI API key from environment or secrets manager."""
    # Try environment variable first
    key = os.getenv('OPENAI_API_KEY')

    # Fallback to AWS Secrets Manager (production)
    if not key and os.getenv('ENV') == 'production':
        import boto3
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId='openai-api-key')
        key = response['SecretString']

    return key
```

---

## Verification Checklist

After completing the above steps, verify security:

- [ ] Old API key has been revoked in OpenAI dashboard
- [ ] New API key generated and working
- [ ] No unauthorized usage detected in billing
- [ ] `.env` removed from git history (verified with `git log`)
- [ ] `.env.example` created with placeholder values
- [ ] `.env` is in `.gitignore`
- [ ] Pre-commit hooks installed and tested
- [ ] Local `.env` file contains only the new API key
- [ ] All team members notified to re-clone repository (if applicable)

---

## Additional Security Recommendations

### Set Usage Limits in OpenAI Dashboard

1. Visit [OpenAI Organization Settings](https://platform.openai.com/account/org-settings)
2. Set monthly usage limit (e.g., $50/month)
3. Enable email notifications for:
   - Usage thresholds (50%, 75%, 90%)
   - Unusual activity
   - Billing anomalies

### Use Separate Keys for Dev/Prod

- **Development**: Create a separate API key with lower limits
- **Production**: Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- **Testing**: Use mock API responses

### Monitor API Key Usage

**Set up weekly reviews**:
```bash
# Create a script to check OpenAI usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  | jq '.data[] | {date: .date, cost: .cost}'
```

---

## Questions or Issues?

If you encounter problems:

1. **API key not working**: Double-check you copied the entire key
2. **git-filter-repo errors**: Ensure you have no uncommitted changes
3. **Unauthorized usage detected**: Contact OpenAI support immediately
4. **Pre-commit hooks failing**: Check `.pre-commit-config.yaml` syntax

---

## References

- [OpenAI API Key Best Practices](https://platform.openai.com/docs/guides/production-best-practices/api-keys)
- [git-filter-repo Documentation](https://github.com/newren/git-filter-repo)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning)

---

**Last Updated**: 2025-11-30
**Next Review**: After key rotation and git history cleaning
