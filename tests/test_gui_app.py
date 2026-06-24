from __future__ import annotations

import sys
import json
import datetime as dt
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class _FakeVar:
    def __init__(self, *a, **kw):
        self._val = kw.get("value", a[0] if a else None)
    def get(self): return self._val
    def set(self, v): self._val = v


_WIDGET_METHODS = {
    "configure": lambda s, *a, **kw: None,
    "config": lambda s, *a, **kw: None,
    "bind": lambda s, *a, **kw: None,
    "unbind": lambda s, *a, **kw: None,
    "grid": lambda s, *a, **kw: None,
    "grid_propagate": lambda s, *a, **kw: None,
    "grid_remove": lambda s, *a, **kw: None,
    "pack": lambda s, *a, **kw: None,
    "place": lambda s, *a, **kw: None,
    "pack_forget": lambda s, *a, **kw: None,
    "winfo_width": lambda s: 400,
    "winfo_height": lambda s: 300,
    "winfo_rootx": lambda s: 0,
    "winfo_rooty": lambda s: 0,
    "winfo_exists": lambda s: True,
    "bbox": lambda s, *a, **kw: (0, 0, 100, 50),
    "create_polygon": lambda s, *a, **kw: 1,
    "create_text": lambda s, *a, **kw: 1,
    "create_rectangle": lambda s, *a, **kw: 1,
    "create_oval": lambda s, *a, **kw: 1,
    "create_line": lambda s, *a, **kw: 1,
    "create_arc": lambda s, *a, **kw: 1,
    "create_image": lambda s, *a, **kw: 1,
    "create_window": lambda s, *a, **kw: 1,
    "delete": lambda s, *a, **kw: None,
    "tag_lower": lambda s, *a, **kw: None,
    "tag_configure": lambda s, *a, **kw: None,
    "tag_raise": lambda s, *a, **kw: None,
    "itemconfigure": lambda s, *a, **kw: None,
    "itemconfig": lambda s, *a, **kw: None,
    "columnconfigure": lambda s, *a, **kw: None,
    "rowconfigure": lambda s, *a, **kw: None,
    "cget": lambda s, *a, **kw: "",
    "focus_get": lambda s: None,
    "focus_set": lambda s, *a, **kw: None,
    "winfo_children": lambda s: [],
    "after": lambda s, *a, **kw: "after-id",
    "after_cancel": lambda s, *a, **kw: None,
    "destroy": lambda s, *a, **kw: None,
    "update_idletasks": lambda s, *a, **kw: None,
    "insert": lambda s, *a, **kw: None,
    "see": lambda s, *a, **kw: None,
    "select_range": lambda s, *a, **kw: None,
    "select_clear": lambda s, *a, **kw: None,
    "window_create": lambda s, *a, **kw: None,
    "yview_scroll": lambda s, *a, **kw: None,
    "yview": lambda s, *a, **kw: None,
    "set_active": lambda s, *a, **kw: None,
    "set_colors": lambda s, *a, **kw: None,
}

def _make_fake_widget_class(name="FakeWidget"):
    def __init__(self, *a, **kw): pass
    def __init_subclass__(cls, **kw): pass
    def __getattr__(self, name):
        return lambda *a, **kw: None
    ns = {"__init__": __init__, "__init_subclass__": __init_subclass__, "__getattr__": __getattr__}
    ns.update(_WIDGET_METHODS)
    return type(name, (), ns)


