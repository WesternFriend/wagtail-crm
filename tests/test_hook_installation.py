import shlex
import subprocess
from types import SimpleNamespace

import pytest

from scripts import install_hooks


@pytest.fixture
def installation(tmp_path, monkeypatch):
    hooks = tmp_path / "hooks with spaces"
    hooks.mkdir()
    mise = tmp_path / "mise tools" / "mise"
    mise.parent.mkdir()
    mise.write_text('#!/bin/sh\nshift 2\nexec "$@"\n')
    mise.chmod(0o755)
    prek = tmp_path / "prek"
    prek.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\ncat\nexit 7\n')
    prek.chmod(0o755)
    state = SimpleNamespace(hooks=hooks, mise=mise, invalid=False, calls=0)
    template = (
        f"#!/bin/sh\nPREK={shlex.quote(str(prek))}\n"
        'exec "$PREK" hook-impl --hook-type=pre-push -- "$@"\n'
    )

    def run(command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(stdout=f"{state.hooks}\n")
        assert command == ["prek", "install"]
        state.calls += 1
        for name in ("pre-commit", "pre-push"):
            path = hooks / name
            path.write_text("unexpected template\n" if state.invalid else template)
            path.chmod(0o755)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(install_hooks.shutil, "which", lambda _: str(mise))
    monkeypatch.setattr(install_hooks.subprocess, "run", run)
    return state


def test_reinstallation_is_repeatable_and_preserves_executable_modes(installation):
    install_hooks.main()
    first = (installation.hooks / "pre-push").read_text()
    install_hooks.main()
    assert (installation.hooks / "pre-push").read_text() == first
    for name in ("pre-commit", "pre-push"):
        assert (installation.hooks / name).stat().st_mode & 0o111


def test_gui_hook_preserves_quoted_arguments_stdin_and_failure_status(installation):
    install_hooks.main()
    # Execute the generated shell with real processes, independent of the stub
    # used for Git discovery and prek installation in the fixture.
    with subprocess.Popen(  # noqa: S603
        [str(installation.hooks / "pre-push"), "remote name", "url with spaces"],
        env={"PATH": "/usr/bin:/bin"},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    ) as process:
        output, _ = process.communicate("refs/heads/example synthetic-ref\n")
    assert process.returncode == 7
    assert output.splitlines() == [
        "hook-impl",
        "--hook-type=pre-push",
        "--",
        "remote name",
        "url with spaces",
        "refs/heads/example synthetic-ref",
    ]


@pytest.mark.parametrize("existing", [False, True])
def test_unexpected_template_restores_previous_hooks(installation, existing):
    paths = [installation.hooks / name for name in ("pre-commit", "pre-push")]
    if existing:
        for path in paths:
            path.write_text("previous hook\n")
            path.chmod(0o750)
    installation.invalid = True
    with pytest.raises(SystemExit, match="Unexpected prek shim format"):
        install_hooks.main()
    for path in paths:
        if existing:
            assert path.read_text() == "previous hook\n"
            assert path.stat().st_mode & 0o777 == 0o750
        else:
            assert not path.exists()


def test_whitespace_hook_path_is_rejected_before_installation(installation):
    installation.hooks = installation.hooks.parent / "hooks "
    with pytest.raises(SystemExit, match="whitespace"):
        install_hooks.main()
    assert installation.calls == 0
