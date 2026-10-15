import pytest

from apps.audit.models import AuditLog
from tests.conftest import client_for

pytestmark = pytest.mark.django_db


def test_login_me_logout_flow(entry_user):
    from rest_framework.test import APIClient
    c = APIClient(enforce_csrf_checks=True)
    token = c.get("/api/v1/auth/csrf/").json()["csrfToken"]
    r = c.post("/api/v1/auth/login/", {"username": "entry", "password": "a-strong-test-password"},
               format="json", HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 200, r.content
    assert r.json()["roles"] == ["Data entry officer"]
    assert r.json()["capabilities"] == ["enter_data"]
    me = c.get("/api/v1/auth/me/")
    assert me.json()["username"] == "entry"
    token = c.cookies["csrftoken"].value
    assert c.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert AuditLog.objects.filter(action="login", actor_label="entry").exists()
    assert AuditLog.objects.filter(action="logout", actor_label="entry").exists()


def test_bad_login_is_generic_and_audited(client, entry_user):
    r = client.post("/api/v1/auth/login/", {"username": "entry", "password": "wrong"}, format="json")
    assert r.status_code == 400
    assert r.json()["detail"] == "Incorrect username or password."
    assert AuditLog.objects.filter(action="login_failed", actor_label="entry").exists()


def test_login_requires_csrf_token(entry_user):
    from rest_framework.test import APIClient
    c = APIClient(enforce_csrf_checks=True)
    c.get("/api/v1/auth/csrf/")
    r = c.post("/api/v1/auth/login/", {"username": "entry", "password": "a-strong-test-password"}, format="json")
    assert r.status_code == 403


@pytest.mark.parametrize("url", ["/api/v1/admin/lgas/", "/api/v1/admin/audit-log/",
                                 "/api/v1/admin/data-sources/", "/api/v1/auth/me/"])
def test_admin_endpoints_reject_anonymous(client, url):
    assert client.get(url).status_code in (401, 403)


def test_role_matrix(entry_user, reviewer, administrator, plain_user):
    cases = {
        "/api/v1/admin/lgas/": {entry_user: 403, reviewer: 403, administrator: 200, plain_user: 403},
        "/api/v1/admin/audit-log/": {entry_user: 403, reviewer: 403, administrator: 200, plain_user: 403},
        "/api/v1/admin/data-sources/": {entry_user: 200, reviewer: 200, administrator: 200, plain_user: 403},
    }
    for url, expected in cases.items():
        for user, code in expected.items():
            assert client_for(user).get(url).status_code == code, (url, user.username)


def test_admin_cannot_hard_delete_reference_data(administrator):
    c = client_for(administrator)
    lga_id = c.get("/api/v1/admin/lgas/").json()["results"][0]["id"]
    assert c.delete(f"/api/v1/admin/lgas/{lga_id}/").status_code == 405


def test_admin_update_is_audited(administrator):
    c = client_for(administrator)
    com = c.get("/api/v1/admin/communities/", {"search": "Kaiama"}).json()["results"][0]
    r = c.patch(f"/api/v1/admin/communities/{com['id']}/",
                {"location": {"latitude": 5.08, "longitude": 6.30}, "location_source": "Field team GPS"},
                format="json")
    assert r.status_code == 200, r.content
    assert r.json()["location"] == {"latitude": 5.08, "longitude": 6.30}
    entry = AuditLog.objects.get(action="update", actor_label="admin1")
    assert "location" in entry.details["fields"]


def test_gps_outside_bayelsa_rejected_with_swap_hint(administrator):
    c = client_for(administrator)
    com = c.get("/api/v1/admin/communities/", {"search": "Kaiama"}).json()["results"][0]
    r = c.patch(f"/api/v1/admin/communities/{com['id']}/",
                {"location": {"latitude": 6.30, "longitude": 5.08}}, format="json")
    assert r.status_code == 400
    assert "swapped" in str(r.json()["location"])


def test_history_kept_for_reference_changes(administrator):
    from apps.geo.models import Community
    com = Community.objects.get(name="Sampou")
    com.description = "Updated"
    com.save()
    latest = com.history.first()
    assert latest.description == "Updated" and latest.history_type == "~"


def test_audit_log_is_append_only(administrator):
    entry = AuditLog.objects.create(action="export", actor_label="x")
    with pytest.raises(ValueError):
        entry.save()
    with pytest.raises(ValueError):
        entry.delete()
