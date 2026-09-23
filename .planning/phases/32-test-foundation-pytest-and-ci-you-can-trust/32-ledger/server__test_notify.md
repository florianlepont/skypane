# Ledger: server/test_notify.py

Baseline: 32-BASELINE/server__test_notify.txt (8 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | send_notification() returns True for a 200 response from the injected transport | ported | server/test_notify.py::test_send_notification_returns_true_for_a_200_response_from_the_injected_transport |
| 2 | send_notification() returns False for a 500 response from the injected transport | ported | server/test_notify.py::test_send_notification_returns_false_for_a_500_response_from_the_injected_transport |
| 3 | send_notification() returns False (never raises) when the transport raises TimeoutError | ported | server/test_notify.py::test_send_notification_returns_false_never_raises_when_the_transport_raises_timeout_error |
| 4 | send_notification() returns False (never raises) when the transport raises an arbitrary Exception | ported | server/test_notify.py::test_send_notification_returns_false_never_raises_when_the_transport_raises_an_arbitrary_exception |
| 5 | send_notification() returns False for a loopback, a localhost, a link-local cloud-metadata, and a file:// topic URL, without the injected transport ever being called | ported | server/test_notify.py::test_ssrf_gate_refuses_before_ever_calling_the_transport |
| 6 | body_for_lang() returns the French form for 'fr' and the English source string unchanged for every other language argument | ported | server/test_notify.py::test_body_for_lang_returns_french_or_falls_back_to_english |
| 7 | default_notify_transport() builds a POST request with the body UTF-8 encoded, a Title header, and the caller's timeout, against a faked opener | ported | server/test_notify.py::test_default_transport_builds_the_expected_request |
| 8 | default_notify_transport()'s _NoRedirectHandler refuses a 302 pointing at an internal address (169.254.169.254) outright - send_notification() returns False and the redirect target is never fetched | ported | server/test_notify.py::test_no_redirect_handler_refuses_a_302_to_an_internal_address_and_never_fetches_it |
