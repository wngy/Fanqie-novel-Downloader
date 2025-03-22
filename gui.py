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
        self.buffer += string
        # 在UI线程上安全更新
        self.text_widget.after(10, self.update_text_widget)
    
    def update_text_widget(self):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, self.buffer)
        self.text_widget.see(tk.END)  # 自动滚动到最新内容
        self.text_widget.config(state=tk.DISABLED)
        self.buffer = ""

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
        displayed = super().update(n)
        # 限制更新频率，避免UI卡顿
        current_time = time.time()
        if current_time - self._last_update_time > self._update_interval:
            if self.progress_var and hasattr(self.progress_var, 'set'):
                # 在主线程中更新UI
                percentage = int(self.n / self.total * 100) if self.total else 0
                self.progress_var.set(percentage)
                if self.progress_label:
                    text = f"下载进度: {percentage}% ({self.n}/{self.total})"
                    self.progress_label.configure(text=text)
            self._last_update_time = current_time
        return displayed

class NovelDownloaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("番茄小说下载器")
        self.geometry("800x600")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 默认设置
        self.threads_var = tk.StringVar(value="5")
        self.format_var = tk.StringVar(value="txt")
        self.create_widgets()
        self.is_downloading = False
        self.download_thread = None
        
        # 设置图标（如果有的话）
        try:
            self.iconbitmap("icon.ico")
        except:
            pass
            
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建输入区域
        input_frame = ttk.LabelFrame(main_frame, text="输入信息", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 小说ID输入
        ttk.Label(input_frame, text="小说ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.book_id_entry = ttk.Entry(input_frame, width=50)
        self.book_id_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(input_frame, text="(从番茄小说网址中获取)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 保存路径输入
        ttk.Label(input_frame, text="保存路径:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.save_path_entry = ttk.Entry(input_frame, width=50)
        self.save_path_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.save_path_entry.insert(0, os.path.join(os.getcwd(), "novels"))
        browse_button = ttk.Button(input_frame, text="浏览", command=self.browse_folder)
        browse_button.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 线程数选择
        ttk.Label(input_frame, text="线程数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        threads_frame = ttk.Frame(input_frame)
        threads_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        for i in range(1, 11):
            ttk.Radiobutton(threads_frame, text=str(i), value=str(i), variable=self.threads_var).pack(side=tk.LEFT, padx=2)
        
        # 输出格式选择
        ttk.Label(input_frame, text="输出格式:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        format_frame = ttk.Frame(input_frame)
        format_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="TXT", value="txt", variable=self.format_var).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="EPUB", value="epub", variable=self.format_var).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="分章节TXT", value="chapter", variable=self.format_var).pack(side=tk.LEFT, padx=10)
        
        # 下载按钮
        self.download_button = ttk.Button(input_frame, text="开始下载", command=self.start_download)
        self.download_button.grid(row=4, column=1, pady=10)
        
        # 进度条区域
        progress_frame = ttk.LabelFrame(main_frame, text="下载进度", padding="10")
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="准备就绪")
        self.progress_label.pack(anchor=tk.W, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="下载日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, width=80, height=15)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 底部信息
        info_label = ttk.Label(main_frame, text="作者: Dlmos (Dlmily) | 基于DlmOS驱动 | GitHub: https://github.com/Dlmily/Tomato-Novel-Downloader-Lite", font=("Arial", 8))
        info_label.pack(side=tk.BOTTOM, pady=5)
        
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
            novel_downloader.Run(book_id, save_path)
            self.after(100, self.download_complete, "下载完成！")
        except Exception as e:
            self.after(100, self.download_complete, f"下载出错: {str(e)}")
            
    def download_complete(self, message):
        self.is_downloading = False
        self.download_button.config(text="开始下载", state=tk.NORMAL)
        self.progress_label.config(text=message)
        # 恢复标准输出
        sys.stdout = sys.__stdout__
        messagebox.showinfo("下载状态", message)
    
    def install_ebooklib(self):
        """安装ebooklib库"""
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, "正在安装ebooklib库...\n")
            self.log_text.config(state=tk.DISABLED)
            
            import subprocess
            result = subprocess.run([sys.executable, "-m", "pip", "install", "ebooklib"],
                                  capture_output=True, text=True)
            
            self.log_text.config(state=tk.NORMAL)
            if result.returncode == 0:
                self.log_text.insert(tk.END, "安装成功！\n")
            else:
                self.log_text.insert(tk.END, f"安装失败: {result.stderr}\n")
            self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("安装错误", f"安装ebooklib库时出错: {str(e)}")
        
    def on_closing(self):
        if self.is_downloading:
            if messagebox.askyesno("确认", "下载正在进行中，确定要退出吗？"):
                # 恢复标准输出
                sys.stdout = sys.__stdout__
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = NovelDownloaderGUI()
    app.mainloop()