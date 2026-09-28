"""本地启动器：复用已运行实例，避免重复启动造成端口占用错误。"""
from __future__ import annotations
import json,socket,threading,time,webbrowser
from urllib.request import urlopen
import uvicorn
from app.settings import ensure_directories
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

def serve(port:int):uvicorn.run("app.main:app",host=HOST,port=port,log_level="info")

def wait_until_ready(port:int,timeout:float=15.0)->bool:
    deadline=time.time()+timeout
    while time.time()<deadline:
        if is_our_server(port):return True
        time.sleep(.2)
    return False

if __name__=="__main__":
    ensure_directories();port,reused=choose_port()
    if reused:
        print(f"软件已在 http://{HOST}:{port} 运行，直接打开现有界面。")
    else:
        threading.Thread(target=serve,args=(port,),daemon=True).start()
    if not wait_until_ready(port):
        # 旧实例可能恰好在检测后退出，此时在同一端口补启动一次。
        if reused and port_is_free(port):
            reused=False
            threading.Thread(target=serve,args=(port,),daemon=True).start()
        if not wait_until_ready(port):
            raise RuntimeError(f"本地服务启动失败，无法访问 http://{HOST}:{port}。请查看上方错误信息。")
    local_url=f"http://{HOST}:{port}"
    try:
        import webview
        webview.create_window("中央民族大学就业分享信息检索",local_url,width=1280,height=820,min_size=(1000,650))
        webview.start()
    except Exception as exc:
        print(f"PyWebView 无法启动（{exc}），已改用浏览器。")
        webbrowser.open(local_url)
        try:
            while True: time.sleep(3600)
        except KeyboardInterrupt:pass
