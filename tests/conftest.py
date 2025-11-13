# tests/conftest.py
import sys
from pathlib import Path

# Вкарваме root на проекта (папката над tests/) в sys.path преди импорти
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import main  # вече ще се намери

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()
    monkeypatch.setattr(main, "STORAGE_DIR", storage)
    # ресетваме брояча в main (ако имате функция get_file_count)
    try:
        main.files_stored_counter = main.get_file_count()
    except AttributeError:
        # ако main.get_file_count не е експортирана, може да се пресметне:
        main.files_stored_counter = len([f for f in storage.iterdir() if f.is_file()])
    return TestClient(main.app)
