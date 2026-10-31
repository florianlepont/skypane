"""Role-conditional reductions for the signed-in user (non-admin) view.

Pure helpers: no sqlite, no file or network access. Page renderers ask
`platform_visible()` whether a platform-wide section (flight-data
sources, backup, fleet status, airline registry) may appear in the
served markup; the settings POST handler runs every submitted form
through `sanitise_settings_form()`, which is the enforcement layer (a
hidden control is cosmetic, a crafted request can still send its field).

The role is read only from the principal the dispatcher resolved from
the local users row (`prefs.current_principal()`), never from a request
value. With no principal set (unit tests, pre-sign-in pages) nothing is
reduced.
"""
from companion import access, health_signals, prefs
from companion.settings import wake_interval

# Form fields only an admin may change: the wake interval, the
# diagnostic LED and the tracked runway.
ADMIN_ONLY_SETTING_FIELDS = (
    wake_interval.WAKE_INTERVAL_FIELD_NAME,
    "led_enabled",
    "tracked_runway",
)

_USER_HIDDEN_FIELD_SET = frozenset(ADMIN_ONLY_SETTING_FIELDS)


def _role():
    principal = prefs.current_principal()
    return None if principal is None else principal[1]


def is_user_view():
    """True when the current request's principal is a plain user."""
    return _role() == access.USER


def platform_visible():
    """True when platform-wide sections may render: always, except for a
    user principal."""
    return not is_user_view()


def sanitise_settings_form(form, role):
    """A copy of the submitted settings form that is safe to apply for
    `role`. An admin form is returned unchanged; for a user the
    admin-only fields are dropped and the scope is forced to the display
    scope, so a crafted `scope=all` or `scope=device` cannot widen which
    groups the save resolves.
    """
    # Imported here: the page module imports this one to gate its groups.
    from companion.pages import config_page

    cleaned = dict(form)
    if role != access.USER:
        return cleaned
    for name in _USER_HIDDEN_FIELD_SET:
        cleaned.pop(name, None)
    cleaned[config_page.SCOPE_FIELD_NAME] = config_page.SCOPE_DISPLAY
    return cleaned


def frame_only_anomalies(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state="ok", source_fault=False, offbox=None, fleet_fault=False):
    """Anomaly strings built from the frame's own signals only (check-in
    staleness and battery). The platform inputs are accepted so a caller
    can pass a full snapshot; they never contribute.
    """
    return health_signals.collect_anomalies(
        device_state, "ok", battery_state, False,
        coverage_state="ok", source_fault=False, offbox=None, fleet_fault=False)


def frame_only_severity(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state="ok", source_fault=False, offbox_state="ok", fleet_fault=False):
    """The ok/warn/error severity from the frame's own signals only; the
    platform inputs are accepted and ignored.
    """
    return health_signals.overall_severity(
        device_state, "ok", battery_state, False,
        coverage_state="ok", source_fault=False, offbox_state="ok",
        fleet_fault=False)


def reduce_signals(signals):
    """`signals` (a `health_signals()` snapshot) as the current principal
    may see it: unchanged for an admin or an unset principal, and for a
    user a copy whose platform states are neutral and whose severity and
    anomalies are frame-only. `None` stays `None`.
    """
    if signals is None or not is_user_view():
        return signals
    reduced = dict(signals)
    reduced.update(
        pipeline_state="ok", disagreement_warn=False, source_fault=False,
        coverage_state="ok", offbox=None,
        severity=frame_only_severity(
            signals["device_state"], "ok", signals["battery_state"], False),
        anomalies=frame_only_anomalies(
            signals["device_state"], "ok", signals["battery_state"], False))
    return reduced
