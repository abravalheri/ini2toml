import logging
import sys
from inspect import cleandoc
from unittest.mock import MagicMock

import pytest

from ini2toml import cli
from ini2toml.plugins import ErrorLoadingPlugin
from ini2toml.profile import Profile, ProfileAugmentation


def test_guess_profile(caplog):
    available = ["best_effort", "setup.cfg", "mypy.ini", "pyscaffold/default.cfg"]
    with caplog.at_level(logging.DEBUG):
        assert cli.guess_profile("best_effort", "setup.cfg", available) == "best_effort"
        assert caplog.text == ""
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        assert cli.guess_profile(None, "myproj/setup.cfg", available) == "setup.cfg"
        assert "Profile not explicitly set" in caplog.text
        assert "'setup.cfg' inferred" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        profile = cli.guess_profile(None, "~/.config/pyscaffold/default.cfg", available)
        assert profile == "pyscaffold/default.cfg"
        assert "Profile not explicitly set" in caplog.text
        assert "'pyscaffold/default.cfg' inferred" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        profile = cli.guess_profile(None, "myfile.ini", available)
        assert "Profile not explicitly set" in caplog.text
        assert "using 'best_effort'" in caplog.text


def _profile(name, help_text="help_text"):
    return Profile(name, help_text)


def _aug(name, active, help_text="help_text"):
    return ProfileAugmentation(lambda x: x, active, name, help_text)


def test_parse_args(tmp_path):
    file = tmp_path / "file.ini"
    file.touch()
    args = f"{file} -p setup.cfg -D hello world -E ehllo owrld".split()
    profiles = [_profile(n) for n in "setup.cfg default.cfg".split()]
    aug = [_aug(n, True) for n in "hello world other".split()]
    aug += [_aug(n, False) for n in "ehllo owrld".split()]
    params = cli.parse_args(args, profiles, aug)
    assert params.profile == "setup.cfg"
    assert params.active_augmentations == {
        "hello": False,
        "world": False,
        "ehllo": True,
        "owrld": True,
    }
    assert "other" not in params.active_augmentations


def test_critical_logging_sets_log_level_on_error(monkeypatch, caplog):
    spy = MagicMock()
    monkeypatch.setattr(sys, "argv", ["-vv"])
    monkeypatch.setattr(logging, "basicConfig", spy)
    with pytest.raises(ValueError):
        with cli.critical_logging():
            raise ValueError
    _args, kwargs = spy.call_args
    assert kwargs["level"] == logging.DEBUG


def test_critical_logging_does_nothing_if_no_argv(monkeypatch, caplog):
    spy = MagicMock()
    monkeypatch.setattr(sys, "argv", [])
    monkeypatch.setattr(logging, "basicConfig", spy)
    with pytest.raises(ValueError):
        with cli.critical_logging():
            raise ValueError
    assert spy.call_args is None


def test_exceptions2exit():
    with pytest.raises(SystemExit):
        with cli.exceptions2exit():
            raise ValueError


def test_early_plugin_error(monkeypatch):
    err = MagicMock(side_effect=ErrorLoadingPlugin("fake"))
    monkeypatch.setattr("ini2toml.translator.list_all_plugins", err)

    # Remove all attached handlers, so `logging.basicConfig` can work
    for logger in (logging.getLogger(), logging.getLogger(cli.__package__)):
        monkeypatch.setattr(logger, "handlers", [])

    assert logger.getEffectiveLevel() in {logging.NOTSET, logging.WARNING}

    monkeypatch.setattr("sys.argv", ["ini2toml", "-vv"])
    with pytest.raises(SystemExit):
        cli.run()

    assert logger.getEffectiveLevel() == logging.DEBUG


def test_help(capsys):
    with pytest.raises(SystemExit):
        cli.run(["--help"])
    out, _ = capsys.readouterr()
    assert len(out) > 0
    text = " ".join(x.strip() for x in out.splitlines())
    expected_profile_desc = """\
    conversion. Available profiles:
    - 'best_effort': guess option value conversion based on the string format.
    - '.coveragerc': convert settings to 'pyproject.toml' equivalent.
    - 'setup.cfg': convert settings to 'pyproject.toml' based on :pep:`621`.
    - '.isort.cfg': convert settings to 'pyproject.toml' equivalent.
    - 'mypy.ini': convert settings to 'pyproject.toml' equivalent.
    - 'pytest.ini': convert settings to 'pyproject.toml' ('ini_options' table).
    """
    expected = " ".join(x.strip() for x in expected_profile_desc.splitlines())
    print(out)
    assert expected in text


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="pyproject-fmt is only available on Python 3.7+",
)
def test_auto_formatting(tmp_path, capsys):
    setupcfg = """
    [metadata]
    version = 42
    name = myproj
    """
    normal_output = """
    requires = ["setuptools>=61.2"]
    """
    expected = """
    requires = [
      "setuptools>=61.2",
    ]
    """

    # Check if the underlying function works
    formatted = cli.apply_auto_formatting(cleandoc(expected))
    assert formatted.strip() == cleandoc(expected).strip()

    (tmp_path / "setup.cfg").write_text(cleandoc(setupcfg), encoding="utf-8")
    assert (tmp_path / "setup.cfg").exists()

    # Check the output when formatting in off
    cli.run([str(tmp_path / "setup.cfg")])
    out, _ = capsys.readouterr()
    assert cleandoc(normal_output) in out
    assert cleandoc(expected) not in out

    # Check the output when formatting in on
    cli.run(["-F", str(tmp_path / "setup.cfg")])
    out, _ = capsys.readouterr()
    assert cleandoc(normal_output) not in out
    assert cleandoc(expected) in out
