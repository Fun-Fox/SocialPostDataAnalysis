from io import BytesIO
from time import sleep

from duckduckgo_search import DDGS
import requests
import os

from dotenv import load_dotenv
load_dotenv()

__all__=["search_web"]
# 设置代理
proxies = {
    "http": f"{os.getenv('PROXY_URL')}",
    "https": f"{os.getenv('PROXY_URL')}",
}

search_web_call_count = 0
#
def search_web(query,  logger,num_results=3):
    try:
        # 使用serper.dev进行网络搜索
        # logger.info(f"## 查询: {query}")

        api_key = os.getenv("SERPAPI_API_KEY", None)
        if api_key:
            global search_web_call_count
            search_web_call_count += 1
            sleep(5)
            logger.info(f"[SearchWeb] 第 {search_web_call_count} 次调用，查询词: {query}")

            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "engine": "google",
                "num": num_results
            }
            response = requests.post(url, headers=headers, json=payload, proxies=proxies)
            if response.status_code == 200:
                results = response.json().get("organic", [])
                results_str = "\n\n".join(
                    [f"标题: {r['title']}\n源链接: {r['link']}\n摘要: {r['snippet']}" for r in results])
                results_dict = [{'title':r['title'],'snippet':r['snippet'],'link':r['link']}  for r in results]

            else:
                logger.error(f"错误: 无法获取搜索结果。状态码: {response.status_code}")
                return "错误: 无法获取搜索结果。",None
        else:
            logger.info(f"使用DuckDuckgo免费搜索进行查询")

            with DDGS(proxy=os.getenv("PROXY_URL"), timeout=20) as ddgs:
                news_results = ddgs.text(query, max_results=num_results)
                # Convert results to a string
                results_str = "\n\n".join(
                    [f"标题: {r['title']}\n源链接: {r['href']}\n摘要: {r['body']}" for r in news_results])
                results_dict = [{'title':r['title'],'snippet':r['body'],'link':r['href']}  for r in news_results]
        # logger.info(f"## 结果: {results_str}")
        return results_str,results_dict
    except Exception as e:
        logger.error(f"搜索网络时发生异常: {e}")
        return "错误: 搜索网络时发生异常。",None



