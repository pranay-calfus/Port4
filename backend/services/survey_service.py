"""Business logic for Product & CX-authored surveys: CRUD, publish state,
the customer-facing active-surveys feed, response submission, and the
filtered queries + analytics backing the Product & CX dashboard. Mirrors
feedback_service.py's style - plain dicts over the Supabase client, no ORM
session.
"""

from supabase import Client

from backend.services.ticket_service import _end_of_day, _maybe_single


def _tally(values: list, key=lambda v: v) -> dict:
    counts: dict = {}
    for value in values:
        k = key(value)
        if k is None:
            continue
        counts[k] = counts.get(k, 0) + 1
    return counts


# --- Survey management ----------------------------------------------------


def _replace_questions(client: Client, survey_id: int, questions: list) -> None:
    """Deletes the survey's existing questions and inserts the new set -
    "edit" is a full replace, not a diff, per the accepted v1 scope (see the
    plan) - simpler than reconciling existing answers against renamed/
    retyped/removed questions.
    """
    client.table("survey_questions").delete().eq("survey_id", survey_id).execute()
    rows = [
        {
            "survey_id": survey_id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "position": index,
            "required": q.required,
        }
        for index, q in enumerate(questions)
    ]
    if rows:
        client.table("survey_questions").insert(rows).execute()


def create_survey(client: Client, admin: dict, *, title: str, description: str | None, questions: list) -> dict:
    survey = (
        client.table("surveys")
        .insert({"title": title, "description": description, "created_by": admin["id"]})
        .execute()
        .data[0]
    )
    _replace_questions(client, survey["id"], questions)
    return get_survey(client, survey["id"])


def update_survey(
    client: Client, survey_id: int, *, title: str, description: str | None, questions: list
) -> dict:
    client.table("surveys").update({"title": title, "description": description}).eq(
        "id", survey_id
    ).execute()
    _replace_questions(client, survey_id, questions)
    return get_survey(client, survey_id)


def delete_survey(client: Client, survey_id: int) -> None:
    client.table("surveys").delete().eq("id", survey_id).execute()


def set_published(client: Client, survey_id: int, is_published: bool) -> dict:
    client.table("surveys").update({"is_published": is_published}).eq("id", survey_id).execute()
    return get_survey(client, survey_id)


def _questions_for(client: Client, survey_id: int) -> list[dict]:
    return (
        client.table("survey_questions")
        .select("*")
        .eq("survey_id", survey_id)
        .order("position")
        .execute()
        .data
    )


def _response_count(client: Client, survey_id: int) -> int:
    rows = client.table("survey_responses").select("id").eq("survey_id", survey_id).execute().data
    return len(rows)


def get_survey(client: Client, survey_id: int) -> dict | None:
    survey = _maybe_single(client.table("surveys").select("*").eq("id", survey_id))
    if survey is None:
        return None
    return {
        **survey,
        "questions": _questions_for(client, survey_id),
        "response_count": _response_count(client, survey_id),
    }


def list_surveys(client: Client) -> list[dict]:
    surveys = client.table("surveys").select("*").order("created_at", desc=True).execute().data
    return [{**s, "response_count": _response_count(client, s["id"])} for s in surveys]


# --- Customer-facing: active surveys + submission --------------------------


def list_active_surveys_for_user(client: Client, user_id: int) -> list[dict]:
    """Published surveys this user hasn't responded to yet - the widget's
    feed. A user "no longer sees" a survey the instant they submit it
    (their own response now exists), which is what "prevent duplicate
    submissions" requires at the UI level too, not just the API's 409.
    """
    answered = client.table("survey_responses").select("survey_id").eq("user_id", user_id).execute().data
    answered_ids = {row["survey_id"] for row in answered}
    published = (
        client.table("surveys")
        .select("*")
        .eq("is_published", True)
        .order("created_at")
        .execute()
        .data
    )
    active = [s for s in published if s["id"] not in answered_ids]
    return [{**s, "questions": _questions_for(client, s["id"])} for s in active]


def _validate_answer_shape(question: dict, value) -> None:
    qtype = question["question_type"]
    label = question["question_text"]
    if qtype in ("short_text", "long_text"):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'"{label}" expects a non-empty text answer')
    elif qtype == "rating":
        if not isinstance(value, int) or isinstance(value, bool) or not (1 <= value <= 5):
            raise ValueError(f'"{label}" expects a rating between 1 and 5')
    elif qtype == "single_choice":
        if not isinstance(value, str) or value not in (question["options"] or []):
            raise ValueError(f'"{label}" expects one of its listed options')
    elif qtype == "multiple_choice":
        options = question["options"] or []
        if not isinstance(value, list) or not value or any(v not in options for v in value):
            raise ValueError(f'"{label}" expects a non-empty subset of its listed options')


