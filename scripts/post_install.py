#!/usr/bin/env python3
import matplotlib.font_manager

def main():
    print("Building font cache for matplotlib...")
    matplotlib.font_manager._load_fontmanager(try_read_cache=False)
    print("Font cache built successfully!")

if __name__ == "__main__":
    main() 