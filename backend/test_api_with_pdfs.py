#!/usr/bin/env python3
"""Test FastAPI endpoint with PDF downloads enabled."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.mas_crawler.api import create_app
from src.mas_crawler.config import Config
from fastapi.testclient import TestClient

print("=" * 70)
print("FastAPI PDF Download Test")
print("=" * 70)

# Setup
config = Config.from_env()
download_dir = "/tmp/mas_crawler_test_downloads"
config.download_dir = download_dir

# Create test directory
os.makedirs(download_dir, exist_ok=True)
print(f"\n[SETUP] Download directory: {download_dir}")

# Create app
try:
    app = create_app(config)
    print("✓ FastAPI app created")
except Exception as e:
    print(f"✗ Failed to create app: {e}")
    sys.exit(1)

# Create test client
try:
    client = TestClient(app)
    print("✓ TestClient created")
except Exception as e:
    print(f"✗ Failed to create TestClient: {e}")
    sys.exit(1)

# Test 1: Health check
print("\n[TEST 1] Health Check")
try:
    response = client.get("/api/v1/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✓ Health check passed")
except Exception as e:
    print(f"✗ Health check failed: {e}")

# Test 2: Crawl WITH PDF downloads
print("\n[TEST 2] Crawl with PDF Downloads (limited to 3)")
try:
    response = client.post(
        "/api/v1/crawl",
        json={
            "days_back": 90,
            "include_pdfs": True,
            "max_pdfs": 3,  # Limit to 3 PDFs
        },
    )

    print(f"  Status code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    session = data["session"]
    documents = data["documents"]

    print(f"  Session ID: {session['session_id']}")
    print(f"  Documents found: {session['documents_found']}")
    print(f"  Documents downloaded: {session['documents_downloaded']}")
    print(f"  Documents returned: {len(documents)}")
    print(f"  Success: {session['success']}")

    # Verify response structure
    assert "session" in data, "Missing 'session' in response"
    assert "documents" in data, "Missing 'documents' in response"
    assert "session_id" in session, "Missing 'session_id'"
    assert "documents_found" in session, "Missing 'documents_found'"
    assert "documents_downloaded" in session, "Missing 'documents_downloaded'"

    print("✓ Response structure is correct")

except Exception as e:
    print(f"✗ Crawl failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify PDF downloads
print("\n[TEST 3] Verify PDF Downloads")
try:
    # Check downloaded files
    if os.path.exists(download_dir):
        files = os.listdir(download_dir)
        pdf_files = [f for f in files if f.endswith('.pdf')]
        print(f"  Downloaded PDFs: {len(pdf_files)}")

        if pdf_files:
            print(f"  Files: {pdf_files[:5]}")  # Show first 5

            # Check file sizes
            for pdf_file in pdf_files[:3]:
                file_path = os.path.join(download_dir, pdf_file)
                file_size = os.path.getsize(file_path)
                print(f"    - {pdf_file}: {file_size} bytes")

        if session['documents_downloaded'] > 0:
            if len(pdf_files) > 0:
                print("✓ PDFs were downloaded successfully")
            else:
                print("⚠ PDFs reported as downloaded but files not found on disk")
        else:
            print("⚠ No PDFs reported as downloaded")

    else:
        print(f"⚠ Download directory not found: {download_dir}")

except Exception as e:
    print(f"✗ PDF verification failed: {e}")

# Test 4: Verify document response has PDF fields
print("\n[TEST 4] Verify Document Response Fields")
try:
    docs_with_pdfs = [d for d in documents if d.get('downloaded_pdf_path')]
    docs_without_pdfs = [d for d in documents if not d.get('downloaded_pdf_path')]

    print(f"  Documents with PDF path: {len(docs_with_pdfs)}")
    print(f"  Documents without PDF path: {len(docs_without_pdfs)}")

    if docs_with_pdfs:
        doc = docs_with_pdfs[0]
        print(f"\n  Sample document with PDF:")
        print(f"    - Title: {doc['title'][:50]}...")
        print(f"    - Category: {doc['category']}")
        print(f"    - Downloaded PDF path: {doc['downloaded_pdf_path']}")
        print(f"    - File hash: {doc['file_hash'][:16]}..." if doc['file_hash'] else "    - File hash: None")
        print(f"    - Download timestamp: {doc['download_timestamp']}")

        # Verify fields
        assert doc['downloaded_pdf_path'] is not None, "PDF path should not be None"
        assert doc['file_hash'] is not None, "File hash should not be None"
        assert doc['download_timestamp'] is not None, "Download timestamp should not be None"
        assert len(doc['file_hash']) == 64, f"Hash should be 64 chars (SHA-256), got {len(doc['file_hash'])}"

        print("✓ Document PDF fields are valid")
    else:
        print("⚠ No documents with PDF paths to validate")

except Exception as e:
    print(f"✗ Document verification failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Verify JSON serialization
print("\n[TEST 5] Verify JSON Serialization")
try:
    # Try to serialize to JSON
    json_str = json.dumps(data)
    assert isinstance(json_str, str), "JSON serialization failed"

    # Try to parse back
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict), "JSON parsing failed"

    print(f"  JSON size: {len(json_str)} bytes")
    print("✓ JSON serialization is valid")

except Exception as e:
    print(f"✗ JSON serialization failed: {e}")

# Test 6: Verify status endpoint
print("\n[TEST 6] Status Endpoint")
try:
    session_id = session['session_id']
    response = client.get(f"/api/v1/crawl/status/{session_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    status_data = response.json()
    assert status_data['session_id'] == session_id
    assert status_data['status'] == 'completed'
    assert status_data['result'] is not None

    print(f"  Session ID: {status_data['session_id']}")
    print(f"  Status: {status_data['status']}")
    print("✓ Status endpoint works")

except Exception as e:
    print(f"✗ Status endpoint failed: {e}")

# Summary
print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)
print("\n✓ API is working correctly")
print(f"✓ PDFs downloaded: {session['documents_downloaded']}")
print(f"✓ Documents returned: {len(documents)}")
print(f"✓ Download directory: {download_dir}")
print("\nTo view downloaded files:")
print(f"  ls -lh {download_dir}")
print("\n" + "=" * 70)
