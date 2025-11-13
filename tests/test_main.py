import os
from pathlib import Path
import main

def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    j = resp.json()
    assert "message" in j and j["message"] == "File Storage API"
    assert "endpoints" in j and isinstance(j["endpoints"], list)


def test_store_and_get_file(client):
    # качваме файл
    files = {"file": ("hello.txt", b"hello world", "text/plain")}
    resp = client.post("/files", files=files)
    assert resp.status_code == 200
    j = resp.json()
    assert j["filename"] == "hello.txt"
    assert j["size"] == len(b"hello world")
    # теглим файла
    get_resp = client.get("/files/hello.txt")
    assert get_resp.status_code == 200
    assert get_resp.content == b"hello world"
    # content type от FileResponse
    assert get_resp.headers.get("content-type") == "application/octet-stream"


def test_list_files(client):
    # качваме два файла
    client.post("/files", files={"file": ("a.txt", b"a", "text/plain")})
    client.post("/files", files={"file": ("b.txt", b"b", "text/plain")})
    resp = client.get("/files")
    assert resp.status_code == 200
    j = resp.json()
    assert "files" in j and isinstance(j["files"], list)
    assert set(j["files"]) >= {"a.txt", "b.txt"}
    assert j["count"] == len(j["files"])


def test_metrics_counter_and_overwrite_behavior(client):
    # Проверяваме, че броячът на съхранени файлове (files_stored_counter)
    # се увеличава само при нов файл, а при overwrite остава същият.
    # Нулираме брояча (fixture-а вече го е нулирал по-горе, но правим сигурно)
    main.files_stored_counter = main.get_file_count()

    # качваме нов файл
    client.post("/files", files={"file": ("dup.txt", b"first", "text/plain")})
    m1 = client.get("/metrics").json()
    assert m1["files_stored_total"] == 1
    assert m1["files_current"] == 1

    # качваме със същото име (overwrite)
    client.post("/files", files={"file": ("dup.txt", b"second", "text/plain")})
    m2 = client.get("/metrics").json()
    # files_stored_total не трябва да се е увеличил (остава 1)
    assert m2["files_stored_total"] == 1
    # но в текущите файлове трябва да имаме все още 1
    assert m2["files_current"] == 1

    # проверяваме, че съдържанието е overwrite-нато
    get_resp = client.get("/files/dup.txt")
    assert get_resp.status_code == 200
    assert get_resp.content == b"second"


def test_get_file_directory_traversal_blocked(client, tmp_path, monkeypatch):
    """
    GET /files/{filename} трябва да предотврати directory traversal.
    При опит да се поиска файл извън storage очакваме да не се върне
    съдържанието му (и status 400 или 404).
    """
    # Създаваме тестов файл извън папката storage
    outside_file = tmp_path / "outside.txt"
    outside_bytes = b"outside"
    outside_file.write_bytes(outside_bytes)

    # Установяваме storage да е под-директория на tmp_path
    storage = tmp_path / "storage"
    storage.mkdir(exist_ok=True)

    # Monkeypatch-ваме main.STORAGE_DIR към тази папка
    monkeypatch.setattr(main, "STORAGE_DIR", storage)
    main.files_stored_counter = main.get_file_count()

    # 1) Опит с нормален ../ сегмент (може да бъде нормализиран -> 404)
    resp = client.get("/files/../outside.txt")
    assert resp.status_code in (400, 404)

    # Уверяваме се, че не е върнато съдържанието на outside.txt
    assert resp.content != outside_bytes

    # 2) Допълнителен опит с URL-encoding — някои сървъри ще връщат 400 тогава.
    resp_enc = client.get("/files/%2E%2E%2Foutside.txt")
    # accept 400 or 404 (depending on how server decodes/normalizes),
    # but definitely not 200 with outside_file content.
    assert resp_enc.status_code in (400, 404)
    assert resp_enc.content != outside_bytes
