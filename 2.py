import time
import requests
import bs4
import re
import os
import random
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from lxml import etree
from tqdm import tqdm
import ebooklib
from ebooklib import epub

# 全局变量
cookie_path = "cookie.json"
MAX_WORKERS = 5  # 默认线程数
OUTPUT_FORMAT = "txt"  # 默认输出格式: txt 或 epub

# 获取随机User-Agent
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.47",
    ]
    return random.choice(user_agents)

# 获取或加载Cookie
def get_cookie():
    bas = 1000000000000000000
    for i in range(random.randint(bas * 6, bas * 8), bas * 9):
        time.sleep(random.randint(50, 150) / 1000)
        cookie = 'novel_web_id=' + str(i)
        headers = {
            'User-Agent': get_random_user_agent(),
            'cookie': cookie
        }
        try:
            response = requests.get('https://fanqienovel.com', headers=headers, timeout=10)
            if response.status_code == 200 and len(response.text) > 200:
                with open(cookie_path, 'w', encoding='utf-8') as f:
                    json.dump(cookie, f)
                print(f"cookie已生成: {cookie}")
                return cookie
        except Exception as e:
            print(f"请求失败: {e}")
    return None

# 模拟浏览器请求
def get_headers():
    return {
        "User-Agent": get_random_user_agent(),
        "Cookie": get_cookie()
    }

# 加密内容解析
CODE_ST = 58344
CODE_ED = 58715
charset = ['D', '在', '主', '特', '家', '军', '然', '表', '场', '4', '要', '只', 'v', '和', '?', '6', '别', '还', 'g',
           '现', '儿', '岁', '?', '?', '此', '象', '月', '3', '出', '战', '工', '相', 'o', '男', '首', '失', '世', 'F',
           '都', '平', '文', '什', 'V', 'O', '将', '真', 'T', '那', '当', '?', '会', '立', '些', 'u', '是', '十', '张',
           '学', '气', '大', '爱', '两', '命', '全', '后', '东', '性', '通', '被', '1', '它', '乐', '接', '而', '感',
           '车', '山', '公', '了', '常', '以', '何', '可', '话', '先', 'p', 'i', '叫', '轻', 'M', '士', 'w', '着', '变',
           '尔', '快', 'l', '个', '说', '少', '色', '里', '安', '花', '远', '7', '难', '师', '放', 't', '报', '认',
           '面', '道', 'S', '?', '克', '地', '度', 'I', '好', '机', 'U', '民', '写', '把', '万', '同', '水', '新', '没',
           '书', '电', '吃', '像', '斯', '5', '为', 'y', '白', '几', '日', '教', '看', '但', '第', '加', '候', '作',
           '上', '拉', '住', '有', '法', 'r', '事', '应', '位', '利', '你', '声', '身', '国', '问', '马', '女', '他',
           'Y', '比', '父', 'x', 'A', 'H', 'N', 's', 'X', '边', '美', '对', '所', '金', '活', '回', '意', '到', 'z',
           '从', 'j', '知', '又', '内', '因', '点', 'Q', '三', '定', '8', 'R', 'b', '正', '或', '夫', '向', '德', '听',
           '更', '?', '得', '告', '并', '本', 'q', '过', '记', 'L', '让', '打', 'f', '人', '就', '者', '去', '原', '满',
           '体', '做', '经', 'K', '走', '如', '孩', 'c', 'G', '给', '使', '物', '?', '最', '笑', '部', '?', '员', '等',
           '受', 'k', '行', '一', '条', '果', '动', '光', '门', '头', '见', '往', '自', '解', '成', '处', '天', '能',
           '于', '名', '其', '发', '总', '母', '的', '死', '手', '入', '路', '进', '心', '来', 'h', '时', '力', '多',
           '开', '己', '许', 'd', '至', '由', '很', '界', 'n', '小', '与', 'Z', '想', '代', '么', '分', '生', '口',
           '再', '妈', '望', '次', '西', '风', '种', '带', 'J', '?', '实', '情', '才', '这', '?', 'E', '我', '神', '格',
           '长', '觉', '间', '年', '眼', '无', '不', '亲', '关', '结', '0', '友', '信', '下', '却', '重', '己', '老',
           '2', '音', '字', 'm', '呢', '明', '之', '前', '高', 'P', 'B', '目', '太', 'e', '9', '起', '稜', '她', '也',
           'W', '用', '方', '子', '英', '每', '理', '便', '西', '数', '期', '中', 'C', '外', '样', 'a', '海', '们',
           '任']

def interpreter(cc):
    """解析加密内容"""
    bias = cc - CODE_ST
    if 0 <= bias < len(charset):  # 检查bias是否在charset的有效范围内
        if charset[bias] == '?':
            return chr(cc)
        return charset[bias]
    return chr(cc)  

