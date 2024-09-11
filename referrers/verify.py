#!/usr/bin/env python3
"""
Verify the database, that is:

*   That every file referenced in ``referrer_metadata.js`` is saved locally, and
*   There are no files saved locally that aren't referenced in
    ``referrer_metadata.js``

"""

import os

from javascript import read_js


def get_paths_in_metadata() -> set[str]:
    """
    Return a set of paths which are referenced in ``videos_metadata.js``.
    """
    paths_in_metadata = set()

    metadata = read_js("referrer_metadata.js", varname="referrers")

    for b in metadata:
        if b.get("archive_path"):
            paths_in_metadata.add(b["archive_path"])

    return paths_in_metadata


def get_paths_saved_locally() -> set[str]:
    """
    Return a set of paths for files which are saved locally.
    """
    paths_saved_locally = set()

    for root, _, filenames in os.walk("."):
        if root.startswith(
            ("./scripts", "./.venv", "./.git", "./.ruff_cache")
        ):
            continue

        for f in filenames:
            if f == ".DS_Store":
                continue

            if root == "." and f in {
                ".gitignore",
                "index.html",
                "referrer_metadata.js",
                "README.md",
                "denim.png",
                "verify.py"
            }:
                continue

            paths_saved_locally.add(os.path.join(root.replace("./", ""), f))

    return paths_saved_locally


if __name__ == "__main__":
    paths_in_metadata = get_paths_in_metadata()
    paths_saved_locally = get_paths_saved_locally()

    if paths_in_metadata - paths_saved_locally:
        print("❌ Some files in referrer_metadata.js aren't saved locally:")

        for p in sorted(paths_in_metadata - paths_saved_locally):
            print(p)
    else:
        print("✅ Every file in referrer_metadata.js is saved locally")

    if paths_saved_locally - paths_in_metadata:
        print("❌ Some files saved locally aren't in referrer_metadata.js:")

        for p in sorted(paths_saved_locally - paths_in_metadata):
            print(p)
    else:
        print("✅ Every file saved locally is referenced in referrer_metadata.js")