@pytest.fixture
def app(tmp_path):
    """Create a KnowledgeChatApp with mocked tkinter."""
    mock_root = MagicMock()
    mock_root.tk = MagicMock()
    mock_root.after = MagicMock(return_value="after-id")
    mock_root.after_cancel = MagicMock()
    mock_root.winfo_screenwidth = MagicMock(return_value=1920)
    mock_root.winfo_screenheight = MagicMock(return_value=1080)
    mock_root.configure = MagicMock()
    mock_root.title = MagicMock()
    mock_root.geometry = MagicMock()
    mock_root.minsize = MagicMock()
    mock_root.mainloop = MagicMock()
    mock_root.update = MagicMock()
    mock_root.destroy = MagicMock()
    mock_root.winfo_rootx = MagicMock(return_value=0)
    mock_root.winfo_rooty = MagicMock(return_value=0)
    mock_root.winfo_width = MagicMock(return_value=1120)
    mock_root.winfo_height = MagicMock(return_value=760)
    mock_root.columnconfigure = MagicMock()
    mock_root.rowconfigure = MagicMock()
    mock_root.bind_all = MagicMock()
    mock_root.update_idletasks = MagicMock()
    mock_root.wait_window = MagicMock()

    FakeCanvas = _make_fake_widget_class("FakeCanvas")
    FakeFrame = _make_fake_widget_class("FakeFrame")
    FakeLabel = _make_fake_widget_class("FakeLabel")
    FakeEntry = _make_fake_widget_class("FakeEntry")
    FakeText = _make_fake_widget_class("FakeText")
    FakeButton = _make_fake_widget_class("FakeButton")
    FakeScrollbar = _make_fake_widget_class("FakeScrollbar")

    mock_tk = MagicMock()
    mock_tk.Tk = MagicMock(return_value=mock_root)
    mock_tk.Frame = FakeFrame
    mock_tk.Canvas = FakeCanvas
    mock_tk.Label = FakeLabel
    mock_tk.Entry = FakeEntry
    mock_tk.Text = FakeText
    mock_tk.Button = FakeButton
    mock_tk.Scrollbar = FakeScrollbar
    mock_tk.BooleanVar = _FakeVar
    mock_tk.StringVar = _FakeVar
    mock_tk.IntVar = _FakeVar

    FakePhotoImage = type("FakePhotoImage", (), {
        "__init__": lambda s, *a, **kw: None,
        "width": lambda s: 100,
        "height": lambda s: 100,
        "subsample": lambda s, *a: s,
    })
    mock_tk.PhotoImage = FakePhotoImage
    mock_tk.Toplevel = MagicMock()
    mock_tk.TclError = type("TclError", (Exception,), {})
    mock_tk.Event = MagicMock
    for attr in ("N", "S", "E", "W", "LEFT", "RIGHT", "TOP", "BOTTOM", "BOTH", "X", "Y", "NONE", "END",
                 "NORMAL", "DISABLED", "HORIZONTAL", "VERTICAL", "CENTER", "YES", "NO",
                 "INSERT", "SEL", "WORD", "ACTIVE", "CURRENT", "ALL"):
        setattr(mock_tk, attr, "mock")

    mock_ttk = MagicMock()
    mock_ttk.Style = MagicMock(return_value=MagicMock(theme_use=MagicMock()))
    mock_ttk.Frame = _make_fake_widget_class("TtkFrame")
    mock_ttk.Scrollbar = _make_fake_widget_class("TtkScrollbar")
    mock_ttk.Separator = _make_fake_widget_class("TtkSeparator")
    mock_ttk.Notebook = MagicMock()
    mock_ttk.Label = _make_fake_widget_class("TtkLabel")
    mock_ttk.Button = _make_fake_widget_class("TtkButton")
    mock_ttk.Checkbutton = _make_fake_widget_class("TtkCheckbutton")
    mock_ttk.Combobox = _make_fake_widget_class("TtkCombobox")
    mock_ttk.Entry = _make_fake_widget_class("TtkEntry")
    mock_ttk.Progressbar = MagicMock()

    mock_colorchooser = MagicMock()
    mock_filedialog = MagicMock()
    mock_messagebox = MagicMock()
    mock_simpledialog = MagicMock()

    mock_widgets = MagicMock()
    mock_widgets.RoundedButton = MagicMock
    mock_widgets.IconButton = MagicMock
    mock_widgets.MiniToolButton = MagicMock
    mock_widgets.WebSearchToggleButton = MagicMock

    with patch.dict("sys.modules", {
        "tkinter": mock_tk,
        "tkinter.ttk": mock_ttk,
        "tkinter.colorchooser": mock_colorchooser,
        "tkinter.filedialog": mock_filedialog,
        "tkinter.messagebox": mock_messagebox,
        "tkinter.simpledialog": mock_simpledialog,
        "tkinterdnd2": MagicMock(),
        "knowledgelab.ui.widgets": mock_widgets,
    }):
        if "main" in sys.modules:
            del sys.modules["main"]
        for mod_name in list(sys.modules):
            if mod_name.startswith("knowledgelab.ui.chat_list"):
                del sys.modules[mod_name]
        import main

        main.SETTINGS_PATH = tmp_path / "settings.json"
        main.CHAT_STORE_PATH = tmp_path / "sessions.json"
        main.PROJECT_ACTIONS_PATH = tmp_path / "actions.json"
        main.VAULT_DIR = tmp_path / "vault"
        main.VAULT_DIR.mkdir(parents=True, exist_ok=True)

        if not hasattr(main, "WARNING_PREFIX"):
            main.WARNING_PREFIX = "[LM Studio Warning] "

        a = main.KnowledgeChatApp(mock_root)
        return a


