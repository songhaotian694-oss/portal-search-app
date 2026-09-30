"""本地启动器：复用已运行实例，避免重复启动造成端口占用错误。"""
from __future__ import annotations
import json,socket,sys,threading,time,webbrowser
from urllib.request import urlopen
if '--self-check' in sys.argv:
    from app.package_check import main as package_check
    raise SystemExit(package_check())
import uvicorn
from app.settings import DIRS,ensure_directories

# A windowed PyInstaller process has no console streams. Uvicorn still needs
# writable streams for its log handlers, so keep them in the local log folder.
if sys.stdout is None or sys.stderr is None:
    ensure_directories()
    startup_log=(DIRS["logs"]/"desktop-launch.log").open("a",encoding="utf-8",buffering=1)
    if sys.stdout is None:sys.stdout=startup_log
    if sys.stderr is None:sys.stderr=startup_log

from app.main import app
from app.version import APP_VERSION

HOST="127.0.0.1"

def is_our_server(port:int)->bool:
    try:
        with urlopen(f"http://{HOST}:{port}/api/version",timeout=.6) as response:
            data=json.loads(response.read().decode("utf-8"))
            return isinstance(data,dict) and data.get("version")==APP_VERSION
    except Exception:return False

def port_is_free(port:int)->bool:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        try:sock.bind((HOST,port));return True
        except OSError:return False

def choose_port()->tuple[int,bool]:
    for port in range(8765,8775):
        if not port_is_free(port) and is_our_server(port):return port,True
    for port in range(8765,8775):
        if port_is_free(port):return port,False
    raise RuntimeError("本机端口 8765—8774 均被占用，请关闭不需要的程序后重试。")

def make_server(port:int):
    return uvicorn.Server(uvicorn.Config(app,host=HOST,port=port,log_level="info"))

def serve(port:int):make_server(port).run()

def free_debug_port()->int:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.bind((HOST,0))
        return sock.getsockname()[1]

def wait_until_ready(port:int,timeout:float=15.0)->bool:
    deadline=time.time()+timeout
    while time.time()<deadline:
        if is_our_server(port):return True
        time.sleep(.2)
    return False

if __name__=="__main__":
    ensure_directories();port,reused=choose_port()
    # Native login belongs to this process's desktop form. Reusing a backend
    # from another form/process would attach authentication to that old window.
    if reused:
        free_ports=[candidate for candidate in range(8765,8775) if port_is_free(candidate)]
        if not free_ports:raise RuntimeError("软件实例过多，请关闭旧窗口后重新启动。")
        port=free_ports[0]
    server=make_server(port)
    server_thread=threading.Thread(target=server.run,daemon=True)
    server_thread.start()
    if not wait_until_ready(port):
        raise RuntimeError(f"本地服务启动失败，无法访问 http://{HOST}:{port}。请查看上方错误信息。")
    local_url=f"http://{HOST}:{port}"
    try:
        import webview
        from app.desktop_login import desktop_login
        debug_port=free_debug_port()
        webview.settings['REMOTE_DEBUGGING_PORT']=debug_port
        window=webview.create_window("知序 · 选调生信息检索",local_url,width=1280,height=820,min_size=(1000,650))
        desktop_login.attach(window,debug_port)
        closing=threading.Event()

        def close_desktop():
            if closing.is_set():
                return False
            closing.set()

            def shutdown():
                # Keep the UI pump alive until the server has saved the latest
                # tokens and disconnected Playwright from its native view.
                server.should_exit=True
                server_thread.join(timeout=10)
                try:desktop_login.dispose()
                except Exception:pass
                window.destroy()

            threading.Thread(target=shutdown,daemon=True).start()
            return True

        window.events.closing+=close_desktop
        webview.start(gui="edgechromium",private_mode=True)
        server.should_exit=True
        server_thread.join(timeout=10)
    except Exception as exc:
        from app.desktop_login import desktop_login
        desktop_login.detach()
        print(f"PyWebView 无法启动（{exc}），已改用浏览器。")
        webbrowser.open(local_url)
        try:
            while True: time.sleep(3600)
        except KeyboardInterrupt:pass
