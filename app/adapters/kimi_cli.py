import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.adapters.base import AdapterError, StreamHandle
from app.config import Settings


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in messages:
        role = str(item.get("role", "user"))
        content = item.get("content", "")
        if isinstance(content, list):
            merged = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    merged.append(str(part.get("text", "")))
            content = "\n".join(merged)
        lines.append(f"[{role}] {str(content)}")
    return "\n".join(lines).strip()


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


class KimiCliAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(self, payload: dict[str, Any], provider_config: dict[str, Any]) -> dict[str, Any]:
        cmd, prompt, env, use_stdin_prompt = self._build_command(payload, provider_config, stream=False)
        timeout_sec = int(provider_config.get("timeout_sec", self.settings.kimi_timeout_sec))
        stdin = asyncio.subprocess.PIPE if use_stdin_prompt else None
        stdin_input = prompt.encode("utf-8") if use_stdin_prompt else None
        response_file = str(provider_config.get("response_file", "")).strip() or None
        if response_file:
            try:
                os.remove(response_file)
            except FileNotFoundError:
                pass

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=stdin,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(input=stdin_input), timeout=timeout_sec)
        except asyncio.TimeoutError as exc:
            raise AdapterError(f"kimi cli timeout after {timeout_sec}s") from exc
        except FileNotFoundError as exc:
            raise AdapterError(f"kimi cli command not found: {cmd[0]}") from exc
        except OSError as exc:
            raise AdapterError(f"kimi cli process spawn failed: {exc}") from exc

        if proc.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="ignore").strip()
            raise AdapterError(f"kimi cli failed: {stderr_text or f'exit code {proc.returncode}'}")

        content = ""
        if response_file:
            try:
                with open(response_file, encoding="utf-8") as f:
                    content = f.read().strip()
            except OSError:
                content = ""
        if not content:
            content = stdout.decode("utf-8", errors="ignore").strip()
        if not content:
            raise AdapterError("kimi cli returned empty response")

        now = int(time.time())
        completion_tokens = _estimate_tokens(content)
        prompt_tokens = _estimate_tokens(prompt)
        response_model = str(payload.get("model", ""))

        return {
            "id": f"chatcmpl-kimi-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": now,
            "model": response_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    async def prepare_stream(self, payload: dict[str, Any], provider_config: dict[str, Any]) -> StreamHandle:
        cmd, prompt, env, use_stdin_prompt = self._build_command(payload, provider_config, stream=True)
        stdin = asyncio.subprocess.PIPE if use_stdin_prompt else None

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=stdin,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError as exc:
            raise AdapterError(f"kimi cli command not found: {cmd[0]}") from exc
        except OSError as exc:
            raise AdapterError(f"kimi cli process spawn failed: {exc}") from exc

        if use_stdin_prompt:
            if proc.stdin is None:
                raise AdapterError("kimi cli stdin unavailable in stdin mode")
            proc.stdin.write(prompt.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

        chat_id = f"chatcmpl-kimi-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        model = str(payload.get("model", ""))

        async def iterator() -> AsyncIterator[bytes]:
            yield self._to_sse(
                {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
            )

            assert proc.stdout is not None
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="ignore").rstrip("\r\n")
                if not text:
                    continue
                yield self._to_sse(
                    {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                    }
                )

            return_code = await proc.wait()
            if return_code != 0:
                stderr_text = ""
                if proc.stderr:
                    stderr_text = (await proc.stderr.read()).decode("utf-8", errors="ignore").strip()
                raise AdapterError(f"kimi stream failed: {stderr_text or f'exit code {return_code}'}")

            yield self._to_sse(
                {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
            )
            yield b"data: [DONE]\n\n"

        async def close() -> None:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()

        return StreamHandle(iterator=iterator(), close=close)

    def _build_command(
        self,
        payload: dict[str, Any],
        provider_config: dict[str, Any],
        stream: bool,
    ) -> tuple[list[str], str, dict[str, str], bool]:
        command = str(provider_config.get("command") or self.settings.kimi_cli_cmd)
        args = provider_config.get("args", ["chat"])
        if isinstance(args, str):
            args = [args]

        cmd = [command, *[str(item) for item in args]]

        upstream_model = provider_config.get("upstream_model")
        model_arg = provider_config.get("model_arg", "--model")
        if upstream_model and model_arg:
            cmd.extend([str(model_arg), str(upstream_model)])

        prompt = _messages_to_prompt(payload.get("messages", []))
        prompt_arg = provider_config.get("prompt_arg", "--prompt")
        use_stdin_prompt_config = bool(provider_config.get("use_stdin_prompt", True))
        force_stdin_prompt = bool(provider_config.get("force_stdin_prompt", False))
        stdin_prompt_arg = provider_config.get("stdin_prompt_arg")

        if stream:
            stream_arg = provider_config.get("stream_arg", "--stream")
            if stream_arg:
                if isinstance(stream_arg, list):
                    cmd.extend([str(item) for item in stream_arg])
                else:
                    cmd.append(str(stream_arg))

        extra_args = provider_config.get("extra_args", [])
        if isinstance(extra_args, list):
            cmd.extend([str(item) for item in extra_args])

        has_print = "--print" in cmd
        has_input_format = any(item == "--input-format" or item.startswith("--input-format=") for item in cmd)
        use_stdin_prompt = use_stdin_prompt_config and (has_print or force_stdin_prompt)
        if use_stdin_prompt and has_print and not has_input_format:
            cmd.extend(["--input-format", "text"])
        if use_stdin_prompt and stdin_prompt_arg is not None:
            if isinstance(stdin_prompt_arg, list):
                cmd.extend([str(item) for item in stdin_prompt_arg])
            else:
                cmd.append(str(stdin_prompt_arg))

        if not use_stdin_prompt:
            if prompt_arg in (None, ""):
                cmd.append(prompt)
            else:
                cmd.extend([str(prompt_arg), prompt])

        env = os.environ.copy()
        extra_env = provider_config.get("env", {})
        if isinstance(extra_env, dict):
            for k, v in extra_env.items():
                env[str(k)] = str(v)

        return cmd, prompt, env, use_stdin_prompt

    @staticmethod
    def _to_sse(data: dict[str, Any]) -> bytes:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