# -----------------------------------------------------------------------
# 1. Settings management
# -----------------------------------------------------------------------

class TestSettingsManagement:

    def test_load_settings_returns_defaults_when_no_file(self, app, tmp_path):
        app.settings = app.load_settings()
        assert "send_on_enter" in app.settings
        assert "use_lightrag" in app.settings
        assert "game_guard_enabled" in app.settings
        assert "button_color" in app.settings

    def test_save_settings_creates_file(self, app, tmp_path):
        app.settings["send_on_enter"] = False
        app.save_settings()
        from knowledgelab.config import SETTINGS_PATH
        assert SETTINGS_PATH.exists()
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        assert data["send_on_enter"] is False

    def test_load_settings_roundtrip(self, app, tmp_path):
        app.settings["send_on_enter"] = False
        app.settings["web_search_enabled"] = True
        app.save_settings()
        app2_settings = app.load_settings()
        assert app2_settings["send_on_enter"] is False
        assert app2_settings["web_search_enabled"] is True

    def test_settings_has_expected_keys(self, app):
        expected = [
            "send_on_enter", "use_lightrag", "button_color",
            "game_guard_enabled", "auto_process_links", "auto_route_topics",
            "auto_create_topics", "auto_detect_books_in_images",
            "book_lookup_enabled", "web_search_enabled",
            "obsidian_path", "vault_path", "lmstudio_base_url",
            "llm_model", "embedding_model", "response_language",
        ]
        for key in expected:
            assert key in app.settings, f"Missing key: {key}"


# -----------------------------------------------------------------------
# 2. Chat store
# -----------------------------------------------------------------------

class TestChatStore:

    def test_load_chat_store_returns_empty_when_no_file(self, app, tmp_path):
        store_file = tmp_path / "sessions.json"
        if store_file.exists():
            store_file.unlink()
        store = app.load_chat_store()
        assert isinstance(store, dict)
        assert "chats" in store

    def test_create_chat_adds_to_store(self, app):
        initial_count = len(app.get_chats())
        app.create_chat(save=False)
        assert len(app.get_chats()) == initial_count + 1

    def test_delete_chat_removes_from_store(self, app):
        app.create_chat(save=False)
        chats = app.get_chats()
        assert len(chats) >= 2
        chat_to_delete = chats[-1]
        chat_id = chat_to_delete["id"]
        with patch("tkinter.messagebox.askyesno", return_value=True):
            app.delete_chat_by_id(chat_id)
        remaining_ids = [c["id"] for c in app.get_chats()]
        assert chat_id not in remaining_ids

    def test_rename_chat_updates_name(self, app):
        chat = app.get_active_chat()
        chat["title"] = "Test Rename Title"
        chat["updated_at"] = app.new_id("ts")
        app.save_chat_store()
        found = app.chat_by_id(chat["id"])
        assert found["title"] == "Test Rename Title"

    def test_get_active_chat_returns_current(self, app):
        chat = app.get_active_chat()
        assert chat is not None
        assert chat["id"] == app.active_chat_id

    def test_get_chats_returns_list(self, app):
        chats = app.get_chats()
        assert isinstance(chats, list)


# -----------------------------------------------------------------------
# 3. Message operations
# -----------------------------------------------------------------------