def submit_response(client: Client, survey: dict, user: dict, answers: list) -> dict:
    """Validates one answer per required question and each answer's shape
    against its question's question_type, then inserts the response and
    its answers. `survey` must be the full detail dict from get_survey
    (i.e. includes `questions`). Raises ValueError - which the router turns
    into a 4xx - on any validation failure or a duplicate submission,
    mirroring ticket_service.create_user's pre-check-then-insert pattern
    rather than catching the DB's own unique-constraint violation.
    """
    existing = (
        client.table("survey_responses")
        .select("id")
        .eq("survey_id", survey["id"])
        .eq("user_id", user["id"])
        .execute()
    )
    if existing.data:
        raise ValueError("You have already submitted a response to this survey")

    questions_by_id = {q["id"]: q for q in survey["questions"]}
    answers_by_question = {a.question_id: a.value for a in answers}

    for question in survey["questions"]:
        if question["required"] and question["id"] not in answers_by_question:
            raise ValueError(f'Missing required answer for "{question["question_text"]}"')

    for answer in answers:
        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise ValueError(f"Question {answer.question_id} does not belong to this survey")
        _validate_answer_shape(question, answer.value)

    response = (
        client.table("survey_responses")
        .insert({"survey_id": survey["id"], "user_id": user["id"]})
        .execute()
        .data[0]
    )
    answer_rows = [
        {"response_id": response["id"], "question_id": a.question_id, "value": a.value}
        for a in answers
    ]
    client.table("survey_answers").insert(answer_rows).execute()
    return get_response(client, response["id"])


def get_response(client: Client, response_id: int) -> dict | None:
    response = _maybe_single(client.table("survey_responses").select("*").eq("id", response_id))
    if response is None:
        return None
    answers = (
        client.table("survey_answers").select("*").eq("response_id", response_id).execute().data
    )
    user = _maybe_single(client.table("users").select("*").eq("id", response["user_id"]))
    return {**response, "answers": answers, "user": user}


# --- Dashboard: filtered responses + analytics ------------------------------


def list_responses(
    client: Client,
    *,
    survey_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    rating: int | None = None,
    question_id: int | None = None,
    user_id: int | None = None,
) -> list[dict]:
    query = client.table("survey_responses").select("*")
    if survey_id is not None:
        query = query.eq("survey_id", survey_id)
    if user_id is not None:
        query = query.eq("user_id", user_id)
    if date_from:
        query = query.gte("submitted_at", date_from)
    if date_to:
        query = query.lte("submitted_at", _end_of_day(date_to))
    query = query.order("submitted_at", desc=True).order("id", desc=True)
    responses = query.execute().data

    response_ids = [r["id"] for r in responses]
    if not response_ids:
        return []

    answers = client.table("survey_answers").select("*").in_("response_id", response_ids).execute().data
    answers_by_response: dict[int, list[dict]] = {}
    for a in answers:
        answers_by_response.setdefault(a["response_id"], []).append(a)

    # Rating/question filters apply at the answer level - done in Python
    # rather than a PostgREST join, since these are small per-survey
    # datasets and the shape of `value` (JSON) varies by question type.
    if question_id is not None or rating is not None:
        keep_ids = set()
        for a in answers:
            if question_id is not None and a["question_id"] != question_id:
                continue
            if rating is not None and a["value"] != rating:
                continue
            keep_ids.add(a["response_id"])
        responses = [r for r in responses if r["id"] in keep_ids]

    user_ids = {r["user_id"] for r in responses}
    users_by_id = {}
    if user_ids:
        rows = client.table("users").select("*").in_("id", list(user_ids)).execute().data
        users_by_id = {u["id"]: u for u in rows}

    return [
        {**r, "answers": answers_by_response.get(r["id"], []), "user": users_by_id.get(r["user_id"])}
        for r in responses
    ]


def survey_analytics(
    client: Client, survey_id: int, *, date_from: str | None = None, date_to: str | None = None
) -> dict:
    questions = _questions_for(client, survey_id)
    query = client.table("survey_responses").select("id").eq("survey_id", survey_id)
    if date_from:
        query = query.gte("submitted_at", date_from)
    if date_to:
        query = query.lte("submitted_at", _end_of_day(date_to))
    response_ids = [r["id"] for r in query.execute().data]
    answers = (
        client.table("survey_answers").select("*").in_("response_id", response_ids).execute().data
        if response_ids
        else []
    )
    answers_by_question: dict[int, list] = {}
    for a in answers:
        answers_by_question.setdefault(a["question_id"], []).append(a["value"])

    per_question = []
    for q in questions:
        values = answers_by_question.get(q["id"], [])
        entry = {
            "question_id": q["id"],
            "question_text": q["question_text"],
            "question_type": q["question_type"],
            "response_count": len(values),
            "average_rating": None,
            "rating_distribution": {},
            "most_common_answers": [],
        }
        if q["question_type"] == "rating":
            numeric = [v for v in values if isinstance(v, int) and not isinstance(v, bool)]
            entry["average_rating"] = sum(numeric) / len(numeric) if numeric else None
            entry["rating_distribution"] = _tally(numeric)
        else:
            flat = []
            for v in values:
                flat.extend(v) if isinstance(v, list) else flat.append(v)
            ranked = sorted(_tally(flat).items(), key=lambda kv: kv[1], reverse=True)[:10]
            entry["most_common_answers"] = [{"answer": a, "count": n} for a, n in ranked]
        per_question.append(entry)

    return {
        "survey_id": survey_id,
        "total_responses": len(response_ids),
        "questions": per_question,
    }
