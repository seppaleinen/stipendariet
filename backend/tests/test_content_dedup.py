"""
Unit tests for content deduplication using simhash.
"""

from app.utils.content_dedup import compute_content_hash, deduplicate_pages


def test_compute_content_hash_returns_32_char_hex():
    """Test compute_content_hash returns 32-char hex string (128-bit simhash)."""
    content = "This is test content for hashing with some unique words"
    hash_val = compute_content_hash(content)

    assert isinstance(hash_val, str)
    assert len(hash_val) == 32  # 128-bit = 32 hex chars
    # Verify all characters are valid hex
    int(hash_val, 16)


def test_compute_content_hash_deterministic():
    """Test compute_content_hash returns same hash for same content."""
    content = "This is the same content"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)

    assert hash1 == hash2


def test_compute_content_hash_different_content():
    """Test different content produces different hashes."""
    content1 = "This is content one"
    content2 = "This is content two"

    hash1 = compute_content_hash(content1)
    hash2 = compute_content_hash(content2)

    assert hash1 != hash2


def test_compute_content_hash_similar_content():
    """Test similar content produces similar hashes (low Hamming distance)."""
    content1 = "This is a test document with some content"
    content2 = "This is a test document with some content and more"

    hash1 = compute_content_hash(content1)
    hash2 = compute_content_hash(content2)

    # Similar content should have similar hashes
    # Hamming distance should be relatively low
    h1 = int(hash1, 16)
    h2 = int(hash2, 16)
    hamming = bin(h1 ^ h2).count("1")

    # Allow up to ~40 bits difference for similar content with added words (128-bit)
    assert hamming < 50


def test_deduplicate_pages_removes_duplicates():
    """Test deduplicate_pages removes exact duplicate pages."""
    pages = [
        {"url": "https://example.com/page1", "markdown": "Same content here", "content_hash": compute_content_hash("Same content here")},
        {"url": "https://example.com/page2", "markdown": "Same content here", "content_hash": compute_content_hash("Same content here")},
        {"url": "https://example.com/page3", "markdown": "Different content", "content_hash": compute_content_hash("Different content")},
    ]

    result = deduplicate_pages(pages)

    assert len(result) == 2
    assert result[0]["url"] == "https://example.com/page1"
    assert result[1]["url"] == "https://example.com/page3"


def test_deduplicate_pages_preserves_order():
    """Test deduplicate_pages preserves order of first occurrences."""
    pages = [
        {"url": "https://example.com/page1", "markdown": "Content A", "content_hash": compute_content_hash("Content A")},
        {"url": "https://example.com/page2", "markdown": "Content B", "content_hash": compute_content_hash("Content B")},
        {"url": "https://example.com/page3", "markdown": "Content A", "content_hash": compute_content_hash("Content A")},
    ]

    result = deduplicate_pages(pages)

    assert len(result) == 2
    assert result[0]["url"] == "https://example.com/page1"
    assert result[1]["url"] == "https://example.com/page2"


def test_deduplicate_pages_empty_list():
    """Test deduplicate_pages handles empty list."""
    result = deduplicate_pages([])

    assert result == []


def test_deduplicate_pages_no_duplicates():
    """Test deduplicate_pages returns all pages when no duplicates."""
    pages = [
        {"url": "https://example.com/page1", "markdown": "Content A", "content_hash": compute_content_hash("Content A")},
        {"url": "https://example.com/page2", "markdown": "Content B", "content_hash": compute_content_hash("Content B")},
        {"url": "https://example.com/page3", "markdown": "Content C", "content_hash": compute_content_hash("Content C")},
    ]

    result = deduplicate_pages(pages)

    assert len(result) == 3


def test_compute_content_hash_empty():
    """Test compute_content_hash handles empty content."""
    hash_val = compute_content_hash("")

    assert hash_val == "0" * 32


def test_compute_content_hash_whitespace():
    """Test compute_content_hash handles whitespace-only content."""
    hash_val = compute_content_hash("   \n\t  ")

    assert hash_val == "0" * 32
