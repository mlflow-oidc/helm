"""Image tags of ghcr.io/mlflow-oidc/mlflow-tracking-server and the chart that defaults to one.

Every image build is published as ``<mlflow>-<plugin>-<YYYYMMDD>`` (immutable) besides the moving
``<plugin>`` and ``latest``. The chart's ``image.tag`` default is always an immutable build whose
plugin part equals ``appVersion``.

Usage:
  image_tags.py check <chart-dir>
      Fail unless the chart's default image.tag is an immutable build of its appVersion.
  image_tags.py newest <current-tag> < tags.txt
      Print the newest immutable build newer than <current-tag> (by plugin, then build date, then
      MLflow), or nothing.
  image_tags.py bump <chart-dir> <tag>
      Move the chart to <tag>: image.tag, appVersion and the chart version (a new plugin major,
      minor or patch bumps the chart the same way; a new build of the same plugin is a chart patch),
      the README and comments naming the release, and the Artifact Hub changes annotation.
      Prints the new chart version.
"""

import re
import sys
from pathlib import Path

BUILD = re.compile(r"^(\d+\.\d+\.\d+)-(\d+\.\d+\.\d+)-(\d{8})$")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def semver(version: str) -> tuple[int, int, int]:
    match = SEMVER.match(version)
    if not match:
        raise SystemExit(f"not a plain semantic version: {version!r}")
    return tuple(int(part) for part in match.groups())


def build(tag: str):
    """``(plugin, date, mlflow)`` for an immutable build tag, ordered newest-last; None otherwise."""
    match = BUILD.match(tag.strip())
    if not match:
        return None
    mlflow, plugin, date = match.groups()
    return semver(plugin), date, semver(mlflow)


def chart_fields(root: Path) -> tuple[str, str, str]:
    chart = (root / "Chart.yaml").read_text()
    values = (root / "values.yaml").read_text()
    version = re.search(r"^version:\s*(\S+)\s*$", chart, re.M).group(1)
    app = re.search(r'^appVersion:\s*"?([^"\n]+)"?\s*$', chart, re.M).group(1)
    tag = re.search(r'^image:\n(?:[ ]{2}.*\n)*?[ ]{2}tag:\s*"?([^"\n]*)"?\s*$', values, re.M)
    return version, app, tag.group(1) if tag else ""


def check(chart_dir: str) -> None:
    _, app, tag = chart_fields(Path(chart_dir))
    parsed = build(tag)
    if parsed is None:
        raise SystemExit(f"::error title=Mutable default image tag::image.tag is {tag!r}; it must be an immutable build <mlflow>-<plugin>-<YYYYMMDD>")
    if parsed[0] != semver(app):
        raise SystemExit(f"::error title=Image tag does not match appVersion::image.tag {tag} is a build of plugin {'.'.join(map(str, parsed[0]))}, appVersion is {app}")
    print(f"image.tag {tag} is an immutable build of appVersion {app}")


def newest(current: str) -> None:
    current_build = build(current)
    builds = sorted((parsed, tag) for tag in sys.stdin.read().split() if (parsed := build(tag)))
    if builds and (current_build is None or builds[-1][0] > current_build):
        print(builds[-1][1])


def bump(chart_dir: str, tag: str) -> None:
    root = Path(chart_dir)
    chart_version, old_app, old_tag = chart_fields(root)
    new = build(tag)
    if new is None:
        raise SystemExit(f"not an immutable build tag: {tag!r}")
    old = build(old_tag)
    if old is not None and new <= old:
        raise SystemExit(f"{tag} is not newer than {old_tag}")
    new_app = ".".join(map(str, new[0]))
    old_plugin, new_plugin = semver(old_app), new[0]
    if new_plugin < old_plugin:
        raise SystemExit(f"plugin {new_app} is older than appVersion {old_app}")
    major, minor, patch = semver(chart_version)
    if new_plugin[0] > old_plugin[0]:
        new_chart = f"{major + 1}.0.0"
    elif new_plugin[1] > old_plugin[1]:
        new_chart = f"{major}.{minor + 1}.0"
    else:
        new_chart = f"{major}.{minor}.{patch + 1}"

    chart_file = root / "Chart.yaml"
    text = chart_file.read_text()
    text = re.sub(r"^version:.*$", f"version: {new_chart}", text, count=1, flags=re.M)
    text = re.sub(r"^appVersion:.*$", f'appVersion: "{new_app}"', text, count=1, flags=re.M)
    what = f"mlflow-oidc-auth {new_app}" if new_plugin != old_plugin else f"a new build of mlflow-oidc-auth {new_app}"
    changes = f"annotations:\n  artifacthub.io/changes: |\n    - kind: changed\n      description: Default to {what}, image {tag}\n"
    if re.search(r"^annotations:", text, re.M):
        text = re.sub(r"^annotations:\n(?:[ ]{2,}.*\n?)*", changes, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + changes
    chart_file.write_text(text)

    values_file = root / "values.yaml"
    values = values_file.read_text()
    values = re.sub(r'^(image:\n(?:[ ]{2}.*\n)*?[ ]{2}tag:\s*).*$', rf'\g<1>"{tag}"', values, count=1, flags=re.M)
    values_file.write_text(values)

    # The README names the targeted release; example tags in its tables are left alone.
    readme = root / "README.md"
    if readme.exists() and new_plugin != old_plugin:
        readme.write_text(re.sub(rf"(currently `?){re.escape(old_app)}(`?)", rf"\g<1>{new_app}\g<2>", readme.read_text()))

    print(new_chart)


if __name__ == "__main__":
    command, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if command == "check" and len(args) == 1:
        check(*args)
    elif command == "newest" and len(args) == 1:
        newest(*args)
    elif command == "bump" and len(args) == 2:
        bump(*args)
    else:
        raise SystemExit(__doc__)
