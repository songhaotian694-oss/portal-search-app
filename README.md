# 中央民族大学就业分享信息检索软件

这是一个只监听 `127.0.0.1` 的本地桌面软件。新版 React 界面直接检索本机 SQLite 数据库；PyWebView 提供桌面窗口。在 Windows 桌面软件中，学校认证页由原生 WebView2 控件内嵌显示，用户自行填写账号、密码和验证码；登录成功后认证区域自动关闭并进入首页。认证页面不会注入软件的 Python 接口。

## 启动

双击桌面“选调生信息搜索”快捷方式，或运行 `dist/EmploymentPortalSearch/EmploymentPortalSearch.exe`。新版界面包含“概览”“智能检索”“数据探索”“数据更新”四个入口，旧界面已移除。请保留完整打包文件夹，不要单独移动 EXE。

## 从源代码运行

需安装 Python 3.11（建议使用虚拟环境）。在本目录执行：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python launcher.py
```

Windows 桌面认证使用系统 WebView2 Runtime。若以普通浏览器运行前端，认证会改用单独的 Edge / Chrome；未安装可用浏览器时可运行 `install_browser.bat` 安装 Playwright Chromium。

先在 `frontend/` 运行 `pnpm install` 与 `pnpm build`，再运行 `python launcher.py`。`启动软件.vbs` 可隐藏命令窗口；程序在 8765—8774 中选择本机端口。启动日志记录在 `data/logs`。

双击 `创建桌面快捷方式.vbs` 可在桌面创建带图标的“选调生信息搜索”快捷方式。如果已打包，快捷方式会直接指向 EXE；否则指向脚本启动器。图标文件位于 `assets/app-icon.ico`，同时提供 `assets/app-icon.png` 和可编辑的 `assets/app-icon.svg`。请保持快捷方式指向的项目文件夹位置不变；移动项目或首次打包后重新运行创建脚本即可。

“智能检索”直接查询本地结构化学生记录，可按姓名、届别、学历、专业、地区、单位和岗位检索，并查看来源与 OCR 证据。“数据探索”根据本地记录展示专业、地区、岗位等关系。就业分享海报使用内置 RapidOCR 本地识别，不上传图片。

## 连接真实门户（必须由用户本人操作）

1. 在“数据更新”中展开“门户设置”，填写有权限访问的登录页、就业栏目和允许域名并保存。当前机器已有本地配置时会自动加载。
2. 点击“在软件内登录”，在软件内的学校认证页自行认证。登录成功后自动返回首页，也可以通过认证区上方“返回软件”取消操作。
3. 先运行“测试获取前两页”；确认同步状态正常后点击“一键更新数据”。同步与识别在后台运行，界面会持续显示进度。
4. 在“智能检索”查看本机记录及证据；在“数据探索”查看关系图；在“数据更新”下载 Excel。

接口方式不可用时可以改为网页方式；网页方式所需的 CSS 选择器属于高级配置，可在 `config/portal.yaml` 中维护。

如果本机 `config/portal.yaml` 已按学校就业信息列表的真实接口完成配置，数据同步
可采用接口方式：登录后监听门户自身发出的 `getNoticeByPage`
请求，学习实际请求体，再用当前登录会话直接读取 `datas.tables`。每条记录的
`notice_content` 已含通知正文，因此程序不会逐条打开详情页。原始 JSON 按
关键词和页码保存在 `data/raw_json`，正文直接保存到 `data/article_text`，正文中
的图片和附件保存到 `data/attachments`。只有接口不可用时才使用页面模式作为
后备；Cookie 不会写入接口模板或源代码。

采集器仅访问 `allowed_domains` 内的 URL；外部附件只记录链接，不自动下载。每页/请求间隔读取 `page_interval_seconds`（默认 1.5 秒）。每条文章按详情链接去重、内容哈希增量更新；失败项会写入本地失败记录，之后可以单独重试。登录失效会暂停采集，需要再次手动登录后继续。

## 数据、隐私与安全

登录页和数据更新页提供“在本机保留登录状态”。勾选后，成功认证的 Cookie、localStorage 和 sessionStorage 保存到 `data/auth_state.bin`；Windows 使用 DPAPI 为当前系统用户加密。下次启动先验证保存的会话，过期后提示重新认证。软件不读取或保存密码，内嵌认证控件关闭浏览器密码自动保存和表单自动填充。取消勾选会删除已保存状态，当前内存会话仍可继续使用。

所有正文、附件、SQLite 数据库、索引、导出文件和日志均位于 `data/`，且已在 `.gitignore` 中排除。旧 `data/playwright_state.json` 会在下次成功保存时迁移为加密状态；所有登录状态均**不得提交到 Git、发送给他人或上传到网盘**。日志不记录密码、Cookie 或 Authorization 请求头。网页正文以纯文本方式显示，不执行其中 HTML/脚本；附件名会清理为安全本地文件名。

图片使用内置 RapidOCR 自动识别；文字置信度不足或出现截断时，系统最多追加两次分区识别，并保存位置与置信度供自动校验。扫描 PDF 按页渲染识别，已有文字层的页面直接读取。规则会按选调身份行划分人物、拼接跨行单位/岗位并提取学历。识别仍不足的字段显示“未提取”，不猜填、不要求人工核对；导出 Excel 保留相应空值。原始资料与本地识别缓存保留，方便后续算法自动重跑。

新电脑保留整个 `EmploymentPortalSearch` 文件夹即可运行。包内只提供学校的公共入口与选择器配置；用户在软件内自行登录后，空数据库会自动拉取完整资料，再自动 OCR 和整理。已有数据在识别算法版本升级后自动重新整理。本机配置可以覆盖内置入口；数据库、账户凭据和 Cookie 不随程序发布。

## 测试

```bat
pytest -q
```

测试覆盖模拟列表/详情/下一页/附件、20 条中文字段表达、Word 解析、数据库去重与增量、FTS 与筛选、文本切片、Excel 导出、路径安全与失败不阻断其他文章。

## 打包

先安装 Python 依赖、pnpm 与 `frontend/` 依赖，再双击 `build_exe.bat`。脚本先编译前端，再使用 PyInstaller 打包，输出在 `dist/EmploymentPortalSearch/`。请保留整个打包输出文件夹。项目内生成的 EXE 会继续使用现有的 `config/` 和 `data/`；将打包文件夹单独复制到别处后，它会在旁边创建自己的配置和数据目录。打包文件不会包含本地 `config/portal.yaml`、数据库或登录状态。

## 前端开发

`frontend/` 是 React + TypeScript 界面，使用 Tailwind CSS、Framer Motion 和 ECharts。所有记录来自本地 FastAPI 接口，不再使用 Mock Data。设计说明见 [前端设计规划](frontend/DESIGN_PLAN.md)。

```bat
cd frontend
pnpm install
pnpm dev
```

打开 `http://127.0.0.1:5173/` 预览；先启动本地 Python 服务，Vite 将 `/api` 代理到 `127.0.0.1:8765`。`pnpm build` 生成 EXE 使用的静态产物。
