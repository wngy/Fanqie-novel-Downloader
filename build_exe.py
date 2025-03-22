import PyInstaller.__main__
import os

# 确保脚本路径正确
script_path = os.path.dirname(os.path.abspath(__file__))
gui_path = os.path.join(script_path, 'gui.py')
icon_path = os.path.join(script_path, 'favicon.ico')  # 如果有图标文件的话

# 设置PyInstaller参数
args = [
    gui_path,
    '--name=番茄小说下载器',
    '--onefile',
    '--windowed',
    '--clean',
    # '--icon=' + icon_path,  # 如果有图标文件，取消此行注释
    '--add-data=2.py;.',
    '--add-data=cookie.json;.',  # 添加cookie文件
    '--hidden-import=requests',
    '--hidden-import=bs4',
    '--hidden-import=lxml',
    '--hidden-import=ebooklib',
    '--hidden-import=ebooklib.epub',  # 明确导入ebooklib.epub模块
    '--hidden-import=tqdm',
]

# 运行PyInstaller
PyInstaller.__main__.run(args)

print("打包完成！")
print("可执行文件位于 dist 文件夹中")