"""ntfy.sh értesítő – endpoint, formátum, kapuzás, best-effort hibakezelés."""

from meccsjoslo.notify import Notifier, make_notifier, notify_started, notify_tip
from meccsjoslo.tipply.state import Score


def _recorder():
    calls = []

    def transport(endpoint, data, headers):
        calls.append((endpoint, data.decode("utf-8"), headers))
        return 200

    return calls, transport


def test_notifier_posts_to_topic_endpoint():
    calls, transport = _recorder()
    n = Notifier("https://ntfy.sh", "gergo_vb2026_tippek", transport=transport)
    assert n.send("hello", title="X", tags="rocket") is True
    endpoint, body, headers = calls[0]
    assert endpoint == "https://ntfy.sh/gergo_vb2026_tippek"
    assert body == "hello"
    assert headers["Title"] == "X" and headers["Tags"] == "rocket"


def test_notifier_send_never_raises():
    def boom(*a):
        raise RuntimeError("net down")

    assert Notifier("https://ntfy.sh", "t", transport=boom).send("x") is False


def test_make_notifier_disabled_by_flag():
    assert make_notifier({"NTFY_ENABLE": "0"}) is None


def test_make_notifier_default_enabled_to_topic():
    n = make_notifier({}, transport=lambda *a: 200)
    assert n is not None
    assert n.endpoint.endswith("/gergo_vb2026_tippek")


def test_notify_tip_formats_message():
    calls, transport = _recorder()
    n = Notifier("https://ntfy.sh", "t", transport=transport)
    notify_tip(n, "Spanyolország", "Szaúd-Arábia", Score(home_goals=2, away_goals=0), "submitted")
    assert "Spanyolország 2:0 Szaúd-Arábia" in calls[0][1]
    assert "mentve" in calls[0][1]


def test_notify_started_formats_message():
    calls, transport = _recorder()
    n = Notifier("https://ntfy.sh", "t", transport=transport)
    notify_started(n, "következő 48h")
    assert "elindult" in calls[0][1] and "48h" in calls[0][1]


def test_notify_helpers_noop_when_notifier_none():
    notify_started(None, "x")
    notify_tip(None, "a", "b", Score(home_goals=1, away_goals=1), "filled")
