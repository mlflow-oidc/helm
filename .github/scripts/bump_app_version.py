"""Move a chart's appVersion to a new mlflow-oidc-auth release and bump the chart version to match.

The chart version moves by the same kind of step as the plugin: a new plugin major is a new chart
major (it may need chart changes, and the pull request says so), a minor is a minor, a patch is a
patch. Comments and the README that name the current default tag are updated too, and the
Artifact Hub changes annotation is replaced with one entry for this bump.

Usage: bump_app_version.py <chart-dir> <new-app-version>
Prints the new chart version.
"""

import re
import sys
from pathlib import Path

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse(version: str) -> tuple[int, int, int]:
    match = SEMVER.match(version)
    if not match:
        raise SystemExit(f"not a plain semantic version: {version!r}")
    return tuple(int(part) for part in match.groups())


def next_chart_version(chart: tuple[int, int, int], old_app: tuple[int, int, int], new_app: tuple[int, int, int]) -> str:
    if new_app <= old_app:
        raise SystemExit(f"{'.'.join(map(str, new_app))} is not newer than {'.'.join(map(str, old_app))}")
    major, minor, patch = chart
    if new_app[0] > old_app[0]:
        return f"{major + 1}.0.0"
    if new_app[1] > old_app[1]:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main(chart_dir: str, new_app: str) -> None:
    root = Path(chart_dir)
    chart_file = root / "Chart.yaml"
    text = chart_file.read_text()
    old_app = re.search(r'^appVersion:\s*"?([^"\n]+)"?\s*$', text, re.M).group(1)
    chart_version = re.search(r"^version:\s*(\S+)\s*$", text, re.M).group(1)
    new_chart = next_chart_version(parse(chart_version), parse(old_app), parse(new_app))

    text = re.sub(r"^version:.*$", f"version: {new_chart}", text, count=1, flags=re.M)
    text = re.sub(r"^appVersion:.*$", f'appVersion: "{new_app}"', text, count=1, flags=re.M)
    changes = (
        "annotations:\n"
        "  artifacthub.io/changes: |\n"
        "    - kind: changed\n"
        f"      description: Default to mlflow-oidc-auth {new_app} (image tag {new_app})\n"
    )
    if re.search(r"^annotations:", text, re.M):
        text = re.sub(r"^annotations:\n(?:[ ]{2,}.*\n?)*", changes, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + changes
    chart_file.write_text(text)

    # Mentions of the default tag in comments and docs; example tags in tables are left alone.
    old = re.escape(old_app)
    for name in ("values.yaml", "README.md"):
        path = root / name
        if not path.exists():
            continue
        body = path.read_text()
        body = re.sub(rf"(currently `?){old}(`?)", rf"\g<1>{new_app}\g<2>", body)
        body = re.sub(rf"(appVersion \(){old}(\))", rf"\g<1>{new_app}\g<2>", body)
        body = re.sub(rf'(tag: "){old}(")', rf"\g<1>{new_app}\g<2>", body)
        path.write_text(body)

    print(new_chart)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
