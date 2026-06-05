#!/usr/bin/env python3
"""
GitHub Repository Setup Script

Sets up a GitHub repository with required secrets for the monitoring workflows.
Uses GitHub API with Personal Access Token.

Usage:
    python execution/setup_github.py --repo owner/repo-name
    python execution/setup_github.py --repo your-name/funding-alert-monitor --create
"""

import os
import sys
import json
import argparse
import base64
import requests
from pathlib import Path
from nacl import encoding, public

from dotenv import load_dotenv

load_dotenv()


def get_public_key(token: str, owner: str, repo: str) -> tuple[str, str]:
    """Get the repository's public key for encrypting secrets."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        print(f"[ERROR] Repository {owner}/{repo} not found or no access")
        print("       Make sure the repo exists and your token has 'repo' scope")
        return None, None

    if not response.ok:
        print(f"[ERROR] Failed to get public key: {response.status_code}")
        print(f"        {response.text}")
        return None, None

    data = response.json()
    return data["key"], data["key_id"]


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a secret using the repository's public key."""
    public_key_bytes = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key_bytes)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def set_secret(token: str, owner: str, repo: str, secret_name: str, encrypted_value: str, key_id: str) -> bool:
    """Set a repository secret."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }

    response = requests.put(url, headers=headers, json=data)

    if response.status_code in (201, 204):
        return True
    else:
        print(f"[ERROR] Failed to set secret {secret_name}: {response.status_code}")
        print(f"        {response.text}")
        return False


def set_variable(token: str, owner: str, repo: str, var_name: str, var_value: str) -> bool:
    """Set a repository variable (non-secret)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/variables/{var_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Try to update first
    data = {"name": var_name, "value": var_value}
    response = requests.patch(url, headers=headers, json=data)

    if response.status_code == 404:
        # Create new variable
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/variables"
        response = requests.post(url, headers=headers, json=data)

    if response.status_code in (201, 204):
        return True
    else:
        print(f"[ERROR] Failed to set variable {var_name}: {response.status_code}")
        print(f"        {response.text}")
        return False


def create_repo(token: str, repo_name: str, private: bool = True) -> tuple[str, str]:
    """Create a new repository."""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    data = {
        "name": repo_name,
        "private": private,
        "auto_init": True,
        "description": "Startup funding alert monitor with source verification, enrichment, and reports."
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        repo_data = response.json()
        return repo_data["owner"]["login"], repo_data["name"]
    elif response.status_code == 422:
        # Repo already exists
        print(f"[INFO] Repository {repo_name} already exists")
        # Get current user
        user_resp = requests.get("https://api.github.com/user", headers=headers)
        if user_resp.ok:
            return user_resp.json()["login"], repo_name
        return None, None
    else:
        print(f"[ERROR] Failed to create repo: {response.status_code}")
        print(f"        {response.text}")
        return None, None


def get_current_user(token: str) -> str:
    """Get the current authenticated user."""
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json()["login"]
    return None


def main():
    parser = argparse.ArgumentParser(description="Set up GitHub repository for monitoring workflows")
    parser.add_argument("--repo", "-r", help="Repository in format owner/repo (default: auto-detect or create)")
    parser.add_argument("--create", action="store_true", help="Create repository if it doesn't exist")
    parser.add_argument("--repo-name", default="funding-alert-monitor", help="Name for new repo (with --create)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()

    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[ERROR] GITHUB_TOKEN not found in environment")
        print("        Add it to your .env file")
        sys.exit(1)

    # Verify token works
    user = get_current_user(token)
    if not user:
        print("[ERROR] GitHub token is invalid or expired")
        sys.exit(1)

    print(f"[OK] Authenticated as: {user}")

    # Determine repository
    if args.repo:
        parts = args.repo.split("/")
        if len(parts) != 2:
            print("[ERROR] Repository must be in format: owner/repo")
            sys.exit(1)
        owner, repo = parts
    elif args.create:
        print(f"\n[INFO] Creating repository: {args.repo_name}")
        if args.dry_run:
            print(f"       [DRY RUN] Would create: {user}/{args.repo_name}")
            owner, repo = user, args.repo_name
        else:
            owner, repo = create_repo(token, args.repo_name)
            if not owner:
                sys.exit(1)
            print(f"[OK] Repository ready: {owner}/{repo}")
    else:
        print("[ERROR] Specify --repo owner/name or use --create to create new repo")
        sys.exit(1)

    print(f"\n[INFO] Setting up repository: {owner}/{repo}")

    # Get public key for secret encryption
    if not args.dry_run:
        public_key, key_id = get_public_key(token, owner, repo)
        if not public_key:
            sys.exit(1)
        print("[OK] Got repository public key")

    # Secrets to set
    secrets = {}

    for base_name in ("TAVILY_API_KEY", "EXA_API_KEY", "APIFY_API_TOKEN"):
        found_any = False
        for index in range(1, 11):
            env_name = base_name if index == 1 else f"{base_name}_{index}"
            value = os.environ.get(env_name)
            if value:
                secrets[env_name] = value
                found_any = True
        if not found_any:
            print(f"[WARN] {base_name} not found")

    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    if perplexity_key:
        secrets["PERPLEXITY_API_KEY"] = perplexity_key

    # Variables to set (non-secret)
    variables = {
        "FUNDING_KEYWORDS": os.environ.get("FUNDING_KEYWORDS", "AI,SaaS,Fintech,Robotics,Infrastructure,Defense,Space,Energy"),
    }

    # Set secrets
    print(f"\n[INFO] Setting {len(secrets)} secrets...")
    for name, value in secrets.items():
        if args.dry_run:
            print(f"       [DRY RUN] Would set secret: {name}")
        else:
            encrypted = encrypt_secret(public_key, value)
            if set_secret(token, owner, repo, name, encrypted, key_id):
                print(f"[OK] Set secret: {name}")
            else:
                print(f"[FAIL] Failed to set: {name}")

    # Set variables
    print(f"\n[INFO] Setting {len(variables)} variables...")
    for name, value in variables.items():
        if args.dry_run:
            print(f"       [DRY RUN] Would set variable: {name} = {value}")
        else:
            if set_variable(token, owner, repo, name, value):
                print(f"[OK] Set variable: {name}")
            else:
                print(f"[FAIL] Failed to set: {name}")

    print(f"""
================================================================================
SETUP COMPLETE
================================================================================

Repository: https://github.com/{owner}/{repo}

Next steps:
1. Push your code to the repository:

   cd "{Path(__file__).parent.parent}"
   git init
   git add .
   git commit -m "Initial commit: funding alert monitor"
   git remote add origin https://github.com/{owner}/{repo}.git
   git push -u origin main

2. The funding alert workflow will start running automatically on its schedule.

3. To trigger manually:
   Go to Actions tab > Select workflow > Run workflow

4. Check logs at:
   https://github.com/{owner}/{repo}/actions
""")


if __name__ == "__main__":
    main()
