# GitHub PR Watcher

[![PyPI version](https://img.shields.io/pypi/v/github-pr-watcher?cacheSeconds=30)](https://badge.fury.io/py/github-pr-watcher)
[![Python Versions](https://img.shields.io/pypi/pyversions/github-pr-watcher.svg)](https://pypi.org/project/github-pr-watcher/)
[![License](https://img.shields.io/pypi/l/github-pr-watcher)](https://github.com/gm2211/github-watcher/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A desktop tool to monitor GitHub Pull Requests with native notifications.

The code is pretty bad, as it was mostly written by claude-sonnet 3.5.

It works though, for the most part, and I've checked it to make sure it's not doing anything crazy.

This was equally about creating a useful tool for work, as well as playing around with LLMs.

## Installation

```bash
pip install github-pr-watcher
```

If that doesn't work, try using a versioned variant like `pip3.11 install github-pr-watcher` or `pipx`.

or download the latest release from the [releases page](https://github.com/gm2211/github-watcher/releases).

## Usage

```bash
github-pr-watcher
```
or
```bash
gpw
```
or, if you have downloaded the release:
```bash
cd /path/to/github-pr-watcher && run.sh
```