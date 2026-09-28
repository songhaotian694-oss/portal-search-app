# 中央民族大学就业分享信息检索软件

这是一个只监听 `127.0.0.1` 的本地桌面软件。它用 PyWebView 显示界面，用 Playwright 打开**可见**的 Chromium 浏览器供用户自行登录；不会保存或填写账号、密码、验证码，也不会绕过校方认证或访问无权限数据。

## 安装与启动

需安装 Python 3.11（建议使用虚拟环境）。在本目录执行：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python launcher.py
```

如果点击“登录门户”时提示 Chromium 不存在，可关闭软件并双击
`install_browser.bat`。安装完成后重新运行 `run.bat`。程序在没有找到
Playwright Chromium 时也会尝试使用 Windows 中的 Microsoft Edge。

推荐双击 `启动软件.vbs`，软件窗口会正常显示，不会打开黑色命令窗口。也可双击 `run.bat`，它会短暂启动后自动关闭命令窗口。程序在 8765—8774 中选择本机端口；如果本机 GUI 组件不可用，会自动用默认浏览器打开。启动错误记录在 `data/logs`。

双击 `创建桌面快捷方式.vbs` 可在桌面创建带图标的“选调生信息搜索”快捷方式。图标文件位于 `assets/app-icon.ico`，同时提供 `assets/app-icon.png` 和可编辑的 `assets/app-icon.svg`。请保持快捷方式指向的项目文件夹位置不变；移动项目后重新运行创建脚本即可。

“搜索选调生”直接查询本地结构化学生记录，可按姓名、届别、年级、学历、专业、城市或地区、就业单位和岗位检索，并查看来源与OCR证据。就业分享海报使用内置 RapidOCR（OpenCV + ONNX Runtime，本地OCR）识别，不上传图片；一篇海报包含多名学生时，每名学生会生成一条独立就业记录。门户接口能提供原图地址时直接下载原图，只有原图无法取得时才需要网页截图后识别。

## 先体验模拟模式

1. 打开“数据同步”，点击“运行模拟同步”。这会读取 `tests/fixtures` 中的模拟列表/详情页，把原始 HTML、正文和一个本地模拟 Word 附件保存到 `data`。
2. 处理完数据后打开“搜索选调生”，按姓名、地区或专业搜索每名学生的记录与OCR依据。
3. 点击左侧“导出 Excel”，文件保存在 `data/exports`，包含结果、采集失败记录和待人工核对记录三个工作表。

模拟数据仅为自动化开发和测试夹具，未编造真实学校接口、页面结构或真实就业信息。

## 连接真实门户（必须由用户本人操作）

1. 将 `config/portal.example.yaml` 复制为 `config/portal.yaml`。
2. 填写真实 `portal_url`、`employment_entry` 和 `allowed_domains`。只能填你有正常访问权限的中央民族大学域名。
3. 不知道 CSS 选择器时，点击“登录门户”，在打开的可见浏览器中自行认证，然后自行进入就业信息栏目。
4. 回到软件点击“我已登录”，再进入“设置”点击“页面配置检查”。程序仅保存脱敏当前页 HTML 到 `data/diagnostics`，列出每项选择器的命中数与最多三段脱敏文本。它会明确标出仍是 `TODO`、空选择器或无效 CSS 的设置。
5. 根据检查结果填写 `list_item_selector`、`title_selector`、`date_selector`、`detail_link_selector`、`next_button_selector`、`detail_body_selector`、`attachment_selector`，保存后可先运行“测试同步（前两页）”。确认后再运行完整/增量同步。

未知选择器目前需要在真实登录页确认后填写：上面八个 `*_selector` 项、真实门户地址/就业栏目入口、允许域名，以及登录页识别文字 `login_page_markers`。项目故意没有猜测或硬编码它们。

当前 `config/portal.yaml` 已按学校就业信息列表的真实接口完成配置。数据同步
默认采用老师演示的接口方式：登录后监听门户自身发出的 `getNoticeByPage`
请求，学习实际请求体，再用当前登录会话直接读取 `datas.tables`。每条记录的
`notice_content` 已含通知正文，因此程序不会逐条打开详情页。原始 JSON 按
关键词和页码保存在 `data/raw_json`，正文直接保存到 `data/article_text`，正文中
的图片和附件保存到 `data/attachments`。只有接口不可用时才使用页面模式作为
后备；Cookie 不会写入接口模板或源代码。

采集器仅访问 `allowed_domains` 内的 URL；外部附件只记录链接，不自动下载。每页/请求间隔读取 `page_interval_seconds`（默认 1.5 秒）。每条文章按详情链接去重、内容哈希增量更新；失败项会写入本地失败记录，之后可以单独重试。登录失效会暂停采集，需要再次手动登录后继续。

## 数据、隐私与安全

所有正文、附件、SQLite 数据库、索引、导出文件和日志均位于 `data/`，且已在 `.gitignore` 中排除。`data/playwright_state.json` 含敏感 Cookie，同样已忽略：**不得提交到 Git、发送给他人或上传到网盘**。日志不记录密码、Cookie 或 Authorization 请求头。网页正文以纯文本方式显示，不执行其中 HTML/脚本；附件名会清理为安全本地文件名。

图片与扫描 PDF 在没有安装 OCR 的情况下标记为 `pending_ocr` / 待人工查看；这不会停止其他正文和附件的处理。

## 测试

```bat
pytest -q
```

测试覆盖模拟列表/详情/下一页/附件、20 条中文字段表达、Word 解析、数据库去重与增量、FTS 与筛选、文本切片、Excel 导出、路径安全与失败不阻断其他文章。

## 打包

先安装依赖并确认 `python launcher.py` 正常，然后双击 `build_exe.bat`。PyInstaller 输出在 `dist/EmploymentPortalSearch/`。打包后的首次运行仍需安装 Playwright Chromium 或按组织环境单独准备浏览器依赖。
