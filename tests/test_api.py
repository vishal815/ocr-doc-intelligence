from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_and_retrieve_simple_pdf(client):
    with open(SAMPLES / "simple_text.pdf", "rb") as f:
        resp = client.post("/documents/upload", files={"file": ("simple_text.pdf", f, "application/pdf")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processed"
    document_id = body["document_id"]

    resp2 = client.get(f"/documents/{document_id}")
    assert resp2.status_code == 200
    result = resp2.json()
    assert result["page_count"] == 1
    assert any(el["type"] == "heading" for el in result["pages"][0]["elements"])


def test_upload_and_retrieve_text_export(client):
    with open(SAMPLES / "table_report.pdf", "rb") as f:
        resp = client.post("/documents/upload", files={"file": ("table_report.pdf", f, "application/pdf")})
    document_id = resp.json()["document_id"]

    resp2 = client.get(f"/documents/{document_id}/text")
    assert resp2.status_code == 200
    assert "Invoice" in resp2.text
    assert "Item" in resp2.text and "Widget" in resp2.text


def test_upload_rejects_unsupported_file_type(client):
    with open(SAMPLES / "invalid.txt", "rb") as f:
        resp = client.post("/documents/upload", files={"file": ("invalid.txt", f, "text/plain")})
    assert resp.status_code == 415


def test_upload_rejects_oversized_file(client, monkeypatch):
    import app.services.validation as validation

    monkeypatch.setattr(validation, "MAX_FILE_SIZE_MB", 0.0001)
    with open(SAMPLES / "simple_text.pdf", "rb") as f:
        resp = client.post("/documents/upload", files={"file": ("simple_text.pdf", f, "application/pdf")})
    assert resp.status_code == 413


def test_get_nonexistent_document_returns_404(client):
    resp = client.get("/documents/does-not-exist")
    assert resp.status_code == 404
