#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


@dataclass(order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def from_string(cls, version_str: str) -> "Version":
        # Remove 'v' prefix if present
        version_str = version_str.lstrip("v")
        try:
            major, minor, patch = map(int, version_str.split("."))
            return cls(major=major, minor=minor, patch=patch)
        except ValueError as e:
            raise ValueError(f"Invalid version string: {version_str}") from e

    def bump_major(self) -> "Version":
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> "Version":
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "Version":
        return Version(self.major, self.minor, self.patch + 1)

    def to_int(self) -> int:
        return self.major * 1_000_000_000 + self.minor * 1_000_000 + self.patch

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
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting token from keychain: {e}")

    token = input("Enter your GitHub token: ").strip()

    if not token:

        sys.exit(1)

    # Save token to keychain
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
                token,
            ],
            check=True,
        )

    except subprocess.CalledProcessError as e:
        print(f"Error saving token to keychain: {e}")
    return token


def get_latest_git_tag() -> Optional[str]:
    """Get the latest semver tag from git"""
    try:
        # Fetch all tags
        subprocess.run(["git", "fetch", "--tags"], check=True, capture_output=True)

        # Get all tags and sort them by version number
        result = subprocess.run(
            ["git", "tag", "--list", "v*"], check=True, capture_output=True, text=True
        )

        tags = result.stdout.strip().split("\n")
        version_tags = []

        for tag in tags:
            # Only consider tags that match semantic versioning pattern
            if re.match(r"^v?\d+\.\d+\.\d+$", tag):
                version_tags.append(tag)

        if not version_tags:
            return None

        # Sort tags by version number
        def version_key(version: str):
            return Version.from_string(version).to_int()

        version_tags.sort(key=version_key)
        return version_tags[-1]

    except subprocess.CalledProcessError as e:
        print(f"Error getting latest git tag: {e}")
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

            sys.exit(1)

    # Prepare release data
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",  # Changed back to 'token'
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "tag_name": f"v{version}",
        "target_commitish": "main",
        "name": f"{version}",
        "body": f"Release version: {version}",
        "draft": draft,
        "prerelease": prerelease,
    }

    # Create release
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        print(f"Release created: {response.json()['html_url']}")
    else:
        print(f"Error creating release: {response.text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create a new GitHub release")
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument("--version", help="Specific version to release")
    version_group.add_argument(
        "--major",
        "--breaking",
        action="store_true",
        help="Bump major version (breaking changes)",
    )
    version_group.add_argument(
        "--minor",
        action="store_true",
        help="Bump minor version (new features, default)",
    )
    version_group.add_argument(
        "--patch",
        "--hotfix",
        action="store_true",
        help="Bump patch version (bug fixes)",
    )

    parser.add_argument("--prerelease", action="store_true", help="Mark as prerelease")
    parser.add_argument("--draft", action="store_true", help="Create as draft")

    args = parser.parse_args()

    # Get token from keychain
    token = get_github_token()

    # Get latest git tag
    latest_tag = get_latest_git_tag()
    if latest_tag:
        current_version = Version.from_string(latest_tag)

    else:
        current_version = Version.from_string(get_current_version() or "0.0.0")

    # Determine new version
    if args.version:
        try:
            new_version = Version.from_string(args.version)
        except ValueError:

            sys.exit(1)
    elif args.major:
        new_version = current_version.bump_major()
    elif args.patch:
        new_version = current_version.bump_patch()
    else:  # Default to minor bump
        new_version = current_version.bump_minor()

    if args.prerelease:
        print(f"Creating prerelease for version: {new_version}")

    if args.draft:
        print(f"Creating draft release for version: {new_version}")

    response = input("\nContinue? [y/N] ")
    if response.lower() != "y":

        sys.exit(0)

    create_release(token, str(new_version), args.prerelease, args.draft)


if __name__ == "__main__":
    main()
