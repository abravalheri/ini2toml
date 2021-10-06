from itertools import chain
from pathlib import Path

from cfg2toml import toml_adapter
from cfg2toml.cli import guess_profile
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


def test_examples():
    translator = Translator()
    available_profiles = list(translator.profiles.keys())
    for orig, expected in examples():
        print(f"---------------------------- {orig} ----------------------------")
        profile = guess_profile(None, str(orig), available_profiles)
        out = translator.translate(orig.read_text(), profile)
        expected_text = expected.read_text().strip()
        assert out == expected_text
        # Make sure they can be parsed
        assert toml_adapter.loads(out) == toml_adapter.loads(expected_text)
