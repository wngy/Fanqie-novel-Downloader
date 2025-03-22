import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import time
from tqdm import tqdm
import importlib.util

# 获取正确的2.py文件路径
def get_script_path():
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        return os.path.join(sys._MEIPASS, "2.py")
    else:
        # 如果是开发环境
        return "2.py"

# 导入2.py中的函数
script_path = get_script_path()
spec = importlib.util.spec_from_file_location("novel_downloader", script_path)
novel_downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(novel_downloader)

class RedirectText:
    """用于重定向输出到GUI的类"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        if string is None:
            string = "None"  # 处理None值情况
        self.buffer += string
        # 在UI线程上安全更新
        if self.text_widget and hasattr(self.text_widget, 'after'):
            self.text_widget.after(10, self.update_text_widget)
    
    def update_text_widget(self):
        if not self.text_widget or not hasattr(self.text_widget, 'config'):
            return  # 如果text_widget无效则直接返回
        try:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, self.buffer)
            self.text_widget.see(tk.END)  # 自动滚动到最新内容
            self.text_widget.config(state=tk.DISABLED)
            self.buffer = ""
        except Exception as e:
            print(f"更新文本控件时出错: {str(e)}", file=sys.__stdout__)

    def flush(self):
        pass

class CustomTqdm(tqdm):
    """自定义tqdm进度条，将更新发送到GUI"""
    def __init__(self, *args, progress_var=None, progress_label=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_var = progress_var
        self.progress_label = progress_label
        self._last_update_time = 0
        self._update_interval = 0.1  # 更新UI的间隔时间（秒）

    def update(self, n=1):
        try:
            displayed = super().update(n)
            # 限制更新频率，避免UI卡顿
            current_time = time.time()
            if current_time - self._last_update_time > self._update_interval:
                try:
                    if self.progress_var and hasattr(self.progress_var, 'set'):
                        # 在主线程中更新UI
                        if self.total and self.total > 0:
                            percentage = min(100, max(0, int(self.n / self.total * 100)))
                        else:
                            percentage = 0
                        self.progress_var.set(percentage)
                        
                        if self.progress_label and hasattr(self.progress_label, 'configure'):
                            text = f"下载进度: {percentage}% ({self.n}/{self.total or '?'})"
                            self.progress_label.configure(text=text)
                except Exception as e:
                    print(f"更新进度条时出错: {str(e)}", file=sys.__stdout__)
                self._last_update_time = current_time
            return displayed
        except Exception as e:
            print(f"tqdm更新时出错: {str(e)}", file=sys.__stdout__)
            return False

class NovelDownloaderGUI(tk.Tk):
    def __init__(self):
        """初始化应用程序界面和设置"""
        try:
            super().__init__()
            self.title("番茄小说下载器 - 精简版")
            self.geometry("800x600")
            self.minsize(600, 450)  # 设置最小窗口大小
            self.resizable(True, True)
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # 添加版本信息
            self.version = "1.1.0"
            
            # 状态变量
            self.is_downloading = False
            self.download_thread = None
            self.last_settings = {}  # 用于存储上次的设置
            
            # 初始化日志记录
            import logging
            self.logger = logging.getLogger("TomatoNovelDownloader.GUI")
            self.logger.info(f"GUI初始化开始，版本: {self.version}")
            
            # 设置变量
            self.threads_var = tk.StringVar(value="5")
            self.format_var = tk.StringVar(value="txt")
            
            # 创建控件前尝试加载配置
            self.load_settings()
            
            # 设置样式主题
            self.setup_style()
            
            # 创建UI控件
            self.create_widgets()
            
            # 设置图标（如果有的话）
            self.setup_icon()
            
            # 监听格式选择变化
            self.format_var.trace_add("write", self.on_format_changed)
            
            # 检查ebooklib可用性（如果需要）
            if self.format_var.get() == "epub":
                self.check_ebooklib_available()
            
            # 设置键盘快捷键
            self.bind("<Control-d>", lambda e: self.start_download())
            self.bind("<F1>", lambda e: self.show_help())
            
            self.logger.info("GUI初始化完成")
            
        except Exception as e:
            import traceback
            print(f"GUI初始化失败: {str(e)}")
            print(traceback.format_exc())
            # 失败时尝试显示消息框
            try:
                messagebox.showerror("初始化错误", f"应用程序初始化失败:\n{str(e)}")
            except:
                pass
            raise  # 重新抛出异常，让全局异常处理器捕获
    
    def setup_icon(self):
        """设置应用图标"""
        icon_paths = [
            "icon.ico",                        # 当前目录
            os.path.join("assets", "icon.ico"), # assets子目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")  # 脚本目录
        ]
        
        for icon_path in icon_paths:
            try:
                if os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
                    self.logger.info(f"成功加载图标: {icon_path}")
                    return
            except Exception as e:
                self.logger.warning(f"加载图标失败: {icon_path} - {str(e)}")
        
        # 如果没有找到图标，使用默认Tk图标
        self.logger.info("未找到图标文件，使用默认图标")
    
    def setup_style(self):
        """设置界面样式和主题"""
        style = ttk.Style()
        current_theme = style.theme_use()
        
        # 尝试使用更现代的主题
        available_themes = style.theme_names()
        preferred_themes = ['clam', 'alt', 'vista', 'xpnative', 'winnative']
        
        for theme in preferred_themes:
            if theme in available_themes:
                try:
                    style.theme_use(theme)
                    self.logger.info(f"使用主题: {theme}")
                    break
                except:
                    # 如果主题切换失败，回退到当前主题
                    style.theme_use(current_theme)
        
        # 自定义按钮样式
        style.configure('Primary.TButton', font=('Helvetica', 10, 'bold'))
        style.configure('Secondary.TButton', font=('Helvetica', 10))
        
        # 配置进度条样式
        style.configure("TProgressbar", thickness=20)
    
    def load_settings(self):
        """加载上次的设置"""
        try:
            import json
            settings_path = os.path.join(os.path.expanduser("~"), ".tomato_novel_settings.json")
            
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                # 应用设置
                if 'threads' in settings and settings['threads']:
                    self.threads_var.set(str(settings['threads']))
                if 'format' in settings and settings['format']:
                    self.format_var.set(settings['format'])
                if 'last_path' in settings and settings['last_path']:
                    self.last_settings['save_path'] = settings['last_path']
                    
                self.logger.info("成功加载配置")
        except Exception as e:
            self.logger.warning(f"加载配置失败: {str(e)}")
    
    def save_settings(self):
        """保存当前设置供下次使用"""
        try:
            import json
            settings = {
                'threads': int(self.threads_var.get()),
                'format': self.format_var.get(),
                'last_path': self.save_path_entry.get() if hasattr(self, 'save_path_entry') else "",
                'last_used': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            settings_path = os.path.join(os.path.expanduser("~"), ".tomato_novel_settings.json")
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            self.logger.info("成功保存配置")
        except Exception as e:
            self.logger.warning(f"保存配置失败: {str(e)}")
    
    def on_format_changed(self, *args):
        """响应格式选择变化"""
        if self.format_var.get() == "epub":
            self.check_ebooklib_available()
    
    def check_ebooklib_available(self):
        """检查是否安装了ebooklib库"""
        try:
            import ebooklib
            return True
        except ImportError:
            # 提示安装
            if messagebox.askyesno("需要安装依赖",
                                 "导出EPUB格式需要安装ebooklib库。\n是否现在安装？"):
                self.install_ebooklib()
            return False
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """番茄小说下载器 - 使用说明

