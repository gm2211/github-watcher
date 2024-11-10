#!/usr/bin/env python3
import argparse
import sys
import requests
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def from_string(cls, version_str: str) -> 'Version':
        # Remove 'v' prefix if present
        version_str = version_str.lstrip('v')
        try:
            major, minor, patch = map(int, version_str.split('.'))
            return cls(major=major, minor=minor, patch=patch)
        except ValueError as e:
            raise ValueError(f"Invalid version string: {version_str}") from e

    def bump_major(self) -> 'Version':
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> 'Version':
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> 'Version':
        return Version(self.major, self.minor, self.patch + 1)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

def get_github_token():
    """Get GitHub token from keychain, prompt if missing"""
    KEYCHAIN_SERVICE = "github-watcher"
    KEYCHAIN_ACCOUNT = "github-token"
    
    try:
        # Try to get token from keychain
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s", KEYCHAIN_SERVICE,
                "-a", KEYCHAIN_ACCOUNT,
                "-w"
            ],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Error accessing keychain: {e}")
    
    # If token not found or error occurred, prompt user
    print("\nGitHub token not found in keychain.")
    print("Please create a new token with 'repo' scope at: https://github.com/settings/tokens")
    token = input("Enter your GitHub token: ").strip()
    
    if not token:
        print("No token provided. Aborting.")
        sys.exit(1)
    
    # Save token to keychain
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-s", KEYCHAIN_SERVICE,
                "-a", KEYCHAIN_ACCOUNT,
                "-w", token
            ],
            check=True
        )
        print("Token saved to keychain")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to save token to keychain: {e}")
    
    return token

def get_latest_git_tag() -> Optional[str]:
    """Get the latest semver tag from git"""
    try:
        # Fetch all tags
        subprocess.run(['git', 'fetch', '--tags'], check=True, capture_output=True)
        
        # Get all tags and sort them by version number
        result = subprocess.run(
            ['git', 'tag', '--list', 'v*'], 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        tags = result.stdout.strip().split('\n')
        version_tags = []
        
        for tag in tags:
            # Only consider tags that match semantic versioning pattern
            if re.match(r'^v?\d+\.\d+\.\d+$', tag):
                version_tags.append(tag)
        
        if not version_tags:
            return None
            
        # Sort tags by version number
        version_tags.sort(key=lambda x: Version.from_string(x))
        return version_tags[-1]
    
    except subprocess.CalledProcessError as e:
        print(f"Error getting git tags: {e}")
        return None

def get_current_version():
    """Get current version from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        for line in f:
            if line.startswith("version"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return None

def create_release(token, version, prerelease=False, draft=False):
    """Create a new GitHub release"""
    # Get repo from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        for line in f:
            if line.startswith("repository"):
                repo_url = line.split("=")[1].strip().strip('"').strip("'")
                # Extract owner and repo from URL
                parts = repo_url.split("/")
                owner, repo = parts[-2], parts[-1]
                break
        else:
            print("Error: Could not find repository in pyproject.toml")
            sys.exit(1)

    # Prepare release data
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",  # Changed back to 'token'
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "tag_name": f"v{version}",
        "target_commitish": "main",
        "name": f"{version}",
        "body": f"Release version: {version}",
        "draft": draft,
        "prerelease": prerelease
    }

    print(f"\nCreating release at: {url}")
    
    # Create release
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        print(f"Successfully released version {version}")
        print(f"Release URL: {response.json()['html_url']}")
    else:
        print(f"Error creating release: {response.status_code}")
        print(response.json())
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Create a new GitHub release")
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument("--version", help="Specific version to release")
    version_group.add_argument("--major", "--breaking", action="store_true", help="Bump major version (breaking changes)")
    version_group.add_argument("--minor", action="store_true", help="Bump minor version (new features, default)")
    version_group.add_argument("--patch", "--hotfix", action="store_true", help="Bump patch version (bug fixes)")
    
    parser.add_argument("--prerelease", action="store_true", help="Mark as prerelease")
    parser.add_argument("--draft", action="store_true", help="Create as draft")
    
    args = parser.parse_args()

    # Get token from keychain
    token = get_github_token()

    # Get latest git tag
    latest_tag = get_latest_git_tag()
    if latest_tag:
        current_version = Version.from_string(latest_tag)
        print(f"Latest git tag: {latest_tag}")
    else:
        current_version = Version.from_string(get_current_version() or "0.0.0")
        print(f"No git tags found, using version from pyproject.toml: {current_version}")

    # Determine new version
    if args.version:
        try:
            new_version = Version.from_string(args.version)
        except ValueError:
            print(f"Error: Invalid version format: {args.version}")
            sys.exit(1)
    elif args.major:
        new_version = current_version.bump_major()
    elif args.patch:
        new_version = current_version.bump_patch()
    else:  # Default to minor bump
        new_version = current_version.bump_minor()

    # Confirm with user
    print(f"\nAbout to release version: {new_version}")
    print(f"Previous version: {current_version}")
    if args.prerelease:
        print("This will be marked as a prerelease")
    if args.draft:
        print("This will be created as a draft")
    
    response = input("\nContinue? [y/N] ")
    if response.lower() != 'y':
        print("Aborted")
        sys.exit(0)

    create_release(token, str(new_version), args.prerelease, args.draft)

if __name__ == "__main__":
    main()
