"""
Generate JSON schema and OpenAPI documentation from Pydantic models.

This script generates:
1. JSON schema for CrawlResult model
2. Standalone schema files for documentation
"""

import json
from pathlib import Path

from .models import CrawlResult, Document, CrawlSession, Category


def generate_json_schema() -> dict:
    """
    Generate JSON schema from CrawlResult Pydantic model.

    Returns:
        dict: Complete JSON schema including all model definitions
    """
    return CrawlResult.model_json_schema()


def save_schema_to_file(schema: dict, output_path: str) -> None:
    """
    Save JSON schema to a file with pretty formatting.

    Args:
        schema: JSON schema dictionary
        output_path: Path where schema should be saved
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"Schema saved to: {output_file}")


def generate_model_examples() -> dict:
    """
    Generate example JSON data for documentation.

    Returns:
        dict: Examples for each model type
    """
    from datetime import datetime, timezone

    # Example document
    example_document = Document(
        title="Notice on AML/CFT Requirements for Trade Finance",
        publication_date=datetime(2025, 10, 15, tzinfo=timezone.utc),
        category=Category.CIRCULAR,
        source_url="https://www.mas.gov.sg/news/circular-001",
        normalized_url="https://www.mas.gov.sg/news/circular-001",
        downloaded_pdf_path="./downloads/circular_001.pdf",
        file_hash="a" * 64,
        download_timestamp=datetime(2025, 11, 1, 14, 35, 50, tzinfo=timezone.utc),
    )

    # Example session
    example_session = CrawlSession(
        session_id="crawl_20251101_143542",
        start_time=datetime(2025, 11, 1, 14, 35, 42, tzinfo=timezone.utc),
        end_time=datetime(2025, 11, 1, 14, 38, 15, tzinfo=timezone.utc),
        duration_seconds=153.5,
        documents_found=28,
        documents_downloaded=25,
        documents_skipped=3,
        errors_encountered=2,
        errors_details=[
            "HTTP 404: Regulation page unavailable",
            "PDF timeout: max retries exceeded",
        ],
        success=True,
        crawl_config={
            "days_back": 90,
            "include_pdfs": True,
            "download_dir": "./downloads",
            "max_pdf_size_mb": 50,
        },
    )

    # Example crawl result
    example_result = CrawlResult(session=example_session, documents=[example_document])

    return {
        "document": json.loads(example_document.model_dump_json()),
        "session": json.loads(example_session.model_dump_json()),
        "crawl_result": json.loads(example_result.model_dump_json()),
    }


def main():
    """Generate and save JSON schema and examples."""
    print("Generating JSON schema from Pydantic models...")

    # Generate schema
    schema = generate_json_schema()

    # Save to docs directory
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    schema_path = docs_dir / "json_schema.json"
    save_schema_to_file(schema, str(schema_path))

    # Generate and save examples
    print("\nGenerating example JSON data...")
    examples = generate_model_examples()
    examples_path = docs_dir / "json_examples.json"
    save_schema_to_file(examples, str(examples_path))

    print("\n" + "=" * 60)
    print("Schema generation complete!")
    print("=" * 60)
    print(f"\nJSON Schema: {schema_path}")
    print(f"Examples: {examples_path}")
    print(f"\nSchema contains {len(schema.get('$defs', {}))} model definitions")


if __name__ == "__main__":
    main()
