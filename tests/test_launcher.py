import launcher


def test_launcher_skips_old_server_and_reuses_current_one(monkeypatch):
    monkeypatch.setattr(launcher, "is_our_server", lambda port: port == 8767)
    monkeypatch.setattr(launcher, "port_is_free", lambda port: port >= 8768)
    assert launcher.choose_port() == (8767, True)


def test_launcher_uses_free_port_when_only_old_server_is_running(monkeypatch):
    monkeypatch.setattr(launcher, "is_our_server", lambda port: False)
    monkeypatch.setattr(launcher, "port_is_free", lambda port: port != 8765)
    assert launcher.choose_port() == (8766, False)
