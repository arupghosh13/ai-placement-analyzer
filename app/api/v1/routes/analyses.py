"""Analysis endpoints. Orchestration only: rules live in AnalysisService."""
import uuid

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserId, get_analysis_service
from app.schemas.analysis import AnalysisResponse, AnalysisSummary, CreateAnalysisRequest
from app.schemas.analyze import SkillMatchMetrics
from app.services.analysis_service import AnalysisService, Scorecard

router = APIRouter(prefix="/analyses", tags=["Analyses"])


def _to_response(sc: Scorecard) -> AnalysisResponse:
    a = sc.analysis
    return AnalysisResponse(
        analysis_id=a.id,
        resume_id=a.resume_id,
        status=a.status,
        company_name=sc.job_description.company_name,
        role_title=sc.job_description.role_title,
        metrics=SkillMatchMetrics(
            match_percentage=a.match_score or 0.0,
            matched_skills=sc.matched_skills,
            missing_skills=sc.missing_skills,
            total_jd_skills=a.total_jd_skills,
            total_resume_skills=a.total_resume_skills,
        ),
        matcher_version=a.matcher_version,
        created_at=a.created_at,
    )


@router.post("", response_model=AnalysisResponse)
async def create_analysis(
    body: CreateAnalysisRequest,
    user_id: CurrentUserId,
    service: AnalysisService = Depends(get_analysis_service),
):
    scorecard = await service.create(
        user_id,
        resume_id=body.resume_id,
        jd_text=body.jd_text,
        company_name=body.company_name,
        role_title=body.role_title,
    )
    return _to_response(scorecard)


@router.get("", response_model=list[AnalysisSummary])
async def list_analyses(
    user_id: CurrentUserId,
    service: AnalysisService = Depends(get_analysis_service),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    rows = await service.list_analyses(user_id, limit=limit, offset=offset)
    return [
        AnalysisSummary(
            analysis_id=a.id,
            resume_id=a.resume_id,
            company_name=jd.company_name,
            role_title=jd.role_title,
            match_percentage=a.match_score,
            status=a.status,
            created_at=a.created_at,
        )
        for a, jd in rows
    ]


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: uuid.UUID,
    user_id: CurrentUserId,
    service: AnalysisService = Depends(get_analysis_service),
):
    return _to_response(await service.get(user_id, analysis_id))