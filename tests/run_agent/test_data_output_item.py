from pathlib import Path


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "data_part"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.sse").read_text(encoding="utf-8")


def test_plan_compare_fixture_contains_data_item():
    text = _read_fixture("plan_compare")
    assert "event: response.output_item.added" in text
    assert '"type":"data"' in text
    assert '"name":"plan_compare"' in text


def test_pipeline_status_fixture_contains_data_item():
    text = _read_fixture("pipeline_status")
    assert "event: response.output_item.added" in text
    assert '"type":"data"' in text
    assert '"name":"pipeline_status"' in text


def test_asset_ref_fixture_contains_data_item():
    text = _read_fixture("asset_ref")
    assert "event: response.output_item.added" in text
    assert '"type":"data"' in text
    assert '"name":"asset_ref"' in text
