import sys
from itertools import chain
from pathlib import Path

from cfg2toml import cli, toml_adapter
from cfg2toml.translator import Translator


def examples():
    parent = Path(__file__).parent / "examples"
    for folder in parent.glob("*/"):
        cfg = chain(folder.glob("*.cfg"), folder.glob("*.ini"))
        toml = folder.glob("*.toml")
        for orig in cfg:
            expected = orig.with_suffix(".toml")
            if expected.is_file():
                yield orig, expected
            else:
                try:
                    yield orig, next(toml)
                except:  # noqa
                    print(f"Missing TOML file to compare to {orig}")
                    raise


def test_examples_api():
    translator = Translator()
    available_profiles = list(translator.profiles.keys())
    for orig, expected in examples():
        print(f"---------------------------- {orig} ----------------------------")
        profile = cli.guess_profile(None, str(orig), available_profiles)
        out = translator.translate(orig.read_text(), profile)
        expected_text = expected.read_text().strip()
        assert out == expected_text
        # Make sure they can be parsed
        assert toml_adapter.loads(out) == toml_adapter.loads(expected_text)


def test_examples_cli(capsys):
    for orig, expected in examples():
        print(f"---------------------- {orig} ----------------------", file=sys.stderr)
        cli.run([str(orig)])
        (out, err) = capsys.readouterr()
        expected_text = expected.read_text().strip()
        assert out == expected_text
        # Make sure they can be parsed
        assert toml_adapter.loads(out) == toml_adapter.loads(expected_text)