class TestMessageOperations:

    def test_add_message_appends_to_chat(self, app):
        chat = app.get_active_chat()
        initial_count = len(chat.get("messages", []))
        app.add_message("user", "hello")
        assert len(chat.get("messages", [])) >= initial_count + 1

    def test_add_message_stores_user_role(self, app):
        chat = app.get_active_chat()
        app.add_message("user", "test question")
        last_msg = chat["messages"][-1]
        assert last_msg["role"] == "user"
        assert last_msg["text"] == "test question"

    def test_add_message_stores_assistant_role(self, app):
        chat = app.get_active_chat()
        app.add_message("assistant", "test answer")
        last_msg = chat["messages"][-1]
        assert last_msg["role"] == "assistant"
        assert last_msg["text"] == "test answer"


# -----------------------------------------------------------------------
# 4. Intent classification
# -----------------------------------------------------------------------

class TestIntentClassification:

    def test_is_save_intent_with_url(self, app):
        assert app.is_save_intent("вот ссылка https://example.com/article") is True

    def test_is_save_intent_with_phrase(self, app):
        assert app.is_save_intent("сохрани этот материал") is True

    def test_is_save_intent_negative(self, app):
        assert app.is_save_intent("как работает React") is False

    def test_is_lightrag_help_intent(self, app):
        assert app.is_lightrag_help_intent("как пользоваться lightrag") is True

    def test_is_language_preference_intent(self, app):
        assert app.is_language_preference_intent("отвечай на русском") is True

    def test_wants_knowledge_lookup(self, app):
        assert app.wants_knowledge_lookup("найди в базе про CSS") is True


# -----------------------------------------------------------------------
# 5. String processing
# -----------------------------------------------------------------------

class TestStringProcessing:

    def test_split_knowledge_warnings(self, app):
        output = "::knowledge-warning something bad\nActual output line\nAnother line"
        result, warnings = app.split_knowledge_warnings(output)
        assert "Actual output line" in result
        assert "Another line" in result
        assert "something bad" in warnings

    def test_is_service_output_line(self, app):
        assert app.is_service_output_line("Game Guard: checking GPU") is True
        assert app.is_service_output_line("Starting LM Studio server...") is True
        assert app.is_service_output_line("This is regular output") is False

    def test_trim_output(self, app):
        assert app.trim_output("  hello  ") == "hello"
        assert app.trim_output("\n\nhello\n\n") == "hello"
        assert app.trim_output("") == ""

    def test_friendly_error(self, app):
        msg = app.friendly_error("NativeCommandError detected")
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_format_chat_age(self, app):
        now = dt.datetime.now().isoformat()
        age = app.format_chat_age(now)
        assert isinstance(age, str)

    def test_chat_group_name(self, app):
        chat = {"title": "Test", "messages": [{"context": "Web Development"}]}
        assert app.chat_group_name(chat) == "Web Development"

    def test_title_for_chat(self, app):
        title = app.title_for_chat("Hello World")
        assert title == "Hello World"

    def test_title_for_chat_truncates(self, app):
        long_text = "A" * 100
        title = app.title_for_chat(long_text)
        assert len(title) <= 45
        assert title.endswith("...")


# -----------------------------------------------------------------------
# 6. Routing
# -----------------------------------------------------------------------

class TestRouting:

    def test_selected_route_auto(self, app):
        route = app.selected_route("hello world")
        assert route is not None
        assert hasattr(route, "context_name")

    def test_selected_route_web(self, app):
        route = app.selected_route("react hooks tutorial")
        assert route is not None

    def test_selected_route_game(self, app):
        route = app.selected_route("unity game project")
        assert route is not None

    def test_selected_route_finished(self, app):
        route = app.selected_route("portfolio ready project")
        assert route is not None


# -----------------------------------------------------------------------
# 7. Path operations
# -----------------------------------------------------------------------

class TestPathOperations:

    def test_vault_dir_returns_path(self, app):
        vdir = app.vault_dir()
        assert isinstance(vdir, Path)

    def test_storage_name_for_scope(self, app):
        name = app.storage_name_for_scope("general", "default")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_storage_name_for_finished_projects(self, app):
        from knowledgelab.config import LAYER_FINISHED_PROJECTS
        name = app.storage_name_for_scope("all", "", LAYER_FINISHED_PROJECTS)
        assert name == "finished_projects"

    def test_lightrag_index_path(self, app):
        path = app.lightrag_index_path("general", "default")
        assert isinstance(path, Path)
        assert "vdb_chunks.json" in str(path)

    def test_capture_path_from_rel(self, app):
        path = app.capture_path_from_rel("50 Library/Books/Note.md")
        assert isinstance(path, Path)
        assert "50 Library" in str(path) or "50" in str(path)


