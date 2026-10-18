import uuid

import pytest

pytestmark = pytest.mark.integration


async def test_upload_stores_the_text_not_the_file(client, make_user, upload_resume, db_scalar):
    user = await make_user()
    response = await upload_resume(user)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "parsed"
    assert body["character_count"] >= 50
    stored_length = await db_scalar(
        "SELECT length(raw_text) FROM resumes WHERE id = :i", i=uuid.UUID(body["resume_id"])
    )
    assert stored_length == body["character_count"]


async def test_upload_rejects_unsupported_file_type(client, make_user, upload_resume):
    user = await make_user()
    response = await upload_resume(user, filename="notes.txt")
    assert response.status_code == 400
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


async def test_upload_requires_authentication(client, upload_resume):
    response = await upload_resume({})
    assert response.status_code == 401


async def test_list_and_get_return_metadata_only(client, owner):
    listed = await client.get("/api/v1/resumes", headers=owner.headers)
    assert listed.status_code == 200
    items = listed.json()
    assert [item["resume_id"] for item in items] == [owner.resume_id]
    assert "raw_text" not in items[0]

    fetched = await client.get(f"/api/v1/resumes/{owner.resume_id}", headers=owner.headers)
    assert fetched.status_code == 200
    assert set(fetched.json()) == {"resume_id", "file_name", "file_type", "created_at"}


async def test_other_user_cannot_read_list_or_delete_my_resume(client, owner, make_user):
    bob = await make_user()
    url = f"/api/v1/resumes/{owner.resume_id}"

    read = await client.get(url, headers=bob)
    assert read.status_code == 404
    assert read.json()["error_code"] == "RESUME_NOT_FOUND"
    assert (await client.get("/api/v1/resumes", headers=bob)).json() == []
    assert (await client.delete(url, headers=bob)).status_code == 404
    # Bob's failed delete must not have removed the owner's resume.
    assert (await client.get(url, headers=owner.headers)).status_code == 200


async def test_owner_can_delete_the_resume(client, owner):
    url = f"/api/v1/resumes/{owner.resume_id}"
    assert (await client.delete(url, headers=owner.headers)).status_code == 204
    assert (await client.get(url, headers=owner.headers)).status_code == 404