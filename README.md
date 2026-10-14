# PRTS

从 [最新版本](https://github.com/crowninggg/prts-cursor/releases/latest) 下载对应系统的压缩包。

## Windows 安装

1. 完整解压 Windows 安装包，保持 `PRTS-Install.exe` 与“程序文件”文件夹在同一目录。
2. 双击 `PRTS-Install.exe`。
3. 选择指针大小、待机和窗口拖拽等选项，点击“安装 / 应用设置”。
4. 等待提示设置已应用后关闭安装器。以后可重新打开修改选项。
5. 网页界面无法启动时会自动切换基础安装界面，全部安装选项均可调整。

备用方式：打开“程序文件”，双击“基础安装.cmd”使用基础界面；仅需默认设置时可运行“备用安装.cmd”。

## macOS 安装

1. 从 [Mousecape Releases](https://github.com/alexzielenski/Mousecape/releases) 下载兼容当前系统的 Mousecape，放入“应用程序”并打开一次，在其中保存当前主题。
2. 完整解压 macOS 安装包，双击 `PRTS Install.app`。
3. 选择静态或循环动画主题，按提示安装；首次使用可先选静态主题。
4. 若未自动应用，在 Mousecape 中选中 PRTS，点击 `Capes → Apply Cape`。

备用方式：打开终端，输入 `bash `，将 `Install-PRTS.command` 拖入终端并回车。也可将 `PRTS Install.app/Contents/Resources` 中的 `.cape` 文件导入 Mousecape 后应用。系统拦截时，按“系统设置 → 隐私与安全性”的提示允许打开。

## Linux 安装

1. 完整解压 Linux 安装包，在 `INSTALL.sh` 所在目录打开终端。
2. 运行 `sh INSTALL.sh`，使用当前桌面用户，不要使用 `sudo`。
3. 选择静态或循环动画主题，按提示安装。
4. 未自动切换时，在桌面鼠标指针设置中选择 `PRTS-Final-Static` 或 `PRTS-Final`。
5. 部分应用未刷新时重新打开，必要时注销后登录。需要还原时重新运行安装器选择“还原”。

备用方式：将 `files` 中两个主题文件夹复制到 `~/.local/share/icons`（自定义 `XDG_DATA_HOME` 时使用该目录下的 `icons`），再在桌面设置中选择。Sway、Hyprland 等独立合成器需在各自配置中指定主题名和大小。
