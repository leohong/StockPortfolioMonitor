from streamlit.testing.v1 import AppTest
from src.config import ROOT


def test_streamlit_empty_database_boots(tmp_path, monkeypatch):
    from src.config import load_config
    settings, holdings, source = load_config()
    settings.database = tmp_path / "empty.duckdb"
    monkeypatch.setattr("src.ui.load_config", lambda: (settings, holdings, source))
    app = AppTest.from_file(ROOT / "app.py").run(timeout=30)
    assert not app.exception
    assert "尚無" in app.warning[0].value


def test_streamlit_real_data_and_ranges(tmp_path, real_rows, monkeypatch):
    from datetime import date
    from src.config import load_config
    from src.database.db import connect, persist
    from src.data.validator import validate
    settings, holdings, source = load_config()
    settings.database = tmp_path / "real.duckdb"
    with connect(settings.database) as db:
        persist(db, real_rows, validate(real_rows, date(2026, 8, 31)))
    monkeypatch.setattr("src.ui.load_config", lambda: (settings, holdings, source))
    def no_network(*args):
        raise AssertionError("Rendering must never fetch")
    monkeypatch.setattr("src.ui.refresh", no_network)
    app = AppTest.from_file(ROOT / "app.py").run(timeout=30)
    assert not app.exception
    for selected in ("20D", "60D", "120D", "1Y"):
        app.radio[0].set_value(selected).run(timeout=30)
        assert not app.exception
