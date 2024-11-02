from setuptools import setup

APP = ['github_watcher/main.py']
DATA_FILES = [
    ('', ['github_watcher/gh_notify.app/Contents/Resources/applet.icns']),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'github_watcher/gh_notify.app/Contents/Resources/applet.icns',
    'plist': {
        'CFBundleName': 'GitHub PR Watcher',
        'CFBundleDisplayName': 'GitHub PR Watcher',
        'CFBundleIdentifier': 'com.github.pr-watcher',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.10',
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 