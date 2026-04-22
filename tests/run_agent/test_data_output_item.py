from pathlib import Path
import json


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "data_part"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / f"{name}.sse").read_text(encoding="utf-8")


def _extract_added_item(name: str) -> dict:
    text = _read_fixture(name)
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    for chunk in chunks:
        lines = chunk.splitlines()
        if not lines or lines[0] != "event: response.output_item.added":
            continue
        payload = json.loads(lines[1].removeprefix("data: ").strip())
        return payload["item"]
    raise AssertionError(f"no output_item.added event found in {name}.sse")


def test_plan_compare_fixture_replays_data_item_shape():
    text = _read_fixture("plan_compare")
    assert "event: response.output_item.added" in text
    item = _extract_added_item("plan_compare")
    assert item["type"] == "data"
    assert item["name"] == "plan_compare"
    assert isinstance(item["data"], dict)
    assert item["data"]["plans"][0]["planId"] == "plan_001"


def test_pipeline_status_fixture_replays_data_item_shape():
    text = _read_fixture("pipeline_status")
    assert "event: response.output_item.added" in text
    item = _extract_added_item("pipeline_status")
    assert item["type"] == "data"
    assert item["name"] == "pipeline_status"
    assert isinstance(item["data"], dict)
    assert item["data"]["status"] == "running"
    assert item["data"]["stage"] == "render"


def test_asset_ref_fixture_replays_data_item_shape():
    text = _read_fixture("asset_ref")
    assert "event: response.output_item.added" in text
    item = _extract_added_item("asset_ref")
    assert item["type"] == "data"
    assert item["name"] == "asset_ref"
    assert isinstance(item["data"], dict)
    assert item["data"]["id"] == "asset_001"
    assert item["data"]["label"] == "主角立绘"