def down_text(it, headers):
    """下载章节内容"""
    max_retries = 3  # 最大重试次数
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 使用新API获取内容
            api_url = f"http://rehaofan.jingluo.love/content?item_id={it}"
            response = requests.get(api_url, headers=headers, timeout=10)  # 超时时间
            data = response.json()
            
            if data.get("code") == 0:
                content = data.get("data", {}).get("content", "")
                # 清理HTML标签并保留段落结构
                content = re.sub(r'<header>.*?</header>', '', content, flags=re.DOTALL)
                content = re.sub(r'<footer>.*?</footer>', '', content, flags=re.DOTALL)
                content = re.sub(r'</?article>', '', content)
                content = re.sub(r'<p idx="\d+">', '\n', content)
                content = re.sub(r'</p>', '\n', content)
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\n{2,}', '\n', content).strip()
                content = '\n'.join(['    ' + line if line.strip() else line for line in content.split('\n')])
                
                return content
        except requests.exceptions.RequestException as e:
            retry_count += 1
            print(f"网络请求失败，正在重试({retry_count}/{max_retries}): {str(e)}")
            time.sleep(2 * retry_count)  # 重试延迟时间
        except Exception as e:
            retry_count += 1
            print(f"下载出错，正在重试({retry_count}/{max_retries}): {str(e)}")
            time.sleep(1 * retry_count)
    
    print("达到最大重试次数，下载失败")
    return None

def get_book_info(book_id, headers):
    """获取书籍基本信息"""
    try:
        url = f'https://fanqienovel.com/page/{book_id}'
        response = requests.get(url, headers=headers, timeout=10)
        soup = bs4.BeautifulSoup(response.text, 'lxml')
        
        # 获取书名
        name_element = soup.select_one("h1.info-name")
        name = name_element.text.strip() if name_element else "未知书名"
        
        # 获取作者名
        author_element = soup.select_one("div.author-link")
        author_name = author_element.text.strip() if author_element else "未知作者"
        
        # 获取简介
        desc_element = soup.select_one("div.abstract.full")
        if not desc_element:
            desc_element = soup.select_one("div.abstract")
        description = desc_element.text.strip() if desc_element else ""
        
        print(f"获取到书籍信息: {name} - {author_name}")
        return name, author_name, description
    except Exception as e:
        print(f"获取书籍信息失败: {str(e)}")
        return None, None, None

def extract_chatper_titles(soup):
    """提取章节标题列表"""
    titles = []
    chapter_items = soup.select("div.chapter-item")
    
    for item in chapter_items:
        title_element = item.select_one("div.chapter-title")
        if title_element and title_element.a:
            title = title_element.a.text.strip()
            titles.append(title)
        else:
            titles.append(f"第{len(titles)+1}章")
    
    return titles

def funLog(text, headers):
    """解析章节内容"""
    content = down_text(text.url.split('/')[-1], headers)
    return content

def extract_chatper_titles(soup):
    """提取章节标题"""
    titles = []
    for item in soup.select('div.chapter-item'):
        title = item.get_text(strip=True)
        if title:
            titles.append(title)
    return titles

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

def create_epub_book(name, author_name, description, chapters_data, save_path):
    """创建EPUB电子书"""
    # 创建EPUB实例
    book = epub.EpubBook()
    
    # 设置基本信息
    book.set_identifier(f'fanqie_{name}')
    book.set_title(name)
    book.set_language('zh-CN')
    if author_name:
        book.add_author(author_name)
    
    # 添加简介
    if description:
        intro = epub.EpubHtml(title='简介', file_name='intro.xhtml')
        intro.content = f'<html><body><h1>内容简介</h1><p>{description}</p></body></html>'
        book.add_item(intro)
    
    # 添加章节
    chapters = []
    toc = []
    
    # 添加CSS样式
    style = '''
    @namespace epub "http://www.idpf.org/2007/ops";
    body {
        font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
        line-height: 1.6;
        padding: 5%;
    }
    h1 {
        text-align: center;
        font-weight: bold;
        margin-bottom: 1em;
    }
    p {
        text-indent: 2em;
        margin: 0.5em 0;
    }
    '''
    css = epub.EpubItem(uid="style", file_name="style/style.css", media_type="text/css", content=style)
    book.add_item(css)
    
    # 遍历章节数据添加到电子书
    for i, (title, content) in enumerate(chapters_data):
        chapter = epub.EpubHtml(title=title, file_name=f'chapter_{i+1}.xhtml', lang='zh-CN')
        
        # 格式化章节内容为HTML
        formatted_content = content.replace('\n', '</p><p>')
        chapter_html = f'<html><body><h1>{title}</h1><p>{formatted_content}</p></body></html>'
        chapter.content = chapter_html
        
        # 添加CSS
        chapter.add_item(css)
        
        # 添加到书中
        book.add_item(chapter)
        chapters.append(chapter)
        toc.append(epub.Link(f'chapter_{i+1}.xhtml', title, f'chapter_{i+1}'))
    
    # 添加目录
    book.toc = toc
    
    # 添加默认的NCX和NAV
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # 设置书脊
    spine = ['nav']
    if description:
        spine.append('intro')
    spine.extend(chapters)
    book.spine = spine
    
    # 保存EPUB文件
    output_file_path = os.path.join(save_path, f"{name}.epub")
    epub.write_epub(output_file_path, book, {})
    
    return output_file_path

