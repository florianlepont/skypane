# Only ever reached via PYTHONPATH, and only when a test's own child_env()
# put TEST_SUPPORT_DIR on that PYTHONPATH - never deployed (deploy/deploy.sh
# rsyncs server/, stub-server/, companion/ only, never test-support/).
# Python auto-imports a module named sitecustomize once, at interpreter
# start, if one is found on sys.path - this is that hook, aimed at a child
# interpreter a test harness launches with subprocess.Popen()/run().
#
# Deliberately no guard around either branch below: if installing the
# network guard or the fake provider fails here, the child interpreter
# should crash loudly and immediately, not silently start up unguarded.
import os

if os.environ.get("SKYPANE_TEST_NO_NETWORK"):
    import skypane_test_support

    skypane_test_support.install_child_network_guard()

_fake_provider = os.environ.get("SKYPANE_TEST_FAKE_PROVIDER")
if _fake_provider:
    import skypane_test_support

    if _fake_provider == "default":
        _fake = skypane_test_support.FakeProviders()
    else:
        _fake = skypane_test_support.FakeProviders.from_file(_fake_provider)
    _fake.install()
