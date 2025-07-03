import random
import time




import os
import json
import requests
import time
import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Tuple
from datetime import datetime
from xml.sax.saxutils import escape

# 飞书API端点
BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuTableReader:
    """飞书多维表格读取器 - ComfyUI 插件"""

    @classmethod
    def INPUT_TYPES(cls):
        """定义输入参数"""
        return {
            "required": {
                "feishu_url": ("STRING", {
                    "multiline": False,
                    "default": "https://mwmxcbkef05.feishu.cn/base/Pn1PbIEv5aAMqasFtOfcmfUgnjf?table=tbloPwjcY41fKSWQ&view=vewqIGFhAv"
                }),
                "table_name": ("STRING", {
                    "multiline": False,
                    "default": "分镜提示词"
                }),
                "app_id": ("STRING", {
                    "multiline": False,
                    "default": "cli_a8b40caa1396d01c"
                }),
                "app_secret": ("STRING", {
                    "multiline": False,
                    "default": "KKgicfl5ZwmlsyHED3ERfcvvBbLlDAFG"
                }),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("xml_file_path", "record_num")
    FUNCTION = "generate_xml_from_table"
    CATEGORY = "Scenes/Batch_Opt"

    def generate_xml_from_table(self, feishu_url: str, table_name: str,
                                app_id: str, app_secret: str) -> Tuple[str, int]:
        """
        读取飞书多维表格中的所有记录并生成XML文件

        参数:
            feishu_url: 飞书多维表格地址
            table_name: 要读取的表格名称
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥

        返回:
            xml_file_path: 生成的XML文件路径
            record_num: 处理的记录条数
        """
        try:
            # 1. 获取访问令牌
            token = self.get_access_token(app_id, app_secret)
            if not token:
                raise RuntimeError("无法获取飞书访问令牌")

            # 2. 解析URL获取base_id和table_id
            url_info = self.parse_url(feishu_url)
            base_id = url_info["base_id"]
            if not base_id:
                raise ValueError("无法从URL中解析base_id")

            # 3. 通过表格名称获取表格ID
            table_id = self.get_table_id_by_name(token, base_id, table_name)
            if not table_id:
                raise ValueError(f"未找到名为 '{table_name}' 的表格")

            # 4. 获取表格的所有记录
            records = self.get_all_table_records(token, base_id, table_id)
            if not records:
                raise RuntimeError(f"表格 '{table_name}' 中没有记录")

            record_num = len(records)

            # 5. 生成XML内容
            xml_content = self.generate_xml_content(records)

            # 6. 保存XML文件
            xml_file_path = self.save_xml_file(xml_content)

            return (xml_file_path, record_num)
        except Exception as e:
            raise RuntimeError(f"生成XML文件失败: {str(e)}")

    def get_access_token(self, app_id: str, app_secret: str) -> str:
        """获取租户访问令牌"""
        url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        payload = {"app_id": app_id, "app_secret": app_secret}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                return result.get("tenant_access_token")
            else:
                raise RuntimeError(f"获取token失败: {result.get('msg')}")
        except Exception as e:
            raise RuntimeError(f"获取访问令牌失败: {str(e)}")

    def parse_url(self, url: str) -> Dict[str, str]:
        """解析飞书多维表格URL获取base_id和table_id"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')

            if 'base' in path_parts:
                base_index = path_parts.index('base')
                base_id = path_parts[base_index + 1] if base_index + 1 < len(path_parts) else None
                table_id = parse_qs(parsed.query).get('table', [''])[0]
                return {"base_id": base_id, "table_id": table_id}
            return {"base_id": None, "table_id": None}
        except Exception:
            return {"base_id": None, "table_id": None}

    def get_table_id_by_name(self, access_token: str, base_id: str, table_name: str) -> str:
        """通过表格名称获取表格ID"""
        url = f"{BASE_URL}/bitable/v1/apps/{base_id}/tables"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                for table in result.get("data", {}).get("items", []):
                    if table.get("name") == table_name:
                        return table.get("table_id")
            return None
        except Exception:
            return None

    def get_all_table_records(self, access_token: str, base_id: str, table_id: str) -> list:
        """获取表格的所有记录（支持分页）"""
        all_records = []
        page_token = None
        page_size = 100  # 每页最大记录数

        while True:
            url = f"{BASE_URL}/bitable/v1/apps/{base_id}/tables/{table_id}/records"
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    data = result.get("data", {})
                    records = data.get("items", [])
                    all_records.extend(records)

                    # 检查是否有更多数据
                    has_more = data.get("has_more", False)
                    page_token = data.get("page_token")

                    if not has_more or not page_token:
                        break
                else:
                    raise RuntimeError(f"获取记录失败: {result.get('msg')}")
            except Exception as e:
                raise RuntimeError(f"获取表格记录时出错: {str(e)}")

        return all_records

    def generate_xml_content(self, records: list) -> str:
        """根据记录生成XML内容"""
        # XML头部
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>', '<scenes>']

        # 添加每条记录作为<scene>节点
        for i, record in enumerate(records, 1):
            fields = record.get("fields", {})

            # 提取字段值并进行XML转义
            scene_desc = escape(fields.get("场景要求", ""))
            prompt1 = escape(fields.get("首画面提示词", ""))
            prompt2 = escape(fields.get("中画面提示词", ""))
            prompt3 = escape(fields.get("尾画面提示词", ""))

            # 构建XML节点
            xml_content.append('<scene>')
            xml_content.append(f'<seq>{i}</seq>')
            xml_content.append(f'<scene_desc>{scene_desc}</scene_desc>')
            xml_content.append(f'<prompt1>{prompt1}</prompt1>')
            xml_content.append(f'<prompt2>{prompt2}</prompt2>')
            xml_content.append(f'<prompt3>{prompt3}</prompt3>')
            xml_content.append('</scene>')

        # XML尾部
        xml_content.append('</scenes>')

        return '\n'.join(xml_content)

    def save_xml_file(self, xml_content: str) -> str:
        """保存XML内容到文件"""
        # 获取当前目录（插件目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 创建输出目录（在插件目录下）
        output_dir = os.path.join(current_dir, "feishu_xml_output")
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名（当前年月日时分秒）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"scenes_{timestamp}.xml"
        filepath = os.path.join(output_dir, filename)

        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # 返回相对路径（相对于插件目录）
        relative_path = os.path.join("feishu_xml_output", filename)
        return relative_path


import os
import xml.etree.ElementTree as ET
import random
import time
from typing import List, Dict, Any, Tuple


class SeedGenerator:
    """随机种子生成器"""

    def __init__(self, mode="random", base_seed=0):
        self.mode = mode
        self.base_seed = base_seed
        self.counter = 0
        self.last_time = int(time.time() * 1000)

    def generate_seed(self):
        """生成随机种子"""
        if self.mode == "random":
            # 基于时间、计数器和随机数的组合生成种子
            current_time = int(time.time() * 1000)
            if current_time == self.last_time:
                self.counter += 1
            else:
                self.counter = 0
                self.last_time = current_time

            seed = (current_time + self.counter) % 0xffffffffffffffff
            seed = seed ^ (random.randint(0, 0xffffffff) << 32)
            return seed & 0xffffffffffffffff
        else:
            # 固定种子模式（基于基础种子递增）
            self.counter += 1
            return (self.base_seed + self.counter) % 0xffffffffffffffff


class XMLBatchSceneReader:
    """XML批量场景提示词读取器 - ComfyUI 插件"""

    @classmethod
    def INPUT_TYPES(cls):
        """定义输入参数"""
        return {
            "required": {
                "xml_path": ("STRING", {
                    "multiline": False,
                    "default": ""
                }),
                "scene_start": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 1000,
                    "display": "起始场景序号"
                }),
                "scene_end": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 1000,
                    "display": "结束场景序号"
                }),
                "seed_mode": (["random", "fixed"], {
                    "default": "random",
                    "display": "种子生成模式"
                }),
                "base_seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "display": "基础种子"
                }),
            },
        }

    RETURN_TYPES = ("JOB",)
    RETURN_NAMES = ("prompt_collections",)
    FUNCTION = "read_batch_scenes"
    CATEGORY = "Scenes/Batch_Opt"

    def read_batch_scenes(self, xml_path: str, scene_start: int, scene_end: int,
                          seed_mode: str, base_seed: int) -> List[Dict[str, Any]]:
        """
        从XML文件中读取指定范围的场景提示词并生成种子

        参数:
            xml_path: XML文件路径（相对于当前工作目录）
            scene_start: 起始场景序号
            scene_end: 结束场景序号
            seed_mode: 种子生成模式
            base_seed: 基础种子

        返回:
            prompt_collections: 包含提示词和种子的集合
        """
        # 创建种子生成器
        seed_generator = SeedGenerator(seed_mode, base_seed)

        # 准备结果集合
        prompt_collections = []

        # 检查文件路径是否有效
        if not xml_path:
            print("⚠️ 警告: XML文件路径为空，返回空集合")
            return (prompt_collections,)

        # 获取当前工作目录（ComfyUI根目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 构建完整路径
        full_path = os.path.join(current_dir, xml_path)

        try:
            # 检查文件是否存在
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"XML文件不存在: {full_path}")

            # 解析XML文件
            tree = ET.parse(full_path)
            root = tree.getroot()

            # 确保场景范围有效
            if scene_start > scene_end:
                scene_start, scene_end = scene_end, scene_start

            # 查找所有场景
            scenes = root.findall('scene')
            if not scenes:
                print("⚠️ 警告: XML文件中未找到任何场景")
                return (prompt_collections,)

            # 处理每个场景
            for scene in scenes:
                # 获取序列号
                seq_element = scene.find('seq')
                if seq_element is None:
                    continue

                try:
                    scene_seq = int(seq_element.text)
                except ValueError:
                    continue

                # 检查是否在指定范围内
                if scene_start <= scene_seq <= scene_end:
                    # 提取提示词
                    prompt1_node = scene.find('prompt1')
                    prompt2_node = scene.find('prompt2')
                    prompt3_node = scene.find('prompt3')

                    # 为每个提示生成种子
                    seed1 = seed_generator.generate_seed()
                    seed2 = seed_generator.generate_seed()
                    seed3 = seed_generator.generate_seed()

                    # 添加到集合
                    if prompt1_node is not None and prompt1_node.text:
                        prompt_collections.append({
                            "prompt": prompt1_node.text,
                            "seed": seed1
                        })

                    if prompt2_node is not None and prompt2_node.text:
                        prompt_collections.append({
                            "prompt": prompt2_node.text,
                            "seed": seed2
                        })

                    if prompt3_node is not None and prompt3_node.text:
                        prompt_collections.append({
                            "prompt": prompt3_node.text,
                            "seed": seed3
                        })

            print(f"✅ 成功读取 {len(prompt_collections)} 个提示词")

        except Exception as e:
            print(f"❌ 读取XML场景失败: {str(e)}")

        return (prompt_collections,)


import random
import json
import requests
import re
from collections import deque


class NewsAPI_Fetcher():
    CATEGORIES = ["business", "entertainment", "general", "health", "science", "sports", "technology", "random"]
    LANGUAGES = ["ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "se", "ud", "zh"]
    SOURCES = ["abc-news", "bbc-news", "cnn", "fox-news", "google-news", "reuters", "the-verge", "time", "wired"]
    API_KEY = "fbf21a3762324da7b2fd6a2c82d51189"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "category": (cls.CATEGORIES, {"default": "random"}),
                "language": (cls.LANGUAGES, {"default": "en"}),
                "news_nums": ("INT", {"default": 3, "min": 1, "max": 100}),
                "keyword": ("STRING", {"multiline": True, "default": ""}),
                "news_type": (["top-headlines", "everything"], {"default": "top-headlines"}),
                "nums_per_batch": ("INT", {"default": 10, "min": 1, "max": 100}),
                "max_attempts": ("INT", {"default": 5, "min": 1, "max": 20}),
                "max_content_length": ("INT", {"default": 500, "min": 50, "max": 5000, "step": 50}),
            }
        }

    RETURN_TYPES = ("JSON",)
    RETURN_NAMES = ("news_json",)
    FUNCTION = "fetch_news"
    CATEGORY = "News"

    def __init__(self):
        self.source_queue = deque(self.SOURCES * 3)
        random.shuffle(self.source_queue)
        self.used_sources = set()
        self.article_cache = {}

    def fetch_news(self, category, language, news_nums, keyword, news_type,
                   nums_per_batch, max_attempts, max_content_length):
        # Validate batch size
        if nums_per_batch < news_nums:
            nums_per_batch = news_nums

        # Handle random category
        if category == "random":
            category = random.choice([c for c in self.CATEGORIES if c != "random"])

        # Collect articles
        collected_articles = []
        attempts = 0
        page = 1

        # Smart fetching loop
        while len(collected_articles) < news_nums and attempts < max_attempts:
            # Get next set of sources
            sources = self.get_next_sources(5)

            # Fetch news
            if news_type == "top-headlines":
                articles = self.get_top_headlines(
                    language,
                    nums_per_batch,
                    sources,
                    category,
                    page,
                    max_content_length
                )
            else:
                articles = self.get_everything(
                    keyword,
                    language,
                    nums_per_batch,
                    sources,
                    page,
                    max_content_length
                )

            # Process fetched articles
            if articles:
                # Filter duplicates
                new_articles = [a for a in articles if a["url"] not in self.article_cache]

                # Update cache
                for article in new_articles:
                    self.article_cache[article["url"]] = article

                # Add new articles
                collected_articles.extend(new_articles)

                # Break early if enough articles
                if len(collected_articles) >= news_nums:
                    break

                # Increase page
                page += 1

            attempts += 1

        # Final processing
        if len(collected_articles) > news_nums:
            collected_articles = random.sample(collected_articles, news_nums)
        elif len(collected_articles) < news_nums:
            self.supplement_articles(
                collected_articles,
                news_nums,
                news_type,
                language,
                max_content_length
            )

        # Convert to JSON
        news_json = json.dumps(collected_articles[:news_nums], ensure_ascii=False, indent=2)
        return (news_json,)

    def get_next_sources(self, count):
        """Get next set of news sources"""
        selected = []
        while len(selected) < count and self.source_queue:
            source = self.source_queue.popleft()
            if source not in self.used_sources:
                selected.append(source)
                self.used_sources.add(source)

        if len(selected) < count:
            candidates = list(set(self.SOURCES) - set(selected))
            needed = count - len(selected)
            selected.extend(random.sample(candidates, min(needed, len(candidates))))

        return ",".join(selected)

    def supplement_articles(self, collected_articles, target_count, news_type, language, max_content_length):
        """Supplement missing articles"""
        missing = target_count - len(collected_articles)
        if missing <= 0:
            return

        # Try backup strategy
        backup_sources = ",".join(self.SOURCES)
        backup_articles = []

        if news_type == "top-headlines":
            backup_articles = self.get_top_headlines(
                language,
                missing * 2,
                backup_sources,
                None,
                1,
                max_content_length
            )
        else:
            backup_articles = self.get_everything(
                "",
                language,
                missing * 2,
                backup_sources,
                1,
                max_content_length
            )

        # Add non-duplicate articles
        if backup_articles:
            new_articles = [a for a in backup_articles
                            if a["url"] not in self.article_cache
                            and a not in collected_articles]
            collected_articles.extend(new_articles[:missing])

    def get_top_headlines(self, language, page_size, sources, category, page, max_content_length):
        """Fetch top headlines"""
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": self.API_KEY,
            "language": language,
            "pageSize": page_size,
            "page": page
        }

        # Parameter strategy
        if sources and category:
            if random.choice([True, False]):
                params["sources"] = sources
            else:
                params["category"] = category
        elif sources:
            params["sources"] = sources
        elif category:
            params["category"] = category
        else:
            params["country"] = "us"

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if data.get("status") == "ok":
                return self.process_articles(
                    data.get("articles", []),
                    max_content_length
                )
            else:
                print(f"Failed to fetch top headlines: {data.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error requesting top headlines: {e}")
        return []

    def get_everything(self, query, language, page_size, sources, page, max_content_length):
        """Fetch all news"""
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": self.API_KEY,
            "language": language,
            "pageSize": page_size,
            "sources": sources,
            "page": page,
            "sortBy": "publishedAt"
        }

        if query.strip():
            params["q"] = query

        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            if data.get("status") == "ok":
                return self.process_articles(
                    data.get("articles", []),
                    max_content_length
                )
            else:
                print(f"Failed to fetch news: {data.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error requesting news: {e}")
        return []

    def process_articles(self, articles, max_content_length):
        """Process and simplify article data with content formatting"""
        processed = []
        for article in articles:
            if not article.get("url"):
                continue

            # Process content field
            raw_content = article.get("content", "No content")
            content = self.process_content(raw_content, max_content_length)

            processed.append({
                "source": article.get("source", {}).get("name", "Unknown source"),
                "author": article.get("author", "Unknown author"),
                "title": article.get("title", "No title"),
                "description": article.get("description", "No description"),
                "content": content,  # Use processed content
                "url": article.get("url", ""),
                "urlToImage": article.get("urlToImage", ""),
                "publishedAt": article.get("publishedAt", "")
            })
        return processed

    def process_content(self, content, max_length):
        """Process content with custom max length and remove char count"""
        if content == "No content" or not content:
            return "No content"

        # Remove character count suffix using regex
        content = re.sub(r'\s*\[\s*\+?\d+\s*(?:chars?|characteres?)?\s*\]\s*$', '', content)

        # Trim to max length and add ellipsis if needed
        if max_length > 0 and len(content) > max_length:
            # Find the last space before max_length to avoid cutting words
            last_space = content.rfind(' ', 0, max_length)
            if last_space != -1 and last_space > max_length * 0.9:
                return content[:last_space].strip() + "..."
            return content[:max_length].strip() + "..."

        return content.strip()


import json
import datetime


class Parse_News_Content():
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "news_json": ("JSON", {"default": "[]"}),
                "news_index": ("INT", {"default": 0, "min": 0, "max": 99}),
            }
        }

    RETURN_TYPES = (
        "STRING", "STRING", "STRING", "STRING",
        "STRING", "STRING", "STRING", "STRING", "STRING"
    )
    RETURN_NAMES = (
        "source", "title", "description", "content",
        "author", "publish_at", "url", "urltoimage", "current_date"
    )
    FUNCTION = "parse_news"
    CATEGORY = "News"

    def parse_news(self, news_json, news_index):
        # Get formatted current date
        current_date = self.get_formatted_date()

        try:
            # Parse JSON data
            news_data = json.loads(news_json)

            # Validate index range
            if not isinstance(news_data, list) or len(news_data) == 0:
                return self.return_empty("Invalid news data format", current_date)

            if news_index < 0 or news_index >= len(news_data):
                return self.return_empty(
                    f"Index out of range (0-{len(news_data) - 1})",
                    current_date
                )

            # Get specified article
            article = news_data[news_index]

            # Extract and clean fields
            source = article.get("source", "Unknown source")
            title = article.get("title", "No title").strip()
            description = article.get("description", "No description").strip()

            # Clean content field
            content = article.get("content", "No content")
            if content and content != "No content":
                # Remove character count suffix
                if " chars]" in content:
                    content = content.split(" chars]")[0] + "]"
                content = content.strip()

            author = article.get("author", "Unknown author").strip()
            publish_at = article.get("publishedAt", "Unknown time").strip()
            url = article.get("url", "").strip()
            urltoimage = article.get("urlToImage", "").strip()

            return (
                source, title, description, content,
                author, publish_at, url, urltoimage, current_date
            )

        except json.JSONDecodeError:
            return self.return_empty("Invalid JSON format", current_date)
        except Exception as e:
            return self.return_empty(f"Parsing error: {str(e)}", current_date)

    def get_formatted_date(self):
        """Get current system time formatted as North American date + weekday"""
        now = datetime.datetime.now()
        date_str = now.strftime("%m/%d/%Y")
        weekday_str = now.strftime("%A")
        return f"{date_str} {weekday_str}"

    def return_empty(self, error_message, current_date):
        """Return empty values with error message"""
        if error_message:
            print(f"[Parse_News_Content] Error: {error_message}")
        return (
            "Unknown source", "No title", "No description", "No content",
            "Unknown author", "Unknown time", "", "", current_date
        )






