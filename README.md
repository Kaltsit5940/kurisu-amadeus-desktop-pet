# 红莉栖 · Amadeus Windows 桌宠

以《命运石之门》动画中的牧濑红莉栖 / Amadeus 为灵感制作的个人非官方桌宠。透明半身窗口贴在 Windows 任务栏上，重点呈现表情、口型和托腮动作。可独立运行，无需 Codex，运行时无需联网。

![托腮动作预览](docs/cheek-preview.gif)

## 下载与运行

从 [Releases](https://github.com/Kaltsit5940/kurisu-amadeus-desktop-pet/releases/latest) 下载 `KurisuAmadeusPet.exe`，或下载 `KurisuAmadeusWindows.zip` 后解压，双击 exe 即可运行。已在 Windows 11 64 位环境测试；首次启动会花几秒解包。

默认高度 680 像素、动画刷新率 24 帧/秒。她会出现在主屏幕右下角，搭在任务栏上的手与任务栏上缘对齐。可以在菜单中调整大小和位置。

| 操作 | 效果 |
| --- | --- |
| 右键桌宠或托盘图标 | 选择表情、托腮、大小、帧率、暂停、隐藏或退出 |
| 双击桌宠 | 触发说话动作 |
| 鼠标滚轮 | 调整大小 |
| 拖动桌宠 | 水平移动，继续贴住任务栏 |
| 双击托盘图标 | 找回隐藏的桌宠 |

表情包括惊讶、害羞、思考、开心、不满、得意和眨眼。说话使用五种口型、停顿和眨眼。托腮动作包括抬手、肘部落在任务栏上、手掌托住脸颊、另一只手轻点任务栏，以及放下手。临时表情和动作完成后自动回到常态。

菜单可选 12 / 18 / 24 / 30 帧/秒；刷新率与独立绘制的画面数量是两回事。当前素材包含 20 张美术关键帧，组合成 25 张透明动画画面。运行时直接切换画面，避免透明淡化造成双眼或手部重影。

设置保存在 `%LOCALAPPDATA%\KurisuAmadeusPet\settings.json`。程序不修改注册表，也不设置开机启动。卸载时在托盘菜单退出并删除 exe；如需清除个人设置，再删除设置文件夹。

## 从源码运行

安装 Python 3.13，在项目目录执行：

```powershell
python -m pip install -r requirements.txt
python pet.py
```

`assets/` 已包含准备好的透明素材，运行和打包时无需重新生成美术。

## 构建独立 exe

在 Windows 上运行：

```powershell
.\build.ps1
```

脚本会创建项目内的 `.venv`、安装固定版本的构建依赖，并通过 PyInstaller 生成 `dist/KurisuAmadeusPet.exe`。如需指定 Python 路径：

```powershell
.\build.ps1 -Python "C:\path\to\python.exe"
```

## 素材与检查

- `pet.py`：窗口、任务栏锚点、交互菜单和动画时间轴。
- `assets/`：运行时透明素材、图标及 `manifest.json`。
- `references/`：确认过的基础造型和托腮概念图。
- `generated/`：表情、口型与托腮原始关键帧。
- `assemble.py`、`assemble_cheek.py`：透明素材的整理脚本。
- `docs/`：动作预览与表情对照。

安装 `requirements-art.txt` 后，可以按顺序运行 `python assemble.py` 和 `python assemble_cheek.py`，重新整理透明素材。预览脚本使用 Windows 自带字体。

素材和时间轴自检：

```powershell
python pet.py --self-test
```

实际窗口与动作检查（26 秒后自动退出，设置不会保存）：

```powershell
python pet.py --smoke-seconds 26 --report smoke-report.json
```

人物设计来自《命运石之门》，本项目的美术关键帧基于参考图通过 AI 辅助制作。
