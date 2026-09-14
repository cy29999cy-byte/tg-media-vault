"""Exercise real NiceGUI selectors and their save/reload behavior."""

from unittest.mock import Mock, patch

import pytest
import yaml

pytest.importorskip("nicegui")
from nicegui import ui

from webui.config_tab import build_config_tab
from webui.history_tab import build_history_tab


@pytest.mark.parametrize(
    "selected",
    [["sticker"], ["animation"], ["sticker", "animation"], ["document", "video"]],
)
def test_media_selection_round_trip(selected):
    config = {
        "api_id": 123,
        "api_hash": "test-placeholder",
        "media_types": ["document"],
        "chats": [{"chat_id": "@example", "media_types": ["video"]}],
    }
    callbacks = {}
    original_button = ui.button

    def button(text="", *args, **kwargs):
        if text == "Save Configuration":
            callbacks["save"] = kwargs["on_click"]
        return original_button(text, *args, **kwargs)

    save = Mock()
    with ui.column(), patch("webui.config_tab.ui.button", side_effect=button):
        global_inputs, chats = build_config_tab(config, save)
        for inputs in [global_inputs, chats[0]]:
            assert "sticker" in inputs["media_types"].options
            assert "animation" in inputs["media_types"].options
            inputs["media_types"].set_value(selected)
            inputs["format_sticker"].set_value("webp,tgs")
            inputs["format_animation"].set_value("gif,mp4")
        with patch("webui.config_tab.ui.notify"):
            callbacks["save"]()

    save.assert_called_once()
    restored = yaml.safe_load(yaml.safe_dump(save.call_args.args[0]))
    assert restored["media_types"] == selected
    assert restored["chats"][0]["media_types"] == selected
    for item in [restored, restored["chats"][0]]:
        assert item["file_formats"]["sticker"] == ["webp", "tgs"]
        assert item["file_formats"]["animation"] == ["gif", "mp4"]
    with ui.column():
        global_inputs, chats = build_config_tab(restored, Mock())
        assert global_inputs["media_types"].value == selected
        assert chats[0]["media_types"].value == selected
        assert chats[0]["format_sticker"].value == "webp,tgs"


def test_history_type_options():
    with ui.column(), patch("webui.history_tab.ui.select", wraps=ui.select) as select:
        build_history_tab({}, Mock(), ".")
    options = select.call_args.args[0]
    assert "sticker" in options
    assert "animation" in options
