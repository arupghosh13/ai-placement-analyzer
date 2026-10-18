"""Resume endpoints. Orchestration only: rules live in ResumeService."""
import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.api.deps import CurrentUserId, get_resume_service
from app.models import Resume
from app.schemas.resume import ResumeResponse, ResumeUploadResponse
from app.services.extractor import MAX_FILE_SIZE_BYTES
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["Resumes"])


def _to_response(resume: Resume) -> ResumeResponse:
    return ResumeResponse(
        resume_id=resume.id,
        file_name=resume.filename,
        file_type=resume.file_type,
        created_at=resume.created_at,
    )


@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(
    user_id: CurrentUserId,
    resume_file: UploadFile = File(...),
    service: ResumeService = Depends(get_resume_service),
):
    # Read at most 1 byte over the limit: enough for the extractor to reject
    # an oversized file, without loading a huge file into memory.
    file_bytes = await resume_file.read(MAX_FILE_SIZE_BYTES + 1)
    resume, character_count = await service.upload(
        user_id, file_bytes, resume_file.filename or ""
    )
    return ResumeUploadResponse(
        resume_id=resume.id, file_name=resume.filename, character_count=character_count
    )


@router.get("", response_model=list[ResumeResponse])
async def list_resumes(
    user_id: CurrentUserId,
    service: ResumeService = Depends(get_resume_service),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    resumes = await service.list_resumes(user_id, limit=limit, offset=offset)
    return [_to_response(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    user_id: CurrentUserId,
    service: ResumeService = Depends(get_resume_service),
):
    return _to_response(await service.get(user_id, resume_id))


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: uuid.UUID,
    user_id: CurrentUserId,
    service: ResumeService = Depends(get_resume_service),
):
    await service.delete(user_id, resume_id)
    return Response(status_code=204)