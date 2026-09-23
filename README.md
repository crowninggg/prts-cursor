# PRTS

## Windows 安装

1. 下载并完整解压 Windows 安装包，保持安装程序与“程序文件”文件夹在同一目录。
2. 双击 `PRTS-Install.exe`。
3. 选择是否启用后台交互效果，并按需调整其他选项，然后点击“安装 / 应用设置”。
4. 等待提示设置已应用后关闭安装器。之后可重新打开安装器修改设置。
5. 如果提示缺少 WebView2，按提示安装后重试。

备用方式：打开“程序文件”文件夹，双击“备用安装.cmd”使用默认设置；需要调整选项时运行同目录的 `PRTS-Setup.exe`。

## macOS 安装

1. 从 [Mousecape Releases](https://github.com/alexzielenski/Mousecape/releases) 下载 Mousecape，将它放入“应用程序”并至少打开一次。在 Mousecape 中保存当前主题。
2. 完整解压 macOS 安装包，双击 `PRTS Install.app`。
3. 选择静态或动画主题并按提示安装；首次使用可先选择静态主题。
4. 如果主题未自动应用，在 Mousecape 中选中 PRTS，点击 `Capes → Apply Cape`。

备用方式：若无法双击启动，打开终端，输入 `bash ` 后将 `Install-PRTS.command` 拖入终端并回车。仍无法启动时，可在 `PRTS Install.app/Contents/Resources` 中将 `PRTS-Final-Static.cape` 或 `PRTS-Final-Animated.cape` 导入 Mousecape，再点击 `Capes → Apply Cape`。如系统拦截应用，请按“系统设置 → 隐私与安全性”的提示允许打开。

## Linux 安装

1. 完整解压 Linux 安装包，并在 `INSTALL.sh` 所在目录打开终端。
2. 执行 `sh INSTALL.sh`，不要使用 `sudo`。
3. 选择静态或动画主题并按提示完成安装。
4. 如果主题未自动切换，在桌面的鼠标指针设置中选择 `PRTS-Final-Static`（静态）或 `PRTS-Final`（动画）。
5. 部分窗口未更新时，关闭后重新打开；仍未更新则注销并重新登录。

备用方式：将 `files` 内的 `PRTS-Final` 和 `PRTS-Final-Static` 两个完整文件夹复制到个人主目录的 `.local/share/icons`，再在桌面鼠标指针设置中选择对应主题。Sway、Hyprland 等独立合成器请在其光标配置中填写主题名和需要的大小，然后重新载入配置。
