from app.crawler.browser_session import _host, _login_and_target_hosts


def test_extracts_login_and_service_hosts():
    url = (
        "https://ca.muc.edu.cn/zfca/login?"
        "service=http%3A%2F%2Fmy.muc.edu.cn%2Fuser%2FsimpleSSOLogin%23%2F"
    )
    assert _login_and_target_hosts(url) == ("ca.muc.edu.cn", "my.muc.edu.cn")


def test_host_is_case_insensitive():
    assert _host("HTTPS://MY.MUC.EDU.CN/path") == "my.muc.edu.cn"