def download_chapter(div, headers, save_path, book_name, titles, i, total, chapters_data=None):
    """下载单个章节"""
    if not div.a:
        print(f"第 {i + 1} 章没有链接，跳过")
        return None
    
    detail_url = f"https://fanqienovel.com{div.a['href']}"
    response = requests.get(detail_url, headers=headers)
    content = down_text(response.url.split('/')[-1], headers)

    if content:
        if OUTPUT_FORMAT == "txt":
            output_file_path = os.path.join(save_path, f"{book_name}.txt")
            with open(output_file_path, 'a', encoding='utf-8') as f:
                f.write(f'{titles[i]}\n')
                f.write(content + '\n\n')
        elif OUTPUT_FORMAT == "epub" and chapters_data is not None:
            # 为EPUB格式收集章节数据
            chapters_data.append((titles[i], content))
        
        print(f'已下载 {i + 1}/{total}')
        return content
    else:
        print(f"第 {i + 1} 章下载失败")
        return None

def Run(book_id, save_path):
    """运行下载"""
    headers = get_headers()
    
    # 获取书籍信息
    name, author_name, description = get_book_info(book_id, headers)
    if not name:
        print("无法获取书籍信息，请检查小说ID或网络连接。")
        return

    # 获取章节列表
    url = f'https://fanqienovel.com/page/{book_id}'
    response = requests.get(url, headers=headers)
    soup = bs4.BeautifulSoup(response.text, 'lxml')

    li_list = soup.select("div.chapter-item")
    total = len(li_list)
    titles = extract_chatper_titles(soup)

    os.makedirs(save_path, exist_ok=True)

    if OUTPUT_FORMAT == "txt":
        # 创建并写入小说信息
        output_file_path = os.path.join(save_path, f"{name}.txt")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            # 写入书籍信息
            f.write(f'小说名: {name}\n作者: {author_name}\n内容简介: {description}\n\n')

        # 使用多线程下载章节
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for i, div in enumerate(li_list):
                headers = get_headers()
                futures.append(executor.submit(download_chapter, div, headers, save_path, name, titles, i, total))
            
            # 使用进度条
            for _ in tqdm(as_completed(futures), total=total, desc="下载进度"):
                pass

        print(f"小说已下载到: {output_file_path}")
        return output_file_path
    
    elif OUTPUT_FORMAT == "epub":
        chapters_data = []
        
        # 使用多线程下载章节
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for i, div in enumerate(li_list):
                headers = get_headers()
                futures.append(executor.submit(download_chapter, div, headers, save_path, name, titles, i, total, chapters_data))
            
            # 使用进度条
            for _ in tqdm(as_completed(futures), total=total, desc="下载进度"):
                pass
        
        # 创建EPUB文件
        output_file_path = create_epub_book(name, author_name, description, chapters_data, save_path)
        print(f"小说已下载到: {output_file_path}")
        return output_file_path
    
    else:
        print(f"不支持的输出格式: {OUTPUT_FORMAT}，请使用 'txt' 或 'epub'")
        return None
def main():
    global OUTPUT_FORMAT
    
    print("欢迎使用番茄小说下载器精简版！")
    print("作者：Dlmos（Dlmily）")
    print("基于DlmOS驱动")
    print("Github：https://github.com/Dlmily/Tomato-Novel-Downloader-Lite")
    print("参考代码：https://github.com/ying-ck/fanqienovel-downloader/blob/main/src/ref_main.py")
    print("赞助/了解新产品：https://afdian.com/a/dlbaokanluntanos")
    print("")
    
    book_id = input("请输入小说 ID：")
    save_path = input("请输入保存路径：")
    
    # 让用户选择输出格式
    while True:
        format_choice = input("请选择输出格式 (1:TXT, 2:EPUB) [默认:1]: ").strip()
        if not format_choice:
            format_choice = "1"
        
        if format_choice == "1":
            OUTPUT_FORMAT = "txt"
            break
        elif format_choice == "2":
            OUTPUT_FORMAT = "epub"
            break
        else:
            print("输入无效，请重新选择")
    
    # 让用户设置线程数
    while True:
        workers = input(f"请设置下载线程数 (1-10) [默认:{MAX_WORKERS}]: ").strip()
        if not workers:
            break
        
        try:
            workers_num = int(workers)
            if 1 <= workers_num <= 10:
                MAX_WORKERS = workers_num
                break
            else:
                print("线程数必须在1-10之间")
        except ValueError:
            print("请输入有效的数字")
    
    print(f"开始下载，输出格式: {OUTPUT_FORMAT.upper()}，线程数: {MAX_WORKERS}")
    Run(book_id, save_path)
    print("下载完成！")

if __name__ == "__main__":
    main()