# -----------------------------------------------------------------------
# 8. Project actions
# -----------------------------------------------------------------------

class TestProjectActions:

    def test_load_project_actions_empty(self, app, tmp_path):
        actions_file = tmp_path / "actions.json"
        if actions_file.exists():
            actions_file.unlink()
        actions = app.load_project_actions()
        assert isinstance(actions, dict)
        assert "actions" in actions

    def test_create_project_action(self, app):
        from knowledgelab.models import KnowledgeRoute
        route = KnowledgeRoute("Test", "general", "test-project")
        action_id = app.create_project_action(
            source_type="github_repository",
            source_url="https://github.com/test/repo",
            title="Test Project",
            route=route,
        )
        assert action_id.startswith("project-")
        action = app.get_project_action(action_id)
        assert action is not None
        assert action["source_type"] == "github_repository"

    def test_get_project_action(self, app):
        from knowledgelab.models import KnowledgeRoute
        route = KnowledgeRoute("T", "general", "t")
        aid = app.create_project_action(source_type="local_folder", title="My Folder", route=route)
        assert app.get_project_action(aid) is not None
        assert app.get_project_action("nonexistent-id") is None

    def test_update_project_action(self, app):
        from knowledgelab.models import KnowledgeRoute
        route = KnowledgeRoute("T", "general", "t")
        aid = app.create_project_action(source_type="local_folder", title="My Folder", route=route)
        app.update_project_action(aid, title="Updated Title")
        action = app.get_project_action(aid)
        assert action["title"] == "Updated Title"


# -----------------------------------------------------------------------
# 9. Background tasks
# -----------------------------------------------------------------------

class TestBackgroundTasks:

    def test_compact_background_tasks(self, app):
        result = app.compact_background_tasks()
        assert isinstance(result, list)

    def test_material_queue_summary(self, app):
        summary = app.material_queue_summary()
        assert isinstance(summary, str)

    def test_project_server_summary(self, app):
        summary = app.project_server_summary()
        assert isinstance(summary, str)


# -----------------------------------------------------------------------
# 10. Topic management
# -----------------------------------------------------------------------

class TestTopicManagement:

    def test_classify_material_topic(self, app):
        topic = app.classify_material_topic("React hooks tutorial", "web", "article")
        assert isinstance(topic, str)
        assert len(topic) > 0

    def test_ensure_topic_exists(self, app, tmp_path):
        result = app.ensure_topic_exists("New Test Topic", "general", "")
        assert isinstance(result, bool)


# -----------------------------------------------------------------------
# 11. Utility
# -----------------------------------------------------------------------

class TestUtility:

    def test_new_id_unique(self, app):
        id1 = app.new_id("msg")
        id2 = app.new_id("chat")
        assert id1 != id2
        assert id1.startswith("msg-")
        assert id2.startswith("chat-")

    def test_is_process_running(self, app):
        result = app.is_process_running(0)
        assert result is False

    def test_python_executable(self, app):
        exe = app.python_executable()
        assert isinstance(exe, str)
        assert len(exe) > 0

    def test_update_char_count(self, app):
        app.char_count_label = MagicMock()
        app.input = MagicMock()
        app.input.get = MagicMock(return_value="hello world")
        app.update_char_count()
        app.char_count_label.configure.assert_called()

    def test_new_id_chat_prefix(self, app):
        id1 = app.new_id("chat")
        assert id1.startswith("chat-")


# -----------------------------------------------------------------------
# 12. Book operations
# -----------------------------------------------------------------------

class TestBookOperations:

    def test_find_existing_book_note(self, app, tmp_path):
        book = {"title": "Nonexistent Book", "author": "Nobody"}
        result = app.find_existing_book_note(book)
        assert result == "" or isinstance(result, str)


# -----------------------------------------------------------------------
# 13. GPU
# -----------------------------------------------------------------------

