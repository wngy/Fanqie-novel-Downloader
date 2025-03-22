# 番茄小说下载器

这是一个用于下载番茄小说的工具。

## 功能

- 支持番茄小说内容下载
- 将小说转换为适合阅读的格式
- 简洁易用的图形界面

## 使用方法

### 直接使用预编译版本

可以在[Releases](https://github.com/your-username/Tomato-Novel-Downloader-Lite/releases)页面下载最新的预编译版本。

- Windows用户：下载并解压`番茄小说下载器-Windows.zip`，直接运行`番茄小说下载器.exe`。
- MacOS用户：下载并解压`番茄小说下载器-MacOS.zip`，直接运行`番茄小说下载器`应用。
- Linux用户：下载并解压`番茄小说下载器-Linux.zip`，直接运行`番茄小说下载器`可执行文件。

### 从源码运行

1. 克隆仓库：
```bash
git clone https://github.com/your-username/Tomato-Novel-Downloader-Lite.git
cd Tomato-Novel-Downloader-Lite
```

2. 安装依赖：
```bash
pip install requests bs4 lxml ebooklib tqdm
```

3. 运行程序：
```bash
python gui.py
```

## 自动构建与发布

本项目使用GitHub Actions自动构建并发布应用。

### 自动构建流程

当你创建新的Release或手动触发工作流时，GitHub Actions会自动：

1. 在Windows、MacOS和Linux上构建可执行文件
2. 将构建好的可执行文件打包为zip文件
3. 上传构建产物到GitHub Artifacts
4. 如果是从Release触发的，则自动将构建产物上传到Release页面

### 手动触发构建

1. 在GitHub仓库页面，点击"Actions"选项卡
2. 在左侧选择"构建与发布"工作流
3. 点击"Run workflow"按钮
4. 选择要运行的分支，然后点击"Run workflow"

### 创建Release并自动发布

1. 在GitHub仓库页面，点击"Releases"
2. 点击"Draft a new release"
3. 填写标签(tag)和标题
4. 点击"Publish release"
5. GitHub Actions将自动构建并将构建产物上传到此Release

## 许可证

[在此处添加许可证信息]