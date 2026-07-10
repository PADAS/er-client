"""Release guard: fail unless the release tag matches erclient/version.py.

Usage: python .github/scripts/check_version_matches_tag.py <tag>
The tag may carry a leading "v" (v1.16.0 == 1.16.0).
"""
import ast
import pathlib
import sys

VERSION_FILE = pathlib.Path("erclient/version.py")


def read_package_version():
    # A release guard must fail with an actionable one-liner, not a traceback
    try:
        source = VERSION_FILE.read_text()
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"Could not read {VERSION_FILE}: {e}")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        sys.exit(f"Could not parse {VERSION_FILE}: {e}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    getattr(target, "id", None) == "__version__"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    return node.value.value
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <release-tag>")
    tag = sys.argv[1]
    version = read_package_version()
    if not version:
        sys.exit(f"Could not determine __version__ from {VERSION_FILE}")
    if tag.removeprefix("v") != version:
        sys.exit(
            f"Release tag {tag} does not match {VERSION_FILE} ({version}).\n"
            f"Bump {VERSION_FILE} before tagging the release."
        )
    print(f"Tag {tag} matches package version {version}.")


if __name__ == "__main__":
    main()
