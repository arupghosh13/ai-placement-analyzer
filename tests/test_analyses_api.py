import uuid

import pytest

pytestmark = pytest.mark.integration


async def test_create_analysis_returns_a_consistent_scorecard(client, owner, create_analysis):
    response = await create_analysis(owner.headers, owner.resume_id)
    assert response.status_code == 200
    body = response.json()
    metrics = body["metrics"]
    assert body["status"] == "completed"
    assert body["interview_preparation"] == []
    assert body["ai_insights_ready"] is False
    assert "python" in metrics["matched_skills"]
    assert "docker" in metrics["missing_skills"]
    matched, missing = len(metrics["matched_skills"]), len(metrics["missing_skills"])
    assert matched + missing == metrics["total_jd_skills"]
    assert metrics["match_percentage"] == round(matched / metrics["total_jd_skills"] * 100, 2)


async def test_stored_analysis_equals_the_one_returned_on_create(client, owner, create_analysis):
    created = (await create_analysis(owner.headers, owner.resume_id)).json()
    fetched = await client.get(f"/api/v1/analyses/{created['analysis_id']}", headers=owner.headers)
    assert fetched.status_code == 200
    assert fetched.json()["analysis_id"] == created["analysis_id"]
    assert fetched.json()["metrics"] == created["metrics"]


async def test_repeating_a_request_returns_the_same_analysis(
    client, owner, create_analysis, db_scalar
):
    first = await create_analysis(owner.headers, owner.resume_id)
    second = await create_analysis(owner.headers, owner.resume_id)
    assert second.status_code == 200
    assert second.json()["analysis_id"] == first.json()["analysis_id"]
    resume_id = uuid.UUID(owner.resume_id)
    assert await db_scalar("SELECT count(*) FROM analyses WHERE resume_id = :r", r=resume_id) == 1
    assert await db_scalar(
        "SELECT count(*) FROM job_descriptions jd "
        "JOIN resumes r ON r.user_id = jd.user_id WHERE r.id = :r",
        r=resume_id,
    ) == 1  # the duplicate's job description was rolled back


async def test_different_company_creates_a_new_analysis(client, owner, create_analysis):
    google = await create_analysis(owner.headers, owner.resume_id, company="Google")
    meta = await create_analysis(owner.headers, owner.resume_id, company="Meta")
    assert google.json()["analysis_id"] != meta.json()["analysis_id"]
    listed = await client.get("/api/v1/analyses", headers=owner.headers)
    assert [a["company_name"] for a in listed.json()] == ["Meta", "Google"]  # newest first


async def test_invalid_requests_are_rejected(client, owner, create_analysis):
    too_short = await create_analysis(owner.headers, owner.resume_id, jd_text="Python developer")
    assert too_short.status_code == 422
    blank = await create_analysis(owner.headers, owner.resume_id, jd_text=" " * 80)
    assert blank.status_code == 422
    unknown_resume = await create_analysis(owner.headers, str(uuid.uuid4()))
    assert unknown_resume.status_code == 404
    assert unknown_resume.json()["error_code"] == "RESUME_NOT_FOUND"


async def test_other_user_cannot_see_or_use_my_data(client, owner, make_user, create_analysis):
    created = (await create_analysis(owner.headers, owner.resume_id)).json()
    bob = await make_user()

    read = await client.get(f"/api/v1/analyses/{created['analysis_id']}", headers=bob)
    assert read.status_code == 404
    assert read.json()["error_code"] == "ANALYSIS_NOT_FOUND"
    assert (await client.get("/api/v1/analyses", headers=bob)).json() == []

    forbidden = await create_analysis(bob, owner.resume_id)
    assert forbidden.status_code == 404
    assert forbidden.json()["error_code"] == "RESUME_NOT_FOUND"


async def test_skill_rows_are_stored_and_cascade_with_the_resume(
    client, owner, create_analysis, db_scalar
):
    body = (await create_analysis(owner.headers, owner.resume_id)).json()
    analysis_id = uuid.UUID(body["analysis_id"])
    total = body["metrics"]["total_jd_skills"]

    matches = await db_scalar("SELECT count(*) FROM skill_matches WHERE analysis_id = :a", a=analysis_id)
    gaps = await db_scalar("SELECT count(*) FROM skill_gaps WHERE analysis_id = :a", a=analysis_id)
    assert matches + gaps == total
    jd_id = await db_scalar("SELECT job_description_id FROM analyses WHERE id = :a", a=analysis_id)

    deleted = await client.delete(f"/api/v1/resumes/{owner.resume_id}", headers=owner.headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/analyses/{analysis_id}", headers=owner.headers)).status_code == 404

    assert await db_scalar("SELECT count(*) FROM analyses WHERE id = :a", a=analysis_id) == 0
    assert await db_scalar("SELECT count(*) FROM skill_matches WHERE analysis_id = :a", a=analysis_id) == 0
    assert await db_scalar("SELECT count(*) FROM skill_gaps WHERE analysis_id = :a", a=analysis_id) == 0
    # The job description belongs to the user, not the resume, so it stays.
    assert await db_scalar("SELECT count(*) FROM job_descriptions WHERE id = :j", j=jd_id) == 1