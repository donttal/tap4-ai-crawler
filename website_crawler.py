from bs4 import BeautifulSoup
import logging
import time
import random
from pyppeteer import launch

from util.common_util import CommonUtil
from util.llm_util import LLMUtil
from util.oss_util import OSSUtil

llm = LLMUtil()
oss = OSSUtil()

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 更新的用户代理列表
global_agent_headers = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

class WebsitCrawler:
    def __init__(self):
        self.browser = None

    # 爬取指定URL网页内容
    async def scrape_website(self, url, tags, languages):
        # 开始爬虫处理
        try:
            # 记录程序开始时间
            start_time = int(time.time())
            logger.info("正在处理：" + url)
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url

            if self.browser is None:
                self.browser = await launch(headless=True,
                                            ignoreDefaultArgs=["--enable-automation"],
                                            ignoreHTTPSErrors=True,
                                            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                                                  '--disable-software-rasterizer', '--disable-setuid-sandbox'],
                                            handleSIGINT=False, handleSIGTERM=False, handleSIGHUP=False)

            page = await self.browser.newPage()
            # 设置用户代理
            await page.setUserAgent(random.choice(global_agent_headers))

            # 设置页面视口大小并访问具体URL
            width = 1920  # 默认宽度为 1920
            height = 1080  # 默认高度为 1080
            await page.setViewport({'width': width, 'height': height})
            try:
                await page.goto(url, {'timeout': 60000, 'waitUntil': ['load', 'networkidle2']})
            except Exception as e:
                logger.info(f'页面加载超时,不影响继续执行后续流程:{e}')

            # 获取网页内容
            origin_content = await page.content()
            soup = BeautifulSoup(origin_content, 'html.parser')

            # 通过标签名提取内容
            title = soup.title.string.strip() if soup.title else ''

            # 根据url提取域名生成name
            name = CommonUtil.get_name_by_url(url)

            # 获取网页描述
            description = ''
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description:
                description = meta_description['content'].strip()

            if not description:
                meta_description = soup.find('meta', attrs={'property': 'og:description'})
                description = meta_description['content'].strip() if meta_description else ''

            logger.info(f"url:{url}, title:{title},description:{description}")

            # 生成网站截图
            image_key = oss.get_default_file_key(url)
            dimensions = await page.evaluate(f'''(width, height) => {{
                return {{
                    width: {width},
                    height: {height},
                    deviceScaleFactor: window.devicePixelRatio
                }};
            }}''', width, height)
            # 截屏并设置图片大小
            screenshot_path = './' + url.replace("https://", "").replace("http://", "").replace("/", "").replace(".",
                                                                                                                 "-") + '.png'
            await page.screenshot({'path': screenshot_path, 'clip': {
                'x': 0,
                'y': 0,
                'width': dimensions['width'],
                'height': dimensions['height']
            }})
            # 上传图片，返回图片地址
            screenshot_key = oss.upload_file_to_r2(screenshot_path, image_key)

            # 生成缩略图
            thumnbail_key = oss.generate_thumbnail_image(url, image_key)

            # 抓取整个网页内容
            content = soup.get_text()

            # 使用llm工具处理content
            detail = llm.process_detail(content)
            await page.close()

            # 如果tags为非空数组，则使用llm工具处理tags
            processed_tags = None
            if tags and detail:
                processed_tags = llm.process_tags('tag_list is:' + ','.join(tags) + '. content is: ' + detail)

            # 循环languages数组， 使用llm工具生成各种语言
            processed_languages = []
            if languages:
                for language in languages:
                    logger.info("正在处理" + url + "站点，生成" + language + "语言")
                    processed_title = llm.process_language(language, title)
                    processed_description = llm.process_language(language, description)
                    processed_detail = llm.process_language(language, detail)
                    processed_languages.append({'language': language, 'title': processed_title,
                                                'description': processed_description, 'detail': processed_detail})

            logger.info(url + "站点处理成功")
            return {
                'name': name,
                'url': url,
                'title': title,
                'description': description,
                'detail': detail,
                'screenshot_data': screenshot_key,
                'screenshot_thumbnail_data': thumnbail_key,
                'tags': processed_tags,
                'languages': processed_languages,
            }
        except Exception as e:
            logger.error("处理" + url + "站点异常，错误信息:", e)
            return None
        finally:
            # 计算程序执行时间
            execution_time = int(time.time()) - start_time
            # 输出程序执行时间
            logger.info("处理" + url + "用时：" + str(execution_time) + " 秒")
