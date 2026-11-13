"""Integration smoke test using the downloaded official HPO dataset."""
from streamlit.testing.v1 import AppTest

def test_streamlit_app_loads():
    app = AppTest.from_file("app.py", default_timeout=120).run()
    assert not app.exception, [str(x.message) for x in app.exception]
    assert any("Patient observations" in str(x.value) for x in app.subheader)
