from datetime import date, datetime, timezone

from src.database.db import connect
from src.database.v3 import persist_sector_classifications, read_sector_as_of
from src.models_v3 import SectorClassification


def test_sector_mapping_is_not_used_before_available_date(tmp_path):
    row = SectorClassification(ticker="3702", sector="TWSE-29", industry="29", classification_source="official",
        retrieved_at=datetime(2026,9,25,tzinfo=timezone.utc), available_date=date(2026,9,25), effective_from=date(2026,9,25))
    with connect(tmp_path/"sector.duckdb") as db:
        persist_sector_classifications(db, [row])
        assert read_sector_as_of(db, "3702", date(2026,9,24)) is None
        assert read_sector_as_of(db, "3702", date(2026,9,25))[1] == "TWSE-29"