1. 小说ID：从番茄小说网址中获取，通常为数字
   例如：https://fanqienovel.com/page/12345 中的12345

2. 保存路径：小说文件保存的目录，默认在程序所在目录的novels文件夹

3. 线程数：下载使用的线程数量，默认为5
   • 线程数越多，下载速度可能越快
   • 但过多的线程可能导致被网站限制

4. 输出格式：
   • TXT格式：普通文本文件，适合任何阅读器
   • EPUB格式：电子书格式，适合Kindle等电子书阅读器
     (需要安装ebooklib库)

快捷键：
• Ctrl+D：开始下载
• F1：显示帮助

版本：{version}"""
        
        messagebox.showinfo("使用说明", help_text.format(version=self.version))
            
    def create_widgets(self):
        """创建并布局GUI控件"""
        # 创建顶部菜单栏
        self.create_menu()
        
        # 创建主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板 - 输入信息
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建输入区域
        input_frame = ttk.LabelFrame(left_panel, text="下载设置", padding="10")
        input_frame.pack(fill=tk.BOTH, expand=False, padx=0, pady=5)
        
        # 小说ID输入 - 使用更现代的布局
        id_frame = ttk.Frame(input_frame)
        id_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(id_frame, text="小说ID:", width=10).pack(side=tk.LEFT, padx=(0,5))
        
        id_entry_frame = ttk.Frame(id_frame)
        id_entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.book_id_entry = ttk.Entry(id_entry_frame)
        self.book_id_entry.pack(fill=tk.X, expand=True)
        
        # ID提示
        id_tip_frame = ttk.Frame(input_frame)
        id_tip_frame.pack(fill=tk.X, pady=(0,8))
        ttk.Label(id_tip_frame, text="提示: 从番茄小说网址中获取，例如 fanqienovel.com/page/12345 中的12345",
                 font=("Arial", 8), foreground="#666666").pack(side=tk.LEFT, padx=(10,0))
                 
        # 保存路径输入
        path_frame = ttk.Frame(input_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="保存路径:", width=10).pack(side=tk.LEFT, padx=(0,5))
        
        self.save_path_entry = ttk.Entry(path_frame)
        self.save_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        
        # 设置默认保存路径（尝试从上次设置中恢复）
        default_path = os.path.join(os.getcwd(), "novels")
        if hasattr(self, 'last_settings') and 'save_path' in self.last_settings:
            default_path = self.last_settings['save_path']
        self.save_path_entry.insert(0, default_path)
        
        browse_button = ttk.Button(path_frame, text="浏览...", command=self.browse_folder, width=8)
        browse_button.pack(side=tk.LEFT)
        
        # 创建设置框架
        settings_frame = ttk.Frame(input_frame)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 左侧 - 线程设置
        threads_settings = ttk.LabelFrame(settings_frame, text="线程数")
        threads_settings.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        threads_frame = ttk.Frame(threads_settings)
        threads_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 使用更直观的滑块来设置线程数
        self.threads_scale = ttk.Scale(threads_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                                      variable=self.threads_var, command=self.update_threads_label)
        self.threads_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.threads_label = ttk.Label(threads_frame, text=f"{self.threads_var.get()} 线程", width=8)
        self.threads_label.pack(side=tk.LEFT, padx=5)
        
        # 右侧 - 格式设置
        format_settings = ttk.LabelFrame(settings_frame, text="输出格式")
        format_settings.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        format_frame = ttk.Frame(format_settings)
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(format_frame, text="TXT文档", value="txt",
                        variable=self.format_var).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Radiobutton(format_frame, text="EPUB电子书", value="epub",
                        variable=self.format_var).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Radiobutton(format_frame, text="分章节TXT", value="chapter",
                        variable=self.format_var).pack(side=tk.LEFT, padx=5, pady=2)
        
        # 操作按钮区域
        action_frame = ttk.Frame(input_frame)
        action_frame.pack(fill=tk.X, pady=(10,0))
        
        help_button = ttk.Button(action_frame, text="帮助", command=self.show_help, width=10, style='Secondary.TButton')
        help_button.pack(side=tk.LEFT, padx=5)
        
        self.download_button = ttk.Button(action_frame, text="开始下载 (Ctrl+D)",
                                         command=self.start_download, width=20, style='Primary.TButton')
        self.download_button.pack(side=tk.RIGHT, padx=5)
        
        # 右侧面板 - 进度和日志
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(right_panel, text="下载进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0,5))
        
        # 进度信息显示
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill=tk.X, pady=(0,5))
        
        self.progress_var = tk.IntVar()
        self.progress_percent = ttk.Label(progress_info_frame, text="0%", width=5)
        self.progress_percent.pack(side=tk.LEFT, padx=(0,5))
        
        self.progress_bar = ttk.Progressbar(progress_info_frame, orient=tk.HORIZONTAL,
                                           length=100, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 进度状态
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X, pady=(0,5))
        
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT, padx=(0,5))
        self.progress_label = ttk.Label(status_frame, text="准备就绪")
        self.progress_label.pack(side=tk.LEFT, fill=tk.X)
        
        # 日志区域
        log_frame = ttk.LabelFrame(right_panel, text="下载日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建带滚动条的文本框
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_container, wrap=tk.WORD, height=12)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED, font=("Consolas", 9))
        
        # 自定义日志标签样式
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("warning", foreground="orange")
        
        scrollbar = ttk.Scrollbar(log_container, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 底部信息栏
        footer_frame = ttk.Frame(self)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        version_label = ttk.Label(footer_frame, text=f"版本: {self.version}", font=("Arial", 8))
        version_label.pack(side=tk.LEFT)
        
        info_label = ttk.Label(footer_frame,
                              text="作者: POf-L | 基于DlmOS驱动 | GitHub: github.com/POf-L/Fanqie-Tomato-Downloader",
                              font=("Arial", 8), foreground="#666666")
        info_label.pack(side=tk.RIGHT)
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="开始下载", command=self.start_download, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        
        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="保存当前设置", command=self.save_settings)
        settings_menu.add_command(label="重置设置", command=self.reset_settings)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help, accelerator="F1")
        help_menu.add_command(label="关于", command=self.show_about)
    
    def update_threads_label(self, *args):
        """更新线程数量显示标签"""
        try:
            thread_count = int(float(self.threads_var.get()))
            self.threads_var.set(str(thread_count))  # 确保是整数
            self.threads_label.config(text=f"{thread_count} 线程")
        except:
            self.threads_label.config(text="错误")
    
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("关于番茄小说下载器",
                           f"番茄小说下载器 - 精简版 v{self.version}\n\n"
                           "这是一个简单的工具，用于从番茄小说下载您喜欢的小说\n\n"
                           "作者: POf-L\n"
                           "GitHub: github.com/POf-L/Fanqie-Tomato-Downloader")
    
    def reset_settings(self):
        """重置所有设置到默认值"""
        if messagebox.askyesno("确认", "确定要重置所有设置到默认值吗？"):
            self.threads_var.set("5")
            self.format_var.set("txt")
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, os.path.join(os.getcwd(), "novels"))
            
            # 更新线程数滑块标签
            self.update_threads_label()
            
            # 记录操作
            self.add_log("已重置所有设置到默认值", "info")
        
    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, folder_path)
            
    def start_download(self):
        if self.is_downloading:
            messagebox.showinfo("提示", "下载已在进行中")
            return
            
        book_id = self.book_id_entry.get().strip()
        save_path = self.save_path_entry.get().strip()
        
        if not book_id:
            messagebox.showerror("错误", "请输入小说ID")
            return
            
        if not save_path:
            messagebox.showerror("错误", "请选择保存路径")
            return

        # 检查EPUB格式所需的库
        output_format = self.format_var.get()
        if output_format == "epub":
            try:
                import ebooklib
            except ImportError:
                response = messagebox.askyesno("缺少依赖", "转换为EPUB格式需要安装'ebooklib'库。是否现在安装？")
                if response:
                    self.install_ebooklib()
                    # 安装后尝试再次导入
                    try:
                        import ebooklib
                    except ImportError:
                        messagebox.showerror("错误", "安装ebooklib失败，请尝试手动安装：pip install ebooklib")
                        return
                else:
                    return
            
        # 确保保存路径存在
        try:
            os.makedirs(save_path, exist_ok=True)
        except Exception as e:
            messagebox.showerror("错误", f"创建保存路径失败: {str(e)}")
            return
            
        # 准备下载
        self.is_downloading = True
        self.download_button.config(text="下载中...", state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label.config(text="开始下载...")
        
        # 清空日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 重定向标准输出到日志文本框
        self.stdout_redirect = RedirectText(self.log_text)
        sys.stdout = self.stdout_redirect
        
        # 替换tqdm类，使其更新GUI进度条
        novel_downloader.tqdm = lambda *args, **kwargs: CustomTqdm(
            *args, **kwargs, progress_var=self.progress_var, progress_label=self.progress_label
        )
        
        # 设置线程数和输出格式
        threads = int(self.threads_var.get())
        output_format = self.format_var.get()
        novel_downloader.MAX_WORKERS = threads
        novel_downloader.OUTPUT_FORMAT = output_format
        
        # 在新线程中运行下载
        self.download_thread = threading.Thread(target=self.run_download, args=(book_id, save_path, output_format))
        self.download_thread.daemon = True
        self.download_thread.start()
        
    def run_download(self, book_id, save_path, output_format):
        try:
            print(f"开始下载小说 ID: {book_id}")
            print(f"保存路径: {save_path}")
            print(f"使用线程数: {novel_downloader.MAX_WORKERS}")
            print(f"输出格式: {output_format}")
            
            # 确保保存路径存在
            try:
                os.makedirs(save_path, exist_ok=True)
                print(f"保存路径确认: {save_path}")
            except Exception as e:
                raise Exception(f"创建保存目录失败: {str(e)}")
            
            try:
                novel_downloader.Run(book_id, save_path)
                self.after(100, self.download_complete, "下载完成！")
            except AttributeError as e:
                if "'NoneType' object has no attribute" in str(e):
                    error_msg = f"下载失败: 可能是某个章节内容获取失败或文件写入失败。详细错误: {str(e)}"
                    print(error_msg)
                    self.after(100, self.download_complete, error_msg)
                else:
                    raise
        except Exception as e:
            error_msg = f"下载出错: {str(e)}"
            print(f"错误详情: {type(e).__name__}: {str(e)}")
            self.after(100, self.download_complete, error_msg)
            
    def download_complete(self, message):
        try:
            self.is_downloading = False
            self.download_button.config(text="开始下载", state=tk.NORMAL)
            self.progress_label.config(text=message)
            
            # 尝试恢复标准输出
            try:
                if sys.stdout != sys.__stdout__:
                    sys.stdout = sys.__stdout__
            except Exception as e:
                print(f"恢复标准输出时出错: {str(e)}")
                
            # 避免重复显示同一消息
            if "下载完成" in message:
                # 如果是EPUB格式，显示更详细的信息
                if hasattr(self, 'format_var') and self.format_var.get() == "epub":
                    messagebox.showinfo("下载状态", f"{message}\n\nEPUB文件应该已保存到指定目录。\n如果需要查看，请打开保存目录。")
                else:
                    messagebox.showinfo("下载状态", message)
            else:
                # 如果是错误信息，显示更多细节
                messagebox.showinfo("下载状态", f"{message}\n\n请检查小说ID是否正确，或者稍后重试。")
        except Exception as e:
            messagebox.showinfo("下载状态", f"下载过程完成，但状态更新时出错: {str(e)}")
    
    def install_ebooklib(self):
        """安装ebooklib库"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "正在安装ebooklib库...\n")
        self.log_text.config(state=tk.DISABLED)
        
        try:
            import subprocess
            import sys
            
            # 禁用下载按钮，防止安装过程中操作
            original_state = self.download_button["state"]
            self.download_button.config(state=tk.DISABLED)
            
            # 显示详细的安装步骤
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"正在使用 {sys.executable} 安装...\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.update()  # 立即更新UI
            
            # 运行pip安装命令
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "ebooklib", "--upgrade"],
                capture_output=True,
                text=True,
                timeout=60  # 设置超时，防止无限等待
            )
            
            # 处理安装结果
            self.log_text.config(state=tk.NORMAL)
            if result.returncode == 0:
                self.log_text.insert(tk.END, "✓ 安装成功！\n")
                self.log_text.insert(tk.END, "现在可以将小说转换为EPUB格式。\n")
                messagebox.showinfo("安装成功", "ebooklib库安装成功！现在可以使用EPUB格式导出小说。")
            else:
                error_info = result.stderr or "未知错误"
                self.log_text.insert(tk.END, f"✗ 安装失败: \n{error_info}\n")
                self.log_text.insert(tk.END, "请检查网络连接或尝试手动安装：\n")
                self.log_text.insert(tk.END, "pip install ebooklib\n")
                messagebox.showerror("安装失败", f"安装ebooklib库失败，详细信息已在日志中显示。\n\n可能原因：网络问题或权限不足。")
            
            self.log_text.see(tk.END)  # 滚动到最新日志
            self.log_text.config(state=tk.DISABLED)
            
        except subprocess.TimeoutExpired:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, "安装超时，可能是网络问题或服务器响应慢。\n")
            self.log_text.config(state=tk.DISABLED)
            messagebox.showerror("安装超时", "安装ebooklib库超时，请检查网络连接后重试。")
            
        except Exception as e:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"安装过程出错: {str(e)}\n")
            self.log_text.config(state=tk.DISABLED)
            messagebox.showerror("安装错误", f"安装ebooklib库时出错: {str(e)}")
            
        finally:
            # 恢复下载按钮状态
            try:
                self.download_button.config(state=original_state)
            except:
                self.download_button.config(state=tk.NORMAL)
        
    def on_closing(self):
        try:
            if self.is_downloading:
                if messagebox.askyesno("确认", "下载正在进行中，确定要退出吗？"):
                    try:
                        # 恢复标准输出
                        if sys.stdout != sys.__stdout__:
                            sys.stdout = sys.__stdout__
                    except Exception as e:
                        print(f"关闭时恢复标准输出错误: {str(e)}", file=sys.__stdout__)
                    self.destroy()
            else:
                self.destroy()
        except Exception as e:
            print(f"关闭应用程序时出错: {str(e)}", file=sys.__stdout__)
            # 强制关闭
            self.destroy()

