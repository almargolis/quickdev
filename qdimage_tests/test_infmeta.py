"""Tests for qdimage.infmeta"""

import os
import tempfile
from datetime import datetime

import pytest
from PIL import Image

from qdimage.infmeta import InfMeta, _model_short_name, _description_key


class TestModelShortName:
    def test_claude(self):
        assert _model_short_name("claude-sonnet-4-20250514") == "claude"

    def test_gpt4o(self):
        assert _model_short_name("gpt-4o-2024-05-13") == "gpt4o"

    def test_gpt4(self):
        assert _model_short_name("gpt-4-turbo") == "gpt4"

    def test_empty(self):
        assert _model_short_name("") == "llm"

    def test_unknown(self):
        assert _model_short_name("mistral-7b") == "mistral"


class TestDescriptionKey:
    def test_manual(self):
        dt = datetime(2024, 1, 15, 14, 30)
        assert _description_key("manual", dt=dt) == "manual_20240115"

    def test_llm(self):
        dt = datetime(2024, 1, 15, 15, 0, 0)
        key = _description_key("llm", model="claude-sonnet-4-20250514", dt=dt)
        assert key == "claude_20240115_150000"


class TestInfMetaCreateNew:
    def test_create_new(self):
        with tempfile.TemporaryDirectory() as d:
            inf_path = os.path.join(d, "1.inf")
            meta = InfMeta.create_new(
                inf_path, xxhash="abcdef0123456789",
                file_size=1024, width=800, height=600,
                image_format="JPEG", keywords="test photo"
            )
            assert meta.data['xxhash'] == "abcdef0123456789"
            assert meta.data['file_size'] == 1024
            assert meta.data['image']['width'] == 800
            assert meta.data['keywords'] == "test photo"


class TestInfMetaFromImagePath:
    def test_from_image(self):
        with tempfile.TemporaryDirectory() as d:
            img_path = os.path.join(d, "test.jpg")
            img = Image.new('RGB', (200, 100), color='red')
            img.save(img_path, 'JPEG')

            meta = InfMeta.from_image_path(img_path)
            assert meta.data['image']['width'] == 200
            assert meta.data['image']['height'] == 100
            assert meta.data['image']['format'] == 'JPEG'
            assert len(meta.data['xxhash']) == 16
            assert meta.data['file_size'] > 0
            assert meta.inf_path == os.path.join(d, "test.inf")

    def test_merges_existing_inf(self):
        with tempfile.TemporaryDirectory() as d:
            img_path = os.path.join(d, "test.jpg")
            img = Image.new('RGB', (200, 100), color='red')
            img.save(img_path, 'JPEG')

            # Create an existing .inf with descriptions
            inf_path = os.path.join(d, "test.inf")
            meta1 = InfMeta.create_new(
                inf_path, xxhash="0000000000000000",
                file_size=100, width=200, height=100,
                image_format="JPEG", keywords="old keywords"
            )
            meta1.add_description("Old description", source="manual")
            meta1.save()

            # from_image_path should load existing descriptions
            meta2 = InfMeta.from_image_path(img_path)
            # xxhash gets recalculated from actual file
            assert meta2.data['xxhash'] != "0000000000000000"
            # descriptions should be preserved
            assert len(meta2.get_descriptions()) == 1


class TestInfMetaRoundTrip:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            inf_path = os.path.join(d, "1.inf")
            meta = InfMeta.create_new(
                inf_path, xxhash="abcdef0123456789",
                file_size=2048, width=1920, height=1080,
                image_format="JPEG", keywords="product photo"
            )
            meta.save()

            loaded = InfMeta.load(inf_path)
            assert loaded.data['xxhash'] == "abcdef0123456789"
            assert loaded.data['file_size'] == 2048
            assert loaded.data['image']['width'] == 1920
            assert loaded.data['keywords'] == "product photo"

    def test_round_trip_with_descriptions(self):
        with tempfile.TemporaryDirectory() as d:
            inf_path = os.path.join(d, "1.inf")
            meta = InfMeta.create_new(
                inf_path, xxhash="abcdef0123456789",
                file_size=2048, width=1920, height=1080,
                image_format="JPEG"
            )
            dt1 = datetime(2024, 1, 15, 14, 30)
            meta.add_description("Manual desc", source="manual", date=dt1)

            dt2 = datetime(2024, 1, 15, 15, 0, 0)
            meta.add_description(
                "LLM desc", source="llm",
                model="claude-sonnet-4-20250514", date=dt2
            )
            meta.save()

            loaded = InfMeta.load(inf_path)
            descs = loaded.get_descriptions()
            assert len(descs) == 2
            assert "manual_20240115" in descs
            assert "claude_20240115_150000" in descs
            assert descs["manual_20240115"]["text"] == "Manual desc"
            assert descs["claude_20240115_150000"]["model"] == "claude-sonnet-4-20250514"

    def test_round_trip_with_source(self):
        with tempfile.TemporaryDirectory() as d:
            inf_path = os.path.join(d, "2.inf")
            meta = InfMeta.create_new(
                inf_path, xxhash="1111111111111111",
                file_size=1024, width=800, height=600,
                image_format="JPEG"
            )
            meta.set_source(
                xxhash="0000000000000000", file_id="1.jpg",
                crop={'upper_left_x': 100, 'upper_left_y': 200,
                      'lower_right_x': 800, 'lower_right_y': 600},
                adjustments={'brightness': 1.25, 'background_removed': True}
            )
            meta.save()

            loaded = InfMeta.load(inf_path)
            source = loaded.data['source']
            assert source['xxhash'] == "0000000000000000"
            assert source['file_id'] == "1.jpg"
            assert source['crop']['upper_left_x'] == 100
            assert source['adjustments']['brightness'] == 1.25
            assert source['adjustments']['background_removed'] is True

    def test_round_trip_with_exif(self):
        with tempfile.TemporaryDirectory() as d:
            inf_path = os.path.join(d, "1.inf")
            meta = InfMeta.create_new(
                inf_path, xxhash="abcdef0123456789",
                file_size=2048, width=1920, height=1080,
                image_format="JPEG",
                exif={"Make": "Canon", "Model": "EOS R5"}
            )
            meta.save()

            loaded = InfMeta.load(inf_path)
            assert loaded.data['exif']['Make'] == "Canon"
            assert loaded.data['exif']['Model'] == "EOS R5"


class TestInfMetaDescriptions:
    def test_add_multiple_descriptions(self):
        meta = InfMeta("/tmp/test.inf", {})
        dt1 = datetime(2024, 1, 15, 14, 30)
        meta.add_description("First", source="manual", date=dt1)

        dt2 = datetime(2024, 1, 15, 15, 0, 0)
        meta.add_description("Second", source="llm",
                           model="claude-sonnet-4-20250514", date=dt2)

        dt3 = datetime(2024, 1, 16, 9, 0, 0)
        meta.add_description("Third", source="llm",
                           model="gpt-4o-2024-05-13", date=dt3)

        descs = meta.get_descriptions()
        assert len(descs) == 3

    def test_empty_descriptions(self):
        meta = InfMeta("/tmp/test.inf", {})
        assert meta.get_descriptions() == {}

    def test_custom_key(self):
        meta = InfMeta("/tmp/test.inf", {})
        meta.add_description("Custom", source="manual", key="my_custom_key")
        assert "my_custom_key" in meta.get_descriptions()


class TestInfMetaLoadErrors:
    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            InfMeta.load("/nonexistent/path.inf")
