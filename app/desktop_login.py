"""A native school-authentication view hosted inside the existing desktop form.

Only the application's local React page has a pywebview bridge. The remote
school page is a plain WebView2 control with no application API injected.
"""
from __future__ import annotations

import os
import threading
from uuid import uuid4


class DesktopLoginHost:
    def __init__(self):
        self.window = None
        self.debug_port = 0
        self.placeholder = f"about:blank#zhixu-login-{uuid4().hex}"
        self.panel = self.control = None
        self.visible = False
        self.cancelled = False
        self._ready = threading.Event()
        self._error = ""

    @property
    def available(self) -> bool:
        return os.name == "nt" and self.window is not None

    def attach(self, window, debug_port: int) -> None:
        self.window, self.debug_port = window, debug_port

    def detach(self) -> None:
        self.window = None
        self.visible = False

    def _invoke(self, action):
        """All WinForms creation, resizing and disposal run on its UI thread."""
        from System import Action

        form = self.window.native
        if form is None or form.IsDisposed:
            raise RuntimeError("软件窗口尚未就绪，请稍后重试。")
        if form.InvokeRequired:
            form.Invoke(Action(action))
        else:
            action()

    def ensure(self) -> str:
        if not self.available:
            raise RuntimeError("当前运行方式不支持内嵌认证，请通过桌面软件启动。")
        if self.control is not None:
            if self._error:
                raise RuntimeError(self._error)
            return self.placeholder

        def create():
            from Microsoft.Web.WebView2.WinForms import WebView2
            from System.Drawing import Color, Font, Point, Size
            from System.Windows.Forms import Button, DockStyle, Label, Panel

            form = self.window.native
            if not getattr(form, "webview", None) or not form.webview.CoreWebView2:
                raise RuntimeError("内嵌浏览器尚未就绪，请稍后重试。")
            scale = float(getattr(form, "_scale", 1))
            panel = Panel()
            panel.Dock = DockStyle.Fill
            panel.Visible = False
            panel.BackColor = Color.FromArgb(247, 250, 251)
            toolbar = Panel()
            toolbar.Dock = DockStyle.Top
            toolbar.Height = round(58 * scale)
            toolbar.BackColor = panel.BackColor
            label = Label()
            label.AutoSize = True
            label.Text = "知序  ·  学校统一认证，登录成功后自动返回"
            label.Font = Font("Microsoft YaHei", 10)
            label.ForeColor = Color.FromArgb(29, 64, 88)
            label.Location = Point(round(22 * scale), round(19 * scale))
            toolbar.Controls.Add(label)
            cancel = Button()
            cancel.Text = "返回软件"
            cancel.Size = Size(round(100 * scale), round(34 * scale))
            cancel.Click += lambda *_: self.cancel()
            toolbar.Controls.Add(cancel)

            def align(*_):
                cancel.Location = Point(max(0, toolbar.Width - round(122 * scale)), round(12 * scale))

            toolbar.Resize += align
            control = WebView2()
            control.Dock = DockStyle.Fill
            # Use the same environment options and private profile as the app.
            control.CreationProperties = form.webview.CreationProperties
            panel.Controls.Add(control)
            panel.Controls.Add(toolbar)
            control.BringToFront()
            form.Controls.Add(panel)
            panel.BringToFront()
            self.panel, self.control = panel, control

            def initialized(sender, args):
                if not args.IsSuccess:
                    self._error = "无法初始化内嵌认证浏览器，请检查 WebView2 Runtime。"
                    self._ready.set()
                    return
                core = sender.CoreWebView2
                settings = core.Settings
                settings.AreDevToolsEnabled = False
                settings.AreDefaultContextMenusEnabled = False
                settings.IsPasswordAutosaveEnabled = False
                settings.IsGeneralAutofillEnabled = False

                def new_window(_, event):
                    # School SSO sometimes opens its destination in a new tab.
                    # Keep that destination in this same native auth view.
                    event.Handled = True
                    core.Navigate(str(event.Uri))

                core.NewWindowRequested += new_window
                core.Navigate(self.placeholder)
                self._ready.set()

            control.CoreWebView2InitializationCompleted += initialized
            control.EnsureCoreWebView2Async(form.webview.CoreWebView2.Environment)
            align()

        self._invoke(create)
        if not self._ready.wait(15):
            raise RuntimeError("内嵌认证浏览器初始化超时，请重启软件。")
        if self._error:
            raise RuntimeError(self._error)
        return self.placeholder

    def show(self) -> None:
        self.ensure()

        def show():
            self.cancelled = False
            self.panel.Visible = True
            self.panel.BringToFront()
            self.control.Focus()
            self.visible = True

        self._invoke(show)

    def hide(self) -> None:
        if self.panel is None:
            return

        def hide():
            self.panel.Visible = False
            self.visible = False
            if not self.window.native.IsDisposed:
                self.window.native.webview.Focus()

        self._invoke(hide)

    def cancel(self) -> None:
        self.cancelled = True
        self.hide()

    def dispose(self) -> None:
        if self.control is None:
            return

        def dispose():
            self.panel.Dispose()
            self.panel = self.control = None
            self.visible = False
            self._ready.clear()
            self._error = ""

        if self.window.native is not None and not self.window.native.IsDisposed:
            self._invoke(dispose)


desktop_login = DesktopLoginHost()
