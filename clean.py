import shutil
import os

def clean():
    """Clean up build artifacts"""
    dirs_to_clean = ['build', 'dist']
    files_to_clean = [f for f in os.listdir('.') if f.endswith('.egg-info')]
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Removing {d}/")
            shutil.rmtree(d)
    
    for f in files_to_clean:
        if os.path.exists(f):
            print(f"Removing {f}")
            os.remove(f)

if __name__ == "__main__":
    clean() 