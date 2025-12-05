# update_changelog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import datetime
import sys
import os

def update_changelog(version):
    changelog_path = "CHANGELOG.md"
    
    if not os.path.exists(changelog_path):
        print("CHANGELOG.md not found!")
        return

    with open(changelog_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check if version already exists
    header = f"## [{version}]"
    for line in lines:
        if header in line:
            print(f"Version {version} already exists in CHANGELOG.md")
            return

    today = datetime.date.today().isoformat()
    new_entry = f"""
## [{version}] - {today}
### Added
- Automatic release via GitHub Actions.

"""
    
    # Find insertion point (after the first header or at top)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("## ["):
            insert_idx = i
            break
    
    # If no existing versions found, append after main title if exists
    if insert_idx == 0 and len(lines) > 5:
        for i, line in enumerate(lines):
            if line.startswith("# Changelog"):
                insert_idx = i + 4 # Skip header text
                break

    lines.insert(insert_idx, new_entry)

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print(f"Updated CHANGELOG.md for version {version}")

if __name__ == "__main__":
    target_version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    update_changelog(target_version)
