from backend.models import Role
from backend.services import ticket_service


def _register_and_login(client, email="alice@example.com"):
    client.post("/auth/register", json={"name": "Alice", "email": email, "password": "password123"})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_login(client, db_session, email="admin@example.com", department=None, role=Role.ADMIN):
    ticket_service.create_user(
        db_session, name="Admin", email=email, password="adminpass1", role=role, department=department
    )
    login_path = "/product-cx/login" if role == Role.PRODUCT_CX else "/admin/login"
    login = client.post(login_path, json={"email": email, "password": "adminpass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _all_types_payload():
    return {
        "title": "Product Feedback Survey",
        "description": "A quick survey.",
        "questions": [
            {"question_text": "What do you think?", "question_type": "short_text", "required": True},
            {"question_text": "Tell us more.", "question_type": "long_text", "required": False},
            {"question_text": "Rate us", "question_type": "rating", "required": True},
            {
                "question_text": "Pick one",
                "question_type": "single_choice",
                "options": ["A", "B", "C"],
                "required": True,
            },
            {
                "question_text": "Pick many",
                "question_type": "multiple_choice",
                "options": ["X", "Y", "Z"],
                "required": False,
            },
        ],
    }


def test_product_cx_can_create_and_publish_survey(client, db_session):
    headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    response = client.post("/surveys", headers=headers, json=_all_types_payload())
    assert response.status_code == 201
    survey = response.json()
    assert survey["is_published"] is False
    assert len(survey["questions"]) == 5

    publish = client.patch(f"/surveys/{survey['id']}/publish", headers=headers)
    assert publish.status_code == 200
    assert publish.json()["is_published"] is True

    unpublish = client.patch(f"/surveys/{survey['id']}/unpublish", headers=headers)
    assert unpublish.json()["is_published"] is False


def test_super_admin_can_manage_surveys(client, db_session):
    headers = _admin_login(client, db_session, email="super@example.com")
    response = client.post("/surveys", headers=headers, json=_all_types_payload())
    assert response.status_code == 201


def test_department_scoped_admin_cannot_manage_surveys(client, db_session):
    headers = _admin_login(client, db_session, department="Billing Team")
    response = client.post("/surveys", headers=headers, json=_all_types_payload())
    assert response.status_code == 403


def test_editing_survey_replaces_questions(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()

    updated_payload = {
        "title": "Updated Survey",
        "description": None,
        "questions": [
            {"question_text": "Only question now", "question_type": "short_text", "required": True}
        ],
    }
    response = client.patch(f"/surveys/{survey['id']}", headers=admin_headers, json=updated_payload)
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated Survey"
    assert len(updated["questions"]) == 1


def test_deleting_survey_removes_it(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()

    delete_response = client.delete(f"/surveys/{survey['id']}", headers=admin_headers)
    assert delete_response.status_code == 204
    assert client.get(f"/surveys/{survey['id']}", headers=admin_headers).status_code == 404


def test_active_surveys_excludes_unpublished_and_answered(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()

    user_headers = _register_and_login(client)
    assert client.get("/surveys/active", headers=user_headers).json() == []

    client.patch(f"/surveys/{survey['id']}/publish", headers=admin_headers)
    active = client.get("/surveys/active", headers=user_headers).json()
    assert [s["id"] for s in active] == [survey["id"]]

    questions_by_type = {q["question_type"]: q for q in active[0]["questions"]}
    answers = [
        {"question_id": questions_by_type["short_text"]["id"], "value": "Great app"},
        {"question_id": questions_by_type["rating"]["id"], "value": 5},
        {"question_id": questions_by_type["single_choice"]["id"], "value": "A"},
    ]
    submit = client.post(
        f"/surveys/{survey['id']}/responses", headers=user_headers, json={"answers": answers}
    )
    assert submit.status_code == 201

    assert client.get("/surveys/active", headers=user_headers).json() == []


def test_duplicate_submission_returns_409(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()
    client.patch(f"/surveys/{survey['id']}/publish", headers=admin_headers)

    user_headers = _register_and_login(client)
    questions_by_type = {q["question_type"]: q for q in survey["questions"]}
    answers = [
        {"question_id": questions_by_type["short_text"]["id"], "value": "Great app"},
        {"question_id": questions_by_type["rating"]["id"], "value": 4},
        {"question_id": questions_by_type["single_choice"]["id"], "value": "B"},
    ]
    body = {"answers": answers}
    first = client.post(f"/surveys/{survey['id']}/responses", headers=user_headers, json=body)
    assert first.status_code == 201

    second = client.post(f"/surveys/{survey['id']}/responses", headers=user_headers, json=body)
    assert second.status_code == 409


def test_missing_required_answer_is_rejected(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()
    client.patch(f"/surveys/{survey['id']}/publish", headers=admin_headers)
    questions_by_type = {q["question_type"]: q for q in survey["questions"]}

    user_headers = _register_and_login(client)
    # "rating" and "single_choice" are also required but omitted here -
    # only the (also-required) short_text question is answered.
    answers = [{"question_id": questions_by_type["short_text"]["id"], "value": "Great app"}]
    response = client.post(
        f"/surveys/{survey['id']}/responses", headers=user_headers, json={"answers": answers}
    )
    assert response.status_code == 409


def test_survey_analytics_shape(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()
    client.patch(f"/surveys/{survey['id']}/publish", headers=admin_headers)
    questions_by_type = {q["question_type"]: q for q in survey["questions"]}

    for i in range(2):
        user_headers = _register_and_login(client, email=f"user{i}@example.com")
        answers = [
            {"question_id": questions_by_type["short_text"]["id"], "value": "Nice"},
            {"question_id": questions_by_type["rating"]["id"], "value": 5},
            {"question_id": questions_by_type["single_choice"]["id"], "value": "A"},
        ]
        client.post(f"/surveys/{survey['id']}/responses", headers=user_headers, json={"answers": answers})

    analytics = client.get(f"/surveys/{survey['id']}/analytics", headers=admin_headers).json()
    assert analytics["total_responses"] == 2

    by_type = {q["question_type"]: q for q in analytics["questions"]}
    rating_q = by_type["rating"]
    assert rating_q["response_count"] == 2
    assert rating_q["average_rating"] == 5.0
    assert rating_q["rating_distribution"] == {"5": 2}

    choice_q = by_type["single_choice"]
    assert choice_q["most_common_answers"] == [{"answer": "A", "count": 2}]


def test_dashboard_responses_filter_by_survey_and_rating(client, db_session):
    admin_headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    survey = client.post("/surveys", headers=admin_headers, json=_all_types_payload()).json()
    client.patch(f"/surveys/{survey['id']}/publish", headers=admin_headers)
    questions_by_type = {q["question_type"]: q for q in survey["questions"]}

    user_headers = _register_and_login(client)
    answers = [
        {"question_id": questions_by_type["short_text"]["id"], "value": "Nice"},
        {"question_id": questions_by_type["rating"]["id"], "value": 3},
        {"question_id": questions_by_type["single_choice"]["id"], "value": "B"},
    ]
    client.post(f"/surveys/{survey['id']}/responses", headers=user_headers, json={"answers": answers})

    matching = client.get(
        "/surveys/responses", headers=admin_headers, params={"survey_id": survey["id"], "rating": 3}
    )
    assert len(matching.json()) == 1

    non_matching = client.get(
        "/surveys/responses", headers=admin_headers, params={"survey_id": survey["id"], "rating": 5}
    )
    assert non_matching.json() == []