def check_environment():
    """检查系统环境和依赖"""
    issues = []
    
    # 检查Python版本
    import platform
    py_version = platform.python_version_tuple()
    if int(py_version[0]) < 3 or (int(py_version[0]) == 3 and int(py_version[1]) < 6):
        issues.append(f"当前Python版本 ({platform.python_version()}) 过低，建议使用Python 3.6或更高版本")
    
    # 检查tk是否可用
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
    except Exception as e:
        issues.append(f"Tkinter初始化失败: {str(e)}")
    
    # 检查临时文件目录是否可写
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(delete=True) as f:
            f.write(b"test")
    except Exception as e:
        issues.append(f"临时目录写入测试失败: {str(e)}")
    
    return issues

def setup_logging():
    """设置基本日志记录"""
    import logging
    import os
    import tempfile
    
    # 设置日志文件路径
    log_dir = os.path.join(tempfile.gettempdir(), "tomato_novel_downloader")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app_log.txt")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("TomatoNovelDownloader")

if __name__ == "__main__":
    # 设置异常钩子，捕获未处理的异常
    import sys
    import traceback
    
    # 设置日志
    logger = setup_logging()
    logger.info("应用程序启动")
    
    # 检查环境
    issues = check_environment()
    if issues:
        from tkinter import messagebox
        warn_msg = "检测到以下潜在问题，程序可能无法正常运行:\n\n" + "\n".join(issues)
        logger.warning(warn_msg)
        messagebox.showwarning("环境检查警告", warn_msg)
    
    # 处理未捕获的异常
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # 正常的Ctrl+C终止，使用默认处理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        # 记录未捕获的异常
        logger.error("未捕获的异常",
                     exc_info=(exc_type, exc_value, exc_traceback))
        
        # 显示错误对话框
        import tkinter as tk
        from tkinter import messagebox
        if tk._default_root:
            error_message = f"发生未预期的错误:\n{exc_type.__name__}: {exc_value}"
            messagebox.showerror("程序错误", error_message)
    
    # 设置全局异常处理器
    sys.excepthook = handle_exception
    
    try:
        # 启动应用程序
        app = NovelDownloaderGUI()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)  # 确保关闭处理器已设置
        logger.info("GUI初始化完成")
        app.mainloop()
    except Exception as e:
        logger.error(f"应用程序启动失败: {str(e)}", exc_info=True)
        from tkinter import messagebox
        messagebox.showerror("启动错误", f"应用程序启动失败: {str(e)}")
    finally:
        # 确保资源被清理
        logger.info("应用程序关闭")