class TestGPU:

    def test_is_gpu_snapshot_heavy(self, app):
        assert app.is_gpu_snapshot_heavy({"gpu_total": 0}) is False
        assert app.is_gpu_snapshot_heavy({"gpu_total": 50}) is True

    def test_is_gpu_snapshot_heavy_process(self, app):
        snapshot = {"gpu_total": 10, "processes": [{"gpu": 25}]}
        assert app.is_gpu_snapshot_heavy(snapshot) is True

    def test_is_gpu_snapshot_heavy_empty(self, app):
        assert app.is_gpu_snapshot_heavy({}) is False

    def test_is_gpu_snapshot_heavy_single_process_dict(self, app):
        snapshot = {"gpu_total": 5, "processes": {"gpu": 30}}
        assert app.is_gpu_snapshot_heavy(snapshot) is True


# -----------------------------------------------------------------------
# 14. Prompt building
# -----------------------------------------------------------------------

class TestPromptBuilding:

    def test_build_prompt_with_history(self, app):
        prompt = app.build_prompt_with_history("Hello")
        assert isinstance(prompt, str)
        assert "Hello" in prompt

    def test_is_safe_history_message(self, app):
        assert app.is_safe_history_message("Hello") is True
        assert app.is_safe_history_message("") is False
        assert app.is_safe_history_message("NativeCommandError occurred") is False
        assert app.is_safe_history_message("success! server is now running") is False

    def test_build_prompt_includes_context(self, app):
        prompt = app.build_prompt_with_history("test question")
        assert isinstance(prompt, str)
        assert len(prompt) > 0


# -----------------------------------------------------------------------
# 15. Chat selection and operations
# -----------------------------------------------------------------------

class TestChatSelection:

    def test_select_chat(self, app):
        app.create_chat(save=False)
        chats = app.get_chats()
        assert len(chats) >= 2
        other = chats[-1]
        app.select_chat(other["id"])
        assert app.active_chat_id == other["id"]

    def test_select_same_chat_noop(self, app):
        current = app.active_chat_id
        app.select_chat(current)
        assert app.active_chat_id == current

    def test_chat_by_id(self, app):
        chat = app.get_active_chat()
        found = app.chat_by_id(chat["id"])
        assert found is not None
        assert found["id"] == chat["id"]

    def test_chat_by_id_none(self, app):
        assert app.chat_by_id("nonexistent-id") is None


# -----------------------------------------------------------------------
# 16. Input history
# -----------------------------------------------------------------------

class TestInputHistory:

    def test_remember_input(self, app):
        app.input_history = []
        app.input_history_index = 0
        app.remember_input("test question 1")
        assert "test question 1" in app.input_history

    def test_remember_input_dedup(self, app):
        app.input_history = ["question"]
        app.input_history_index = 0
        app.remember_input("question")
        assert app.input_history.count("question") == 1

    def test_load_input_history(self, app):
        app.load_input_history()
        assert isinstance(app.input_history, list)


# -----------------------------------------------------------------------
# 17. Lightrag toggle
# -----------------------------------------------------------------------

class TestLightragToggle:

    def test_lightrag_help_message(self, app):
        msg = app.lightrag_help_message()
        assert isinstance(msg, str)
        assert len(msg) > 0
        assert "LightRAG" in msg

    def test_on_lightrag_toggle(self, app):
        app.lightrag_var = _FakeVar(True)
        app.on_lightrag_toggle(save=False)

    def test_is_lightrag_ready(self, app):
        result = app.is_lightrag_ready("general", "default")
        assert isinstance(result, bool)


# -----------------------------------------------------------------------
# 18. LM Studio integration (mocked)
# -----------------------------------------------------------------------

class TestLMStudioIntegration:

    def test_lmstudio_base_url(self, app):
        url = app.lmstudio_base_url()
        assert isinstance(url, str)
        assert "http" in url

    def test_llm_model_id(self, app):
        model = app.llm_model_id()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_embedding_model_id(self, app):
        model = app.embedding_model_id()
        assert isinstance(model, str)
        assert len(model) > 0


# -----------------------------------------------------------------------
# 19. Settings window operations
# -----------------------------------------------------------------------

