import pytest

from ticket_router import db
from ticket_router.models import ASSIGNED_TEAMS


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    db.init_db(db_path=path)
    return path


def test_init_db_seeds_teams_from_assigned_teams(db_path):
    assert sorted(db.list_teams(db_path=db_path)) == sorted(ASSIGNED_TEAMS)


def test_init_db_is_idempotent(db_path):
    db.init_db(db_path=db_path)
    assert sorted(db.list_teams(db_path=db_path)) == sorted(ASSIGNED_TEAMS)


def test_add_ticket_stores_ai_and_final_priority_independently(db_path):
    ticket_id = db.add_ticket(
        message="My invoice is wrong",
        category="Billing",
        ai_priority="High",
        final_priority="Medium",
        assigned_team="Billing Team",
        reasoning="Billing discrepancy reported",
        confidence=0.9,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    tickets = db.list_tickets_for_team("Billing Team", db_path=db_path)
    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["id"] == ticket_id
    assert ticket["ai_priority"] == "High"
    assert ticket["final_priority"] == "Medium"
    assert ticket["ai_assigned_team"] == "Billing Team"
    assert ticket["assigned_team"] == "Billing Team"
    assert ticket["status"] == "Pending"


def test_set_final_priority_overrides_without_touching_ai_priority(db_path):
    ticket_id = db.add_ticket(
        message="App crashes on launch",
        category="Bug Report",
        ai_priority="Low",
        final_priority="Low",
        assigned_team="Engineering",
        reasoning="Crash report",
        confidence=0.8,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.set_final_priority(ticket_id, "High", db_path=db_path)

    ticket = db.list_tickets_for_team("Engineering", db_path=db_path)[0]
    assert ticket["final_priority"] == "High"
    assert ticket["ai_priority"] == "Low"


def test_reassign_team_moves_ticket_between_teams(db_path):
    ticket_id = db.add_ticket(
        message="Can't log in",
        category="Account Access",
        ai_priority="High",
        final_priority="High",
        assigned_team="Support Team",
        reasoning="Login failure",
        confidence=0.85,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.reassign_team(ticket_id, "Engineering", db_path=db_path)

    assert db.list_tickets_for_team("Support Team", db_path=db_path) == []
    reassigned = db.list_tickets_for_team("Engineering", db_path=db_path)
    assert len(reassigned) == 1
    assert reassigned[0]["id"] == ticket_id
    assert reassigned[0]["assigned_team"] == "Engineering"
    assert reassigned[0]["ai_assigned_team"] == "Support Team"


def test_set_status_updates_status(db_path):
    ticket_id = db.add_ticket(
        message="Feature idea",
        category="Feature Request",
        ai_priority="Low",
        final_priority="Low",
        assigned_team="Sales Team",
        reasoning="Feature suggestion",
        confidence=0.7,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.set_status(ticket_id, "Closed", db_path=db_path)

    ticket = db.list_tickets_for_team("Sales Team", db_path=db_path)[0]
    assert ticket["status"] == "Closed"


def test_list_tickets_for_team_sorts_by_priority_high_to_low(db_path):
    for priority in ("Low", "High", "Medium"):
        db.add_ticket(
            message=f"{priority} priority ticket",
            category="General Inquiry",
            ai_priority=priority,
            final_priority=priority,
            assigned_team="Customer Success",
            reasoning="Test ticket",
            confidence=0.6,
            model_used="gpt-4o-mini",
            db_path=db_path,
        )

    tickets = db.list_tickets_for_team("Customer Success", db_path=db_path)
    assert [t["final_priority"] for t in tickets] == ["High", "Medium", "Low"]


def test_list_all_tickets_returns_every_ticket_pending_first(db_path):
    high_pending = db.add_ticket(
        message="High priority, still open",
        category="Security",
        ai_priority="High",
        final_priority="High",
        assigned_team="Security Team",
        reasoning="Security concern",
        confidence=0.9,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    low_closed = db.add_ticket(
        message="Low priority, already resolved",
        category="Feature Request",
        ai_priority="Low",
        final_priority="Low",
        assigned_team="Engineering",
        reasoning="Feature suggestion",
        confidence=0.7,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.set_status(low_closed, "Closed", db_path=db_path)

    all_tickets = db.list_all_tickets(db_path=db_path)
    assert [t["id"] for t in all_tickets] == [high_pending, low_closed]
    assert all_tickets[0]["status"] == "Pending"
    assert all_tickets[1]["status"] == "Closed"


def test_count_by_status_counts_pending_and_closed_per_team(db_path):
    open_id = db.add_ticket(
        message="Still open",
        category="Technical Support",
        ai_priority="Medium",
        final_priority="Medium",
        assigned_team="QA",
        reasoning="Open issue",
        confidence=0.75,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    closed_id = db.add_ticket(
        message="Already resolved",
        category="Technical Support",
        ai_priority="Low",
        final_priority="Low",
        assigned_team="QA",
        reasoning="Resolved issue",
        confidence=0.75,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.set_status(closed_id, "Closed", db_path=db_path)

    counts = db.count_by_status("QA", db_path=db_path)
    assert counts == {"Pending": 1, "Closed": 1}
    assert open_id != closed_id


def test_pending_counts_by_team_only_counts_pending_and_omits_untouched_teams(db_path):
    pending_id = db.add_ticket(
        message="Needs attention",
        category="Sales",
        ai_priority="Medium",
        final_priority="Medium",
        assigned_team="Sales Team",
        reasoning="Pricing question",
        confidence=0.8,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    closed_id = db.add_ticket(
        message="Already handled",
        category="Sales",
        ai_priority="Low",
        final_priority="Low",
        assigned_team="Sales Team",
        reasoning="Pricing question",
        confidence=0.8,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.set_status(closed_id, "Closed", db_path=db_path)

    counts = db.pending_counts_by_team(db_path=db_path)
    assert counts == {"Sales Team": 1}
    assert "Logistics" not in counts
    assert pending_id != closed_id


def test_delete_ticket_removes_it_permanently(db_path):
    ticket_id = db.add_ticket(
        message="To be deleted",
        category="Other",
        ai_priority="Low",
        final_priority="Low",
        assigned_team="Customer Success",
        reasoning="Test ticket",
        confidence=0.5,
        model_used="gpt-4o-mini",
        db_path=db_path,
    )
    db.delete_ticket(ticket_id, db_path=db_path)

    assert db.list_tickets_for_team("Customer Success", db_path=db_path) == []
    assert db.list_all_tickets(db_path=db_path) == []
