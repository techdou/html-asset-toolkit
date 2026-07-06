#!/usr/bin/env python3
"""Build a React/Vue/static frontend project and package its build entry as single-file HTML.

This wrapper is intentionally deterministic: agents can run one command instead of
remembering the build -> locate entry -> inline -> validate sequence.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
INLINE_SCRIPT = SCRIPT_DIR / "inline_assets.py"
VALIDATE_SCRIPT = SCRIPT_DIR / "validate_single_html.py"
ESTIMATE_SCRIPT = SCRIPT_DIR / "estimate_size.py"

# public/index.html is deliberately excluded here. In React/Vue/Vite projects,
# public/index.html is commonly a source template or static source file, not the
# production build artifact. Users can still package it explicitly with --entry.
DEFAULT_ENTRY_CANDIDATES = (
    "dist/index.html",
    "build/index.html",
    "out/index.html",
)


def printable_cmd(cmd: list[str] | str) -> str:
    return cmd if isinstance(cmd, str) else " ".join(shlex.quote(str(part)) for part in cmd)


def run_command(cmd: list[str] | str, cwd: Path, dry_run: bool = False) -> subprocess.CompletedProcess[str] | None:
    print(f"$ {printable_cmd(cmd)}")
    if dry_run:
        return None
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=isinstance(cmd, str),
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed


def capture_command(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    print(f"$ {printable_cmd(cmd)}")
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed


def detect_package_manager(project_dir: Path) -> str:
    if (project_dir / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (project_dir / "yarn.lock").exists():
        return "yarn"
    if (project_dir / "bun.lockb").exists() or (project_dir / "bun.lock").exists():
        return "bun"
    return "npm"


def default_build_command(manager: str) -> list[str]:
    if manager == "pnpm":
        return ["pnpm", "run", "build"]
    if manager == "yarn":
        return ["yarn", "build"]
    if manager == "bun":
        return ["bun", "run", "build"]
    return ["npm", "run", "build"]


def resolve_project_path(project_dir: Path, value: str | None) -> Path | None:
    """Resolve wrapper-facing paths relative to the frontend project root.

    This is intentionally different from inline_assets.py, whose relative
    --root-dir and --assets-root values resolve beside the input HTML. A user
    running this wrapper from a React/Vue root naturally expects --root-dir dist
    to mean <project>/dist, not <project>/dist/dist.
    """
    if not value:
        return None
    p = Path(value)
    return (p if p.is_absolute() else project_dir / p).resolve()


def resolve_entry(project_dir: Path, entry: str | None) -> Path:
    if entry:
        candidate = resolve_project_path(project_dir, entry)
        assert candidate is not None
        if candidate.exists() and candidate.is_file():
            if candidate.parts and candidate.parent.name.lower() == "public":
                print(
                    "WARNING: packaging public/index.html explicitly. In React/Vue/Vite projects, "
                    "public/index.html is usually not a production build artifact. Prefer dist/index.html, build/index.html, or out/index.html after npm run build.",
                    file=sys.stderr,
                )
            return candidate.resolve()
        raise SystemExit(f"ERROR: build HTML entry not found: {candidate}")

    for rel in DEFAULT_ENTRY_CANDIDATES:
        candidate = project_dir / rel
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    searched = ", ".join(DEFAULT_ENTRY_CANDIDATES)
    raise SystemExit(
        "ERROR: could not find a production build HTML entry. "
        f"Looked for: {searched}. Run your build first, or use --entry path/to/index.html if your build output is custom. "
        "public/index.html is not auto-selected because it is often a source template."
    )


def infer_preset(entry: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    parent = entry.parent.name.lower()
    if parent == "build":
        return "create-react-app"
    if parent in {"dist", "out"}:
        return "react-vue-build"
    if parent == "public":
        return "generic"
    return "react-vue-build"


def infer_output(entry: Path, out: str | None) -> Path:
    if out:
        p = Path(out)
        if not p.is_absolute():
            p = entry.parent / p
        return p.resolve()
    if entry.name.lower() == "index.html" and entry.parent.name.lower() in {"dist", "build", "out"}:
        return (entry.parent / "index.single.html").resolve()
    return (entry.parent / "dist" / f"{entry.stem}.single{entry.suffix}").resolve()


def add_optional_number(args: list[str], flag: str, value: float | int) -> None:
    if value and value > 0:
        args.extend([flag, str(value)])


def parse_validation_report(stdout: str) -> dict[str, Any] | None:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a frontend build and package dist/index.html, build/index.html, or out/index.html as a single-file HTML artifact."
    )
    parser.add_argument("project_dir", nargs="?", default=".", type=Path, help="React/Vue/Vite/CRA project directory. Default: current directory.")
    parser.add_argument("--entry", default=None, help="Built HTML entry. Defaults to dist/index.html, build/index.html, then out/index.html. public/index.html is only used when explicitly provided.")
    parser.add_argument("--skip-build", action="store_true", help="Do not run the package build command; use an existing build directory.")
    parser.add_argument("--package-manager", choices=["auto", "npm", "pnpm", "yarn", "bun"], default="auto")
    parser.add_argument("--build-command", default=None, help="Custom build command string, e.g. 'npm run build'.")
    parser.add_argument("--preset", choices=["auto", "react-vue-build", "vite", "vue-cli", "create-react-app", "generic"], default="auto")
    parser.add_argument("--out", default=None, help="Output HTML path. Relative paths resolve beside the build entry.")
    parser.add_argument("--root-dir", default=None, help="Static root for /assets/... URLs. Relative paths resolve from project_dir. Defaults to the build entry directory.")
    parser.add_argument("--assets-root", default=None, help="Additional asset lookup root. Relative paths resolve from project_dir.")
    parser.add_argument("--include-ext", default=None)
    parser.add_argument("--exclude-ext", default=None)
    parser.add_argument("--max-asset-mb", type=float, default=0)
    parser.add_argument("--max-total-mb", type=float, default=0)
    parser.add_argument("--image-mode", choices=["raw", "webp"], default="raw")
    parser.add_argument("--max-width", type=int, default=1800)
    parser.add_argument("--max-height", type=int, default=1800)
    parser.add_argument("--webp-quality", type=int, default=82)
    parser.add_argument("--css-js-mode", choices=["data-url", "tag"], default="data-url", help="How to embed CSS/JS: data-url (default) or tag (inline <style>/<script> blocks).")
    parser.add_argument("--estimate", action="store_true", help="Run estimate_size.py first. If the projected embedded total exceeds --max-total-mb, abort before packaging.")
    parser.add_argument("--no-validate", action="store_true", help="Skip validate_single_html.py after packaging.")
    parser.add_argument("--strict", action="store_true", help="Strict mode: missing/oversized assets fail inlining and validation warnings fail the command.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Fail when validate_single_html.py reports warnings. Also enabled by --strict.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        print(f"ERROR: project directory not found: {project_dir}", file=sys.stderr)
        return 1

    if not args.skip_build:
        if args.build_command:
            build_cmd: list[str] | str = args.build_command
        else:
            manager = detect_package_manager(project_dir) if args.package_manager == "auto" else args.package_manager
            build_cmd = default_build_command(manager)
        run_command(build_cmd, cwd=project_dir, dry_run=args.dry_run)

    entry = resolve_entry(project_dir, args.entry)
    preset = infer_preset(entry, args.preset)
    output = infer_output(entry, args.out)
    root_dir = resolve_project_path(project_dir, args.root_dir)
    assets_root = resolve_project_path(project_dir, args.assets_root)

    # Optional pre-packaging estimate. Aborts if the projected size exceeds
    # --max-total-mb so agents/users can decide before a heavy run.
    estimated_report: dict[str, Any] | None = None
    if args.estimate:
        est_cmd = [sys.executable, str(ESTIMATE_SCRIPT), str(entry), "--json"]
        if root_dir:
            est_cmd.extend(["--root-dir", str(root_dir)])
        if assets_root:
            est_cmd.extend(["--assets-root", str(assets_root)])
        if args.include_ext:
            est_cmd.extend(["--include-ext", args.include_ext])
        if args.exclude_ext:
            est_cmd.extend(["--exclude-ext", args.exclude_ext])
        if args.max_asset_mb:
            est_cmd.extend(["--max-asset-mb", str(args.max_asset_mb)])
        est_completed = capture_command(est_cmd, cwd=project_dir)
        estimated_report = parse_validation_report(est_completed.stdout or "")
        if estimated_report:
            projected = estimated_report.get("estimated_final_html_bytes", 0)
            if args.max_total_mb and projected > args.max_total_mb * 1024 * 1024:
                print(
                    f"ERROR: estimated final HTML {projected} bytes exceeds "
                    f"--max-total-mb {args.max_total_mb} MB. Aborting before packaging.",
                    file=sys.stderr,
                )
                return 1

    inline_cmd = [sys.executable, str(INLINE_SCRIPT), str(entry), "--preset", preset, "--out", str(output)]
    if root_dir:
        inline_cmd.extend(["--root-dir", str(root_dir)])
    if assets_root:
        inline_cmd.extend(["--assets-root", str(assets_root)])
    if args.include_ext:
        inline_cmd.extend(["--include-ext", args.include_ext])
    if args.exclude_ext:
        inline_cmd.extend(["--exclude-ext", args.exclude_ext])
    add_optional_number(inline_cmd, "--max-asset-mb", args.max_asset_mb)
    add_optional_number(inline_cmd, "--max-total-mb", args.max_total_mb)
    inline_cmd.extend([
        "--image-mode", args.image_mode,
        "--max-width", str(args.max_width),
        "--max-height", str(args.max_height),
        "--webp-quality", str(args.webp_quality),
        "--css-js-mode", args.css_js_mode,
    ])
    if args.strict:
        inline_cmd.append("--strict")
    if args.dry_run:
        inline_cmd.append("--dry-run")

    run_command(inline_cmd, cwd=project_dir, dry_run=args.dry_run)

    validation_report: dict[str, Any] | None = None
    validation_warnings: list[str] = []
    if not args.no_validate and not args.dry_run:
        validate_cmd = [sys.executable, str(VALIDATE_SCRIPT), str(output), "--json"]
        if args.strict or args.fail_on_warning:
            validate_cmd.append("--fail-on-warning")
        completed = capture_command(validate_cmd, cwd=project_dir)
        validation_report = parse_validation_report(completed.stdout or "")
        if validation_report:
            validation_warnings = list(validation_report.get("warnings") or [])
            if validation_warnings:
                print("Validation warnings detected:")
                for warning in validation_warnings:
                    print(f"  - {warning}")
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)

    summary = {
        "project_dir": str(project_dir),
        "entry": str(entry),
        "preset": preset,
        "output": str(output),
        "root_dir": str(root_dir) if root_dir else str(entry.parent),
        "assets_root": str(assets_root) if assets_root else None,
        "validated": not args.no_validate and not args.dry_run,
        "validation_warning_count": len(validation_warnings),
        "validation_warnings": validation_warnings,
    }
    if estimated_report:
        summary["estimated"] = {
            "estimated_final_html_bytes": estimated_report.get("estimated_final_html_bytes"),
            "estimated_total_embedded_bytes": estimated_report.get("estimated_total_embedded_bytes"),
            "missing_count": len(estimated_report.get("missing", [])),
        }
    if validation_report:
        summary["validation"] = {
            "html_size": validation_report.get("html_size"),
            "data_url_count": validation_report.get("data_url_count"),
            "decoded_size_total": validation_report.get("decoded_size_total"),
            "remaining_refs": validation_report.get("remaining_refs"),
            "decoded_text_remaining_refs": validation_report.get("decoded_text_remaining_refs"),
        }
    print("Package summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
