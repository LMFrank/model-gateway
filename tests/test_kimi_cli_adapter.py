from app.adapters.kimi_cli import KimiCliAdapter
from app.config import Settings


def _make_payload(content: str) -> dict[str, object]:
    return {
        "model": "kimi-for-coding",
        "messages": [{"role": "user", "content": content}],
    }


def test_build_command_long_prompt_uses_stdin_and_not_argv() -> None:
    adapter = KimiCliAdapter(Settings())
    long_content = "A" * 150000
    payload = _make_payload(long_content)
    provider_config = {
        "command": "kimi",
        "args": ["chat"],
        "extra_args": ["--print", "--output-format", "text", "--final-message-only"],
        "prompt_arg": "-p",
        "use_stdin_prompt": True,
    }

    cmd, prompt, _, use_stdin_prompt = adapter._build_command(payload, provider_config, stream=False)

    assert use_stdin_prompt is True
    assert "-p" not in cmd
    assert prompt.endswith(long_content)
    assert all(long_content not in arg for arg in cmd)


def test_build_command_use_stdin_prompt_false_keeps_prompt_arg_mode() -> None:
    adapter = KimiCliAdapter(Settings())
    content = "hello kimi"
    payload = _make_payload(content)
    provider_config = {
        "command": "kimi",
        "args": ["chat"],
        "extra_args": ["--print", "--output-format", "text"],
        "prompt_arg": "-p",
        "use_stdin_prompt": False,
    }

    cmd, prompt, _, use_stdin_prompt = adapter._build_command(payload, provider_config, stream=False)

    assert use_stdin_prompt is False
    assert "-p" in cmd
    prompt_idx = cmd.index("-p")
    assert cmd[prompt_idx + 1] == prompt


def test_build_command_auto_adds_input_format_text_when_print_enabled() -> None:
    adapter = KimiCliAdapter(Settings())
    payload = _make_payload("hello")
    provider_config = {
        "command": "kimi",
        "args": ["chat"],
        "extra_args": ["--print", "--output-format", "text", "--final-message-only"],
        "prompt_arg": "-p",
        "use_stdin_prompt": True,
    }

    cmd, _, _, use_stdin_prompt = adapter._build_command(payload, provider_config, stream=False)

    assert use_stdin_prompt is True
    assert "--input-format" in cmd
    idx = cmd.index("--input-format")
    assert cmd[idx + 1] == "text"
