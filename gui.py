import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import time
import requests
import bs4
import re
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict

# 全局配置
CONFIG = {
    "max_workers": 5,
    "max_retries": 3,
    "request_timeout": 15,
    "status_file": "chapter.json",
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
}

def get_headers(cookie=None):
    """生成随机请求头"""
    return {
        "User-Agent": random.choice(CONFIG["user_agents"]),
        "Cookie": cookie if cookie else get_cookie()
    }

def get_cookie():
    """生成或加载Cookie"""
    cookie_path = "cookie.json"
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # 生成新Cookie
    for _ in range(10):
        novel_web_id = random.randint(10**18, 10**19-1)
        cookie = f'novel_web_id={novel_web_id}'
        try:
            resp = requests.get(
                'https://fanqienovel.com',
                headers={"User-Agent": random.choice(CONFIG["user_agents"])},
                cookies={"novel_web_id": str(novel_web_id)},
                timeout=10
            )
            if resp.ok:
                with open(cookie_path, 'w') as f:
                    json.dump(cookie, f)
                return cookie
        except Exception as e:
            print(f"Cookie生成失败: {str(e)}")
            time.sleep(0.5)
    raise Exception("无法获取有效Cookie")

def down_text(it):
    """下载章节内容"""
    max_retries = CONFIG.get('max_retries', 3)
    retry_count = 0
    content = ""
    
    while retry_count < max_retries:
        try:
            api_url = f"https://api.cenguigui.cn/api/tomato/content.php?item_id={it}"
            response = requests.get(api_url, timeout=CONFIG["request_timeout"])
            data = response.json()
            
            if data.get("code") == 200:
                content = data.get("data", {}).get("content", "")
                
                # 移除HTML标签
                content = re.sub(r'<header>.*?</header>', '', content, flags=re.DOTALL)
                content = re.sub(r'<footer>.*?</footer>', '', content, flags=re.DOTALL)
                content = re.sub(r'</?article>', '', content)
                content = re.sub(r'<p idx="\d+">', '\n', content)
                content = re.sub(r'</p>', '\n', content)
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\\u003c|\\u003e', '', content)
                
                # 处理可能的重复章节标题行
                title = data.get("data", {}).get("title", "")
                if title and content.startswith(title):
                    content = content[len(title):].lstrip()
                
                content = re.sub(r'\n{2,}', '\n', content).strip()
                content = '\n'.join(['    ' + line if line.strip() else line for line in content.split('\n')])
                break
        except Exception as e:
            print(f"请求失败: {str(e)}, 重试第{retry_count + 1}次...")
            retry_count += 1
            time.sleep(1 * retry_count)
    
    return content

def get_book_info(book_id, headers):
    """获取书名、作者、简介"""
    url = f'https://fanqienovel.com/page/{book_id}'
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"网络请求失败，状态码: {response.status_code}")
        return None, None, None

    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    
    # 获取书名
    name_element = soup.find('h1')
    name = name_element.text if name_element else "未知书名"
    
    # 获取作者
    author_name_element = soup.find('div', class_='author-name')
    author_name = None
    if author_name_element:
        author_name_span = author_name_element.find('span', class_='author-name-text')
        author_name = author_name_span.text if author_name_span else "未知作者"
    
    # 获取简介
    description_element = soup.find('div', class_='page-abstract-content')
    description = None
    if description_element:
        description_p = description_element.find('p')
        description = description_p.text if description_p else "无简介"
    
    return name, author_name, description

def extract_chapters(soup):
    """解析章节列表"""
    chapters = []
    for idx, item in enumerate(soup.select('div.chapter-item')):
        a_tag = item.find('a')
        if not a_tag:
            continue
        
        raw_title = a_tag.get_text(strip=True)
        
        # 特殊章节
        if re.match(r'^(番外|特别篇|if线)\s*', raw_title):
            final_title = raw_title
        else:
            clean_title = re.sub(
                r'^第[一二三四五六七八九十百千\d]+章\s*',
                '', 
                raw_title
            ).strip()
            final_title = f"第{idx+1}章 {clean_title}"
        
        chapters.append({
            "id": a_tag['href'].split('/')[-1],
            "title": final_title,
            "url": f"https://fanqienovel.com{a_tag['href']}",
            "index": idx
        })
    
    return chapters

class NovelDownloaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("番茄小说下载器")
        self.setup_ui()
        self.is_downloading = False
        self.downloaded_chapters = set()
        self.content_cache = OrderedDict()
    
    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 小说ID输入
        ttk.Label(main_frame, text="小说ID:").grid(row=0, column=0, sticky=tk.W)
        self.novel_id = ttk.Entry(main_frame, width=40)
        self.novel_id.grid(row=0, column=1, padx=5, pady=5)
        
        # 保存路径
        ttk.Label(main_frame, text="保存路径:").grid(row=1, column=0, sticky=tk.W)
        self.save_path = ttk.Entry(main_frame, width=40)
        self.save_path.insert(0, "downloads")
        self.save_path.grid(row=1, column=1, padx=5, pady=5)
        
        # 浏览按钮
        browse_button = ttk.Button(main_frame, text="浏览", command=self.browse_folder)
        browse_button.grid(row=1, column=2, padx=5)
        
        # 下载按钮
        self.download_button = ttk.Button(main_frame, text="开始下载", command=self.start_download)
        self.download_button.grid(row=1, column=3, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, 
                                          variable=self.progress_var,
                                          maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=3, 
                             sticky=(tk.W, tk.E), pady=5)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=3)
        
        # 日志文本框
        self.log_text = tk.Text(main_frame, height=10, width=60)
        self.log_text.grid(row=4, column=0, columnspan=3, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=4, column=3, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # 配置grid权重
        self.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
    
    def log(self, message):
        """添加日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_idletasks()
    
    def update_progress(self, value, status_text):
        """更新进度和状态"""
        self.progress_var.set(value)
        self.status_label["text"] = status_text
        self.update_idletasks()
    
    def start_download(self):
        """开始下载"""
        if self.is_downloading:
            messagebox.showwarning("提示", "下载正在进行中")
            return
        
        novel_id = self.novel_id.get().strip()
        if not novel_id:
            messagebox.showerror("错误", "请输入小说ID")
            return
        
        save_path = self.save_path.get().strip()
        if not save_path:
            save_path = "downloads"
        
        self.download_button["state"] = "disabled"
        self.is_downloading = True
        self.downloaded_chapters.clear()
        self.content_cache.clear()
        
        threading.Thread(target=self.download_novel, 
                       args=(novel_id, save_path), 
                       daemon=True).start()
    
    def download_novel(self, book_id, save_path):
        """下载小说的具体实现"""
        try:
            headers = get_headers()
            self.log("正在获取书籍信息...")
            
            # 获取书籍信息
            name, author_name, description = get_book_info(book_id, headers)
            if not name:
                raise Exception("无法获取书籍信息，请检查小说ID或网络连接")
            
            self.log(f"书名：《{name}》")
            self.log(f"作者：{author_name}")
            self.log(f"简介：{description}")
            
            # 获取章节列表
            url = f'https://fanqienovel.com/page/{book_id}'
            response = requests.get(url, headers=headers)
            soup = bs4.BeautifulSoup(response.text, 'html.parser')
            
            chapters = extract_chapters(soup)
            if not chapters:
                raise Exception("未找到任何章节")
            
            self.log(f"\n开始下载，共 {len(chapters)} 章")
            os.makedirs(save_path, exist_ok=True)
            
            # 创建文件并写入信息
            output_file = os.path.join(save_path, f"{name}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"书名：《{name}》\n作者：{author_name}\n\n简介：\n{description}\n\n")
            
            # 下载章节
            total_chapters = len(chapters)
            success_count = 0
            
            # 先顺序下载前5章
            for chapter in chapters[:5]:
                content = down_text(chapter["id"])
                if content:
                    self.content_cache[chapter["index"]] = (chapter, content)
                    self.downloaded_chapters.add(chapter["id"])
                    success_count += 1
                    progress = (success_count / total_chapters) * 100
                    self.update_progress(progress, f"正在下载: {success_count}/{total_chapters}")
                    self.log(f"已下载：{chapter['title']}")
            
            # 多线程下载剩余章节
            remaining_chapters = chapters[5:]
            with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
                future_to_chapter = {
                    executor.submit(down_text, chapter["id"]): chapter
                    for chapter in remaining_chapters
                }
                
                for future in as_completed(future_to_chapter):
                    chapter = future_to_chapter[future]
                    try:
                        content = future.result()
                        if content:
                            self.content_cache[chapter["index"]] = (chapter, content)
                            self.downloaded_chapters.add(chapter["id"])
                            success_count += 1
                            self.log(f"已下载：{chapter['title']}")
                    except Exception as e:
                        self.log(f"下载失败：{chapter['title']} - {str(e)}")
                    finally:
                        progress = (success_count / total_chapters) * 100
                        self.update_progress(progress, f"正在下载: {success_count}/{total_chapters}")
            
            # 按顺序写入文件
            self.log("\n正在保存文件...")
            
            # 检查重复章节内容
            processed_contents = set()
            with open(output_file, 'a', encoding='utf-8') as f:
                for index in sorted(self.content_cache.keys()):
                    chapter, content = self.content_cache[index]
                    
                    # 检查内容是否重复
                    content_hash = hash(content)
                    if content_hash in processed_contents:
                        self.log(f"跳过重复章节：{chapter['title']}")
                        continue
                    
                    processed_contents.add(content_hash)
                    f.write(f"\n{chapter['title']}\n\n")
                    f.write(content + "\n\n")
            
            self.update_progress(100, "下载完成！")
            self.log(f"\n下载完成！成功：{success_count}章，失败：{total_chapters - success_count}章")
            self.log(f"文件保存在：{output_file}")
            messagebox.showinfo("完成", f"小说《{name}》下载完成！\n保存路径：{output_file}")
            
        except Exception as e:
            self.log(f"\n错误：{str(e)}")
            self.update_progress(0, f"下载失败: {str(e)}")
            messagebox.showerror("错误", f"下载失败: {str(e)}")
        
        finally:
            self.download_button["state"] = "normal"
            self.is_downloading = False
    
    def on_closing(self):
        """窗口关闭处理"""
        if self.is_downloading:
            if messagebox.askyesno("确认", "下载正在进行中，确定要退出吗？"):
                self.destroy()
        else:
            self.destroy()

    def browse_folder(self):
        """打开文件夹选择对话框"""
        folder_path = filedialog.askdirectory(title="选择保存位置")
        if folder_path:
            self.save_path.delete(0, tk.END)
            self.save_path.insert(0, folder_path)

if __name__ == "__main__":
    app = NovelDownloaderGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()