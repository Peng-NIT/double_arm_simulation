"""Render course-scoped LLM explanations with answer-me-with-html."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AM_CLI = ROOT / "third_party" / "answer-me-with-html" / "am.mjs"
MIN_NODE_MAJOR = 20


def _normalize_fences(markdown: str) -> str:
    """Remove outer wrappers and downgrade accidental fenced blocks to safe lists."""
    text = markdown.strip()
    lines = text.splitlines()
    if lines and re.fullmatch(r"\s*```(?:markdown|md)\s*", lines[0], re.IGNORECASE):
        original_fences = sum(bool(re.fullmatch(r"\s*```[^`]*", line)) for line in lines)
        lines = lines[1:]
        # A balanced original count means the model also emitted an outer closing fence.
        if original_fences % 2 == 0 and lines and re.fullmatch(r"\s*```\s*", lines[-1]):
            lines = lines[:-1]

    normalized: list[str] = []
    in_fence = False
    for line in lines:
        if re.fullmatch(r"\s*```[^`]*", line):
            if not in_fence:
                normalized.extend(["", "**过程与关系**"])
            in_fence = not in_fence
            continue
        if in_fence:
            content = line.strip()
            if content:
                normalized.append(f"- {content}")
        else:
            normalized.append(line)
    return "\n".join(normalized).strip()


def _node_major() -> int:
    try:
        result = subprocess.run(
            ["node", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise RuntimeError("服务器未安装 Node.js，无法生成可视化解释。") from exc
    match = re.search(r"v?(\d+)", result.stdout)
    if not match:
        raise RuntimeError("无法识别服务器的 Node.js 版本。")
    return int(match.group(1))


def _validate_draft(markdown: str) -> None:
    """Reject active or externally loaded content before it reaches the renderer."""
    forbidden = [
        r"```\s*(?:html|svg)\b",
        r"<\s*/?\s*(?:script|iframe|object|embed|link|style)\b",
        r"javascript\s*:",
        r"(?:src|href)\s*=",
        r"!\[[^]]*\]\(",
    ]
    if any(re.search(pattern, markdown, flags=re.IGNORECASE) for pattern in forbidden):
        raise ValueError("模型返回了不允许的 HTML、脚本或外部资源，请重试。")
    if len(markdown) > 24_000:
        raise ValueError("可视化解释过长，请重试。")


def render_explanation(markdown: str) -> str:
    """Return a self-contained HTML page; no server or browser process is started."""
    markdown = _normalize_fences(markdown)
    _validate_draft(markdown)
    if not AM_CLI.is_file():
        raise RuntimeError("项目中缺少 answer-me-with-html 渲染工具。")
    major = _node_major()
    if major < MIN_NODE_MAJOR:
        raise RuntimeError(
            f"服务器 Node.js 版本为 {major}，可视化解释需要 Node.js {MIN_NODE_MAJOR} 或更高版本。"
        )

    with tempfile.TemporaryDirectory(prefix="arm-lab-explain-") as temp_dir:
        temp = Path(temp_dir)
        source = temp / "explanation.md"
        output = temp / "explanation.html"
        source.write_text(markdown, encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    "node",
                    str(AM_CLI),
                    "render",
                    str(source),
                    "-o",
                    str(output),
                    "--no-open",
                    "--theme",
                    "blueprint",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=25,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("可视化页面生成超时，请稍后重试。") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "未知错误").strip().splitlines()[-1]
            raise RuntimeError(f"可视化页面生成失败：{detail}") from exc
        if not output.is_file():
            raise RuntimeError("渲染工具未生成 HTML 文件。")
        return output.read_text(encoding="utf-8")