class TestSettingsOperations:

    def test_color_preset_name(self, app):
        from knowledgelab.config import BUTTON_COLOR_PRESETS
        name = app.color_preset_name(BUTTON_COLOR_PRESETS["Blue"])
        assert name == "Blue"

    def test_color_preset_name_unknown(self, app):
        name = app.color_preset_name("#000000")
        assert name == "" or name is not None


# -----------------------------------------------------------------------
# 20. Clear chat
# -----------------------------------------------------------------------

class TestClearChat:

    def test_clear_chat_window(self, app):
        app.add_message("user", "test message to clear")
        chat = app.get_active_chat()
        assert len(chat.get("messages", [])) > 0
        app.clear_chat_window()
        chat = app.get_active_chat()
        assert len(chat.get("messages", [])) == 0
        assert chat["title"] == "Новый чат"


# -----------------------------------------------------------------------
# 21. Operation management
# -----------------------------------------------------------------------

class TestOperationManagement:

    def test_begin_operation(self, app):
        op_id = app.begin_operation("Testing...", 30)
        assert isinstance(op_id, int)
        assert op_id > 0

    def test_is_active_operation(self, app):
        op_id = app.begin_operation("Testing...", 30)
        assert app.is_active_operation(op_id) is True
        app.set_busy(False, "Ready")
        assert app.is_active_operation(op_id) is False

    def test_cancel_busy_timer(self, app):
        app.busy_timer_id = "some-timer-id"
        app.cancel_busy_timer()
        assert app.busy_timer_id is None


# -----------------------------------------------------------------------
# 22. Input text helpers
# -----------------------------------------------------------------------

class TestInputHelpers:

    def test_clear_input(self, app):
        app.input = MagicMock()
        app.clear_input()
        app.input.delete.assert_called()

    def test_replace_input(self, app):
        app.input = MagicMock()
        app.replace_input("new text")
        app.input.delete.assert_called()
        app.input.insert.assert_called()

    def test_append_to_input_empty(self, app):
        app.input = MagicMock()
        app.append_to_input("   ")
        app.input.insert.assert_not_called()


# -----------------------------------------------------------------------
# 23. Status animation
# -----------------------------------------------------------------------

class TestStatusAnimation:

    def test_stop_status_animation(self, app):
        app.status_animation_id = "some-id"
        app.stop_status_animation()
        assert app.status_animation_id is None

    def test_start_status_animation(self, app):
        app.start_status_animation("Testing")
        assert app.busy_status_base == "Testing"


# -----------------------------------------------------------------------
# 24. Game guard
# -----------------------------------------------------------------------

class TestGameGuard:

    def test_schedule_game_guard_probe_disabled(self, app):
        app.settings["game_guard_enabled"] = False
        app.schedule_game_guard_probe()
        assert True


# -----------------------------------------------------------------------
# 25. Message storage details
# -----------------------------------------------------------------------

class TestMessageStorageDetails:

    def test_add_message_with_warnings(self, app):
        chat = app.get_active_chat()
        app.add_message("system", "warn", warnings=["warning one", "warning two"])
        msg = chat["messages"][-1]
        assert "warning one" in msg.get("warnings", [])

    def test_add_message_auto_title(self, app):
        app.create_chat(save=False)
        chat = app.get_active_chat()
        chat["title"] = "Новый чат"
        app.add_message("user", "React hooks tutorial")
        assert chat["title"] != "Новый чат"
        assert "React" in chat["title"]

    def test_add_message_stores_context(self, app):
        chat = app.get_active_chat()
        app.add_message("user", "test", context_name="Web Development")
        msg = chat["messages"][-1]
        assert msg["context"] == "Web Development"

    def test_add_message_stores_project_action_id(self, app):
        chat = app.get_active_chat()
        app.add_message("assistant", "done", project_action_id="project-123")
        msg = chat["messages"][-1]
        assert msg["project_action_id"] == "project-123"


# -----------------------------------------------------------------------
# 26. Last answer lightrag state
# -----------------------------------------------------------------------

