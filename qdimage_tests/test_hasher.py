"""Tests for qdimage.hasher"""

from qdimage.hasher import calculate_xxhash


class TestCalculateXxhash:
    def test_returns_hex_string(self):
        result = calculate_xxhash(b"test data")
        assert isinstance(result, str)
        assert len(result) == 16
        # Verify it's a valid hex string
        int(result, 16)

    def test_same_input_same_hash(self):
        data = b"identical content"
        assert calculate_xxhash(data) == calculate_xxhash(data)

    def test_different_input_different_hash(self):
        assert calculate_xxhash(b"data1") != calculate_xxhash(b"data2")

    def test_empty_bytes(self):
        result = calculate_xxhash(b"")
        assert isinstance(result, str)
        assert len(result) == 16
