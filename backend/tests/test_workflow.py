import pytest

from apps.governance.models import ApprovalRecord, Status
from apps.governance.workflow import WorkflowError, available_actions, perform
from tests.testapp.models import SampleRecord

pytestmark = pytest.mark.django_db


@pytest.fixture
def record(entry_user):
    return SampleRecord.objects.create(title="Fish market, Swali", created_by=entry_user)


def test_happy_path_publishes(record, entry_user, reviewer):
    perform(record, "submit", entry_user)
    record = perform(record, "approve", reviewer)
    assert record.status == Status.APPROVED and record.approved_by == reviewer
    assert record.approved_at is not None
    assert SampleRecord.objects.published().count() == 1
    assert list(ApprovalRecord.objects.values_list("action", flat=True)) == ["approve", "submit"]


def test_drafts_are_not_published(record):
    assert SampleRecord.objects.published().count() == 0


def test_data_entry_cannot_approve(record, entry_user):
    perform(record, "submit", entry_user)
    with pytest.raises(WorkflowError, match="permission"):
        perform(record, "approve", entry_user)


def test_maker_checker_blocks_self_approval(reviewer, reviewer2):
    rec = SampleRecord.objects.create(title="Jetty", created_by=reviewer)
    perform(rec, "submit", reviewer)
    assert "approve" not in available_actions(rec, reviewer)
    with pytest.raises(WorkflowError, match="Another reviewer"):
        perform(rec, "approve", reviewer)
    assert perform(rec, "approve", reviewer2).status == Status.APPROVED


def test_self_approval_can_be_enabled(settings, reviewer):
    settings.ALLOW_SELF_APPROVAL = True
    rec = SampleRecord.objects.create(title="Jetty", created_by=reviewer)
    perform(rec, "submit", reviewer)
    assert perform(rec, "approve", reviewer).status == Status.APPROVED


def test_return_requires_reason_and_allows_resubmission(record, entry_user, reviewer):
    perform(record, "submit", entry_user)
    with pytest.raises(WorkflowError, match="reason"):
        perform(record, "return", reviewer, comment="  ")
    perform(record, "return", reviewer, comment="GPS point is in the river")
    assert perform(record, "submit", entry_user).status == Status.SUBMITTED


def test_invalid_transition(record, reviewer):
    with pytest.raises(WorkflowError, match="Cannot approve"):
        perform(record, "approve", reviewer)


def test_only_administrator_archives(record, entry_user, reviewer, reviewer2, administrator):
    perform(record, "submit", entry_user)
    perform(record, "approve", reviewer)
    with pytest.raises(WorkflowError):
        perform(record, "archive", reviewer2, comment="old")
    rec = perform(record, "archive", administrator, comment="Enterprise closed")
    assert rec.status == Status.ARCHIVED and rec.archived_reason == "Enterprise closed"


def test_transitions_are_audited(record, entry_user, reviewer):
    from apps.audit.models import AuditLog
    perform(record, "submit", entry_user)
    perform(record, "return", reviewer, comment="Missing source")
    log = AuditLog.objects.get(action="return")
    assert log.details == {"from": "submitted", "to": "returned", "comment": "Missing source"}
    assert log.target_label == "Fish market, Swali"
