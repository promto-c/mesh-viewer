import fnmatch
import os
from pathlib import Path

def read_gitignore(root_path):
    ignore_patterns = []
    gitignore_path = root_path / '.gitignore'
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as file:
            ignore_patterns = file.read().splitlines()
    return ignore_patterns

def should_ignore(path, ignore_patterns):
    # Check if the path is the .git directory or matches any ignore pattern
    if path.name == '.git' or any(fnmatch.fnmatch(str(path), pattern) or fnmatch.fnmatch(os.path.basename(path), pattern) for pattern in ignore_patterns):
        return True
    return False

def print_repo_structure(root_path, ignore_patterns, only_dirs=False, prefix=''):
    root_path = Path(root_path)
    entries = sorted(root_path.iterdir(), key=lambda x: (x.is_file(), x.name))
    for index, entry in enumerate(entries):
        if should_ignore(entry, ignore_patterns):
            continue

        if entry.is_dir() or not only_dirs:  # Print if it's a directory or if we're listing all files
            connector = '├──' if index < len(entries) - 1 else '└──'
            print(f"{prefix}{connector} {entry.name}")
            if entry.is_dir():
                extension = '│   ' if index < len(entries) - 1 else '    '
                print_repo_structure(entry, ignore_patterns, only_dirs, prefix=prefix + extension)

def main(repo_path, only_dirs=False):
    root_path = Path(repo_path).resolve()
    ignore_patterns = read_gitignore(root_path)
    print(f"{root_path.name}/")
    print_repo_structure(root_path, ignore_patterns, only_dirs)

if __name__ == '__main__':
    repo_path = ''  # Specify the path to your repository here
    only_dirs = False  # Set to True to list only directories
    main(repo_path, only_dirs)
