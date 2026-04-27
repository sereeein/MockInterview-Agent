from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from mockinterview.agent.resume_parser import ResumeParseError, parse_resume
from mockinterview.config import get_settings
from mockinterview.db.models import ResumeSession
from mockinterview.db.session import get_session
from mockinterview.routes._deps import use_provider

router = APIRouter(prefix="/resume", tags=["resume"])

ALLOWED_ROLES = {"pm", "data", "ai", "other"}


@router.post("")
def upload_resume(
    file: UploadFile = File(...),
    role_type: str = Form(...),
    jd_text: str | None = Form(None),
    company_name: str | None = Form(None),
    db: Session = Depends(get_session),
    _: None = Depends(use_provider),
) -> dict:
    if role_type not in ALLOWED_ROLES:
        raise HTTPException(400, f"role_type must be one of {ALLOWED_ROLES}")
    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(400, "empty file")
    try:
        parsed = parse_resume(pdf_bytes)
    except ResumeParseError as e:
        raise HTTPException(400, str(e)) from e
    rs = ResumeSession(
        user_id=get_settings().seed_user_id,
        resume_json=parsed.model_dump(),
        jd_text=jd_text,
        company_name=company_name,
        role_type=role_type,
    )
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return {
        "id": rs.id,
        "role_type": rs.role_type,
        "resume_json": rs.resume_json,
        "jd_text": rs.jd_text,
        "company_name": rs.company_name,
    }
