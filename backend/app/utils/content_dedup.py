"""
Content deduplication utilities using simhash.

Simhash is a locality-sensitive hash that allows near-duplicate detection
by comparing hash similarity. Two similar documents will have similar hashes.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Tokenize text into 5-grams for simhash."""
    text = text.lower()
    # Keep alphanumeric only
    text = "".join(c if c.isalnum() else " " for c in text)
    words = text.split()
    # Create 5-grams
    if len(words) < 5:
        return [text]
    return [" ".join(words[i : i + 5]) for i in range(len(words) - 4)]


def _simhash_128(text: str) -> int:
    """
    Compute 128-bit simhash for text.

    Uses 5-grams and 128-bit hash values. Returns Python int (arbitrary precision).
    """
    tokens = _tokenize(text)
    if not tokens:
        return 0

    # 128-bit accumulator for each bit position
    bits = [0] * 128

    for token in tokens:
        # Get 128-bit hash of token (using MD5 = 128-bit)
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)

        for i in range(128):
            if h & (1 << i):
                bits[i] += 1
            else:
                bits[i] -= 1

    # Build final hash
    result = 0
    for i in range(128):
        if bits[i] > 0:
            result |= 1 << i

    return result


def compute_content_hash(content: str) -> str:
    """
    Compute 32-char hex simhash for content.

    Args:
        content: Text content to hash

    Returns:
        32-character hexadecimal string (128-bit hash)
    """
    if not content or not content.strip():
        return "0" * 32

    hash_val = _simhash_128(content)
    return f"{hash_val:032x}"


def _hamming_distance(h1: int, h2: int) -> int:
    """Compute Hamming distance between two 128-bit hashes."""
    return bin(h1 ^ h2).count("1")


def deduplicate_pages(pages: list[dict]) -> list[dict]:
    """
    Deduplicate pages using simhash similarity.

    Pages with Hamming distance <= 3 (out of 128 bits) are considered duplicates.
    The first occurrence is kept, subsequent duplicates are removed.

    Args:
        pages: List of page dicts with 'content_hash' key

    Returns:
        Deduplicated list of pages (preserves original order of first occurrences)
    """
    if not pages:
        return []

    # Parse hashes to integers without mutating input pages
    page_hash_pairs = []
    for page in pages:
        if "content_hash" in page and page["content_hash"]:
            try:
                hash_int = int(page["content_hash"], 16)
            except (ValueError, TypeError):
                hash_int = 0
        else:
            hash_int = 0
        page_hash_pairs.append((page, hash_int))

    seen_hashes: list[int] = []
    result = []

    for page, h in page_hash_pairs:
        # Check if similar to any seen hash (Hamming distance <= 3)
        is_duplicate = False
        for seen_h in seen_hashes:
            if bin(h ^ seen_h).count("1") <= 3:
                is_duplicate = True
                logger.debug(
                    f"Duplicate detected: {page.get('url')} (distance: {bin(h ^ seen_h).count('1')})"
                )
                break

        if not is_duplicate:
            seen_hashes.append(h)
            result.append(page)

    return result
