"""Install prek shims that load mise tools even when Git is launched by a GUI."""

import shlex
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    mise = shutil.which("mise")
    if mise is None:
        message = "Run this installer with `mise run hooks-install`."
        raise SystemExit(message)

    # These fixed commands run in the trusted project environment provided by mise.
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    hooks_dir = Path(result.stdout.rstrip("\n"))
    # prek 0.4.8 trims effective hook paths. Reject that mismatch before it
    # installs a shim somewhere Git will not look.
    if any(part != part.strip() for part in hooks_dir.parts):
        message = "Hook directory components cannot start or end with whitespace."
        raise SystemExit(message)
    original = 'exec "$PREK" hook-impl '
    replacement = (
        f'exec {shlex.quote(str(Path(mise).absolute()))} exec -- "$PREK" hook-impl '
    )

    paths = [hooks_dir / name for name in ("pre-commit", "pre-push")]
    previous = {
        path: (path.read_bytes(), path.stat().st_mode) if path.exists() else None
        for path in paths
    }
    try:
        subprocess.run(["prek", "install"], check=True)  # noqa: S607
        updates = []
        for path in paths:
            content = path.read_text()
            if content.count(original) != 1:
                message = f"Unexpected prek shim format in {path}; previous hooks were restored."
                raise SystemExit(message)  # noqa: TRY301 - restore hooks on invalid templates
            updates.append((path, content.replace(original, replacement, 1)))

        for path, content in updates:
            # Writing preserves the executable mode set by prek. Its arguments
            # and stdin remain untouched, including Git's pre-push ref input.
            path.write_text(content)
    except (OSError, subprocess.CalledProcessError, SystemExit):
        for path, saved in previous.items():
            if saved is None:
                path.unlink(missing_ok=True)
            else:
                content, mode = saved
                path.write_bytes(content)
                path.chmod(mode)
        raise


if __name__ == "__main__":
    main()