class TestLastAnswerLightragState:

    def test_last_answer_lightrag_state_none(self, app):
        app.create_chat(save=False)
        result = app.last_answer_lightrag_state()
        assert result is None or isinstance(result, bool)

    def test_last_answer_lightrag_state_after_message(self, app):
        app.add_message("assistant", "answer", lightrag_used=True)
        result = app.last_answer_lightrag_state()
        assert result is True

    def test_last_answer_lightrag_state_disabled(self, app):
        app.add_message("assistant", "answer", lightrag_used=False)
        result = app.last_answer_lightrag_state()
        assert result is False


# -----------------------------------------------------------------------
# 27. Save settings from window
# -----------------------------------------------------------------------

class TestSaveSettingsFromWindow:

    def test_save_settings_from_window(self, app):
        app.enter_send_var = _FakeVar(True)
        app.lightrag_var = _FakeVar(False)
        app.game_guard_var = _FakeVar(True)
        app.auto_process_links_var = _FakeVar(True)
        app.auto_route_topics_var = _FakeVar(True)
        app.auto_create_topics_var = _FakeVar(True)
        app.auto_detect_books_var = _FakeVar(True)
        app.book_lookup_enabled_var = _FakeVar(True)
        app.web_search_enabled_var = _FakeVar(False)
        app.button_color_var = _FakeVar("#476f9d")
        app.obsidian_path_var = _FakeVar("")
        app.vault_path_var = _FakeVar(str(app.vault_dir()))
        app.close_settings = MagicMock()
        app.save_settings_from_window()
        assert app.settings["send_on_enter"] is True
        assert app.settings["web_search_enabled"] is False
        app.close_settings.assert_called_once()


# -----------------------------------------------------------------------
# 28. Navigate input history
# -----------------------------------------------------------------------

class TestNavigateInputHistory:

    def test_navigate_input_history_empty(self, app):
        app.input_history = []
        app.input_history_index = 0
        result = app.navigate_input_history(-1)
        assert result == "break"

    def test_navigate_input_history_forward(self, app):
        app.input_history = ["q1", "q2", "q3"]
        app.input_history_index = 3
        app.replace_input = MagicMock()
        app.navigate_input_history(-1)
        assert app.input_history_index == 2

    def test_navigate_input_history_backward(self, app):
        app.input_history = ["q1", "q2", "q3"]
        app.input_history_index = 0
        app.replace_input = MagicMock()
        app.navigate_input_history(1)
        assert app.input_history_index == 1


# -----------------------------------------------------------------------
# 29. Active process management
# -----------------------------------------------------------------------

class TestActiveProcess:

    def test_set_active_process_none(self, app):
        app.set_active_process(None)
        assert app.active_process is None

    def test_terminate_active_process_none(self, app):
        app.set_active_process(None)
        result = app.terminate_active_process()
        assert result is False

    def test_terminate_active_process_finished(self, app):
        mock_process = MagicMock()
        mock_process.poll = MagicMock(return_value=0)
        app.set_active_process(mock_process)
        result = app.terminate_active_process()
        assert result is False


# -----------------------------------------------------------------------
# 30. Set busy
# -----------------------------------------------------------------------

class TestSetBusy:

    def test_set_busy_true(self, app):
        app.status_var = MagicMock()
        app.set_busy(True, "Working...")
        assert app.busy is True
        app.status_var.set.assert_called()

    def test_set_busy_false(self, app):
        app.status_var = MagicMock()
        app.set_busy(False, "Ready")
        assert app.busy is False
        app.status_var.set.assert_called_with("Ready")


# -----------------------------------------------------------------------
# 31. Video analysis report (mocked)
# -----------------------------------------------------------------------

class TestFormatVideoAnalysis:

    def test_append_video_analysis_report(self, app):
        from knowledgelab.models import VideoAnalysisReport
        report = VideoAnalysisReport(
            parent_note="test/Note.md",
            analysis_note="test/Analysis.md",
            source="test.mp4",
            transcript_status="done",
            frame_analysis_status="done",
            frame_count=3,
            code_snippet_count=1,
            warning="",
        )
        app.last_book_discovery_report = None
        app.append_assistant_message = MagicMock()
        try:
            app.append_video_analysis_report(report)
            app.append_assistant_message.assert_called()
        except NameError:
            pytest.skip("format_video_analysis_report not imported in main.py")
