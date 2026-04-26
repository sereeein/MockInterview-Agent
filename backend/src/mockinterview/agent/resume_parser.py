from io import BytesIO

import pdfplumber

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.resume_parse import (
    RESUME_PARSE_SYSTEM,
    RESUME_PARSE_USER_TEMPLATE,
)
from mockinterview.schemas.resume import ResumeStructured


class ResumeParseError(Exception):
    """Raised when a resume PDF cannot be parsed into structured fields."""


def extract_pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        raise ResumeParseError("PDF 内容为空")
    parts: list[str] = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text:
                    parts.append(text)
    except Exception as e:
        raise ResumeParseError(f"PDF 解析失败：{e}") from e
    return "\n\n".join(parts)


def parse_resume(pdf_bytes: bytes) -> ResumeStructured:
    text = extract_pdf_text(pdf_bytes)
    if not text.strip():
        raise ResumeParseError(
            "PDF 看似扫描件或图片，未能抽取文本。请上传文本版 PDF 或粘贴文本。"
        )
    system = build_cached_system([RESUME_PARSE_SYSTEM])
    user_msg = RESUME_PARSE_USER_TEMPLATE.replace("{resume_text}", text)
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user_msg}],
        max_tokens=4096,
    )
    return ResumeStructured.model_validate(payload)
