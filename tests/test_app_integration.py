"""Integration smoke test using the downloaded official HPO dataset."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

@pytest.mark.skipif(not Path("data/processed/profiles.json").exists(), reason="HPO dataset not yet prepared")
def test_streamlit_app_loads():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=120).run()
    assert not app.exception, [str(x.message) for x in app.exception]
    assert any("Patient observations" in str(x.value) for x in app.subheader)
