import urllib.parse

def extract_book_id(url):
    # 解析 URL
    parsed_url = urllib.parse.urlparse(url)
    
    # 解析查询参数
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    # 提取 book_id
    book_id = query_params.get('book_id', [None])[0]
    
    return book_id

# 提示用户输入 URL
user_url = input("请输入包含 book_id 的 URL: ")

# 提取 book_id
book_id = extract_book_id(user_url)

if book_id:
    print(f"提取的 book_id 是: {book_id}")
else:
    print("未找到 book_id，请检查 URL 是否正确。")