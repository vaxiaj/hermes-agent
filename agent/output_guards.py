"""Guards for structured model output normalization."""

from __future__ import annotations

import re
from typing import Any, Iterable


_TEXT_TYPES = frozenset({"text", "output_text"})
_DATA_TYPES = frozenset({"data"})
_PROTECTED_FIELD_PATHS = {
    "plan_compare": ("plans[*].planId",),
    "pipeline_status": ("status", "stage"),
    "asset_ref": ("id", "label"),
}


def apply_adjacent_data_text_duplication_guard(output_items: Any) -> Any:
    """Drop duplicate adjacent text parts when they exactly mirror data fields.

    B7 is intentionally narrow:
    - only scan adjacent data/text pairs inside a single message content list
    - only match exact text == exact data field value
    - only delete the text part, never the data part
    """
    if not isinstance(output_items, list):
        return output_items

    for item in output_items:
        if _get_field(item, "type") == "message":
            _guard_message_content(item)
    _guard_top_level_output_items(output_items)

    return output_items


def _guard_message_content(item: Any) -> None:
    content = _get_field(item, "content")
    if not isinstance(content, list) or len(content) < 2:
        return

    drop_indices: set[int] = set()
    for idx in range(len(content) - 1):
        left = content[idx]
        right = content[idx + 1]

        if _is_text_part(left) and _is_data_part(right):
            if _text_matches_exact_data_value(left, right):
                drop_indices.add(idx)
        elif _is_data_part(left) and _is_text_part(right):
            if _text_matches_exact_data_value(right, left):
                drop_indices.add(idx + 1)

    if drop_indices:
        _set_field(
            item,
            "content",
            [part for idx, part in enumerate(content) if idx not in drop_indices],
        )


def _guard_top_level_output_items(output_items: list[Any]) -> None:
    drop_indices: set[int] = set()
    for idx in range(len(output_items) - 1):
        left = output_items[idx]
        right = output_items[idx + 1]
        left_type = _get_field(left, "type")
        right_type = _get_field(right, "type")

        if left_type == "message" and _is_data_part(right):
            if _message_item_matches_exact_data_value(left, right):
                drop_indices.add(idx)
        elif _is_data_part(left) and right_type == "message":
            if _message_item_matches_exact_data_value(right, left):
                drop_indices.add(idx + 1)

    if drop_indices:
        kept = [item for idx, item in enumerate(output_items) if idx not in drop_indices]
        output_items[:] = kept


def _is_text_part(part: Any) -> bool:
    return _get_field(part, "type") in _TEXT_TYPES and isinstance(_get_field(part, "text"), str)


def _is_data_part(part: Any) -> bool:
    return _get_field(part, "type") in _DATA_TYPES


def _text_matches_exact_data_value(text_part: Any, data_part: Any) -> bool:
    text = _get_field(text_part, "text")
    if not isinstance(text, str):
        return False

    normalized_text = text.strip()
    if not normalized_text:
        return False

    for candidate in extract_protected_values(data_part):
        if normalized_text == candidate or _text_has_exact_token(normalized_text, candidate):
            return True
    return False


def extract_protected_values(data_part: Any) -> list[str]:
    name = _get_field(data_part, "name")
    payload = _get_field(data_part, "data")
    if not isinstance(name, str):
        return []

    paths = _PROTECTED_FIELD_PATHS.get(name, ())
    values: list[str] = []
    for path in paths:
        for candidate in _extract_path_values(payload, path):
            if candidate not in values:
                values.append(candidate)
    return values


def _message_item_matches_exact_data_value(message_item: Any, data_item: Any) -> bool:
    content = _get_field(message_item, "content")
    if not isinstance(content, list):
        return False
    for part in content:
        if _is_text_part(part) and _text_matches_exact_data_value(part, data_item):
            return True
    return False


def _text_has_exact_token(text: str, candidate: str) -> bool:
    return bool(
        re.search(rf"(?<![A-Za-z0-9_]){re.escape(candidate)}(?![A-Za-z0-9_])", text)
    )


def _extract_path_values(value: Any, path: str) -> Iterable[str]:
    current = _to_plain_data(value)
    segments = path.split(".")
    for idx, segment in enumerate(segments):
        if segment.endswith("[*]"):
            key = segment[:-3]
            children = []
            if isinstance(current, dict):
                maybe_children = current.get(key, [])
                if isinstance(maybe_children, list):
                    children = maybe_children
            if not children:
                return
            remaining = ".".join(segments[idx + 1 :])
            for child in children:
                if remaining:
                    yield from _extract_path_values(child, remaining)
                else:
                    yield from _coerce_string_values(child)
            return

        if isinstance(current, dict):
            current = current.get(segment)
        else:
            return

    yield from _coerce_string_values(current)


def _coerce_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            yield normalized


def _to_plain_data(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    obj_dict = getattr(value, "__dict__", None)
    if isinstance(obj_dict, dict):
        return obj_dict
    return value


def _get_field(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _set_field(value: Any, key: str, new_value: Any) -> None:
    if isinstance(value, dict):
        value[key] = new_value
    else:
        setattr(value, key, new_value)
