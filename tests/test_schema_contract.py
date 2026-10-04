from pathlib import Path


def test_schema_declares_legacy_identifier_sequences():
    schema = Path("init_db.py").read_text()

    assert "CREATE SEQUENCE IF NOT EXISTS seq_id_professor" in schema
    assert "CREATE SEQUENCE IF NOT EXISTS seq_id_admin" in schema
