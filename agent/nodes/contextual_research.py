from asyncio import sleep

from dotenv import load_dotenv
from pocketflow import Node

from agent.tools.crawler import WebCrawler
from agent.tools.parser import analyze_site
import yaml

from agent.tools.search import search_web
from agent.utils.call_llm import call_llm

load_dotenv()
__all__ = ["DecideAction", "SearchWeb", ]


class DecideAction(Node):
    def prep(self, shared):
        """准备上下文和问题，用于决策过程。

        参数:
            shared (dict): 共享存储，包含上下文和问题。

        返回:
            tuple: 包含问题和上下文的元组。
        """

        # 获取当前上下文（如果不存在，则默认为“无先前搜索”）
        context = shared.get("context", "无先前搜索")
        # 从共享存储中获取问题
        user_name = shared["user_name"]
        post = shared["post"]
        create_time = shared["create_time"]
        links_count = shared.get("links_count",0 )

        logger = shared["logger"]
        logger.info(f"开始内容背景调查...")
        return user_name, create_time, post, context, links_count,logger

    def exec(self, inputs):
        """调用 LLM 决定是搜索还是回答。"""
        user_name, create_time, post, context, links_count,logger = inputs

        logger.info(f"代理正在决定下一步操作...")
        # 创建一个提示，帮助 LLM 决定下一步操作，并使用适当的 yaml 格式
        prompt = f"""
            
            你是一个可以搜索网络的内容背景调查师,现在提供一个网络社媒名人在社交账号上所发帖子的内容
            为了实现进一步分析,请参考查询条件,客观调查帖子中提到的内容的具体背景
            
            ### 查询条件
            
            - 事件基本信息 : 确认热词对应的具体事件、时间、地点、主要人物
            - 事件发展脉络 : 事件起因、关键节点、最新进展
            - 社会影响范围 : 受众群体、地域影响、行业影响
            - 争议焦点 : 各方观点分歧、争论核心问题
            - 官方回应 : 相关权威机构/人物的正式表态
            - 公众反应 : 主流情绪倾向、典型评论
            - 关联事件 : 与此热点相关的历史/并行事件
            
            并非所有查询条件都需满足，可使用优先级进行排序
            查询优先级：事件基本信息>事件发展脉络>社会影响范围>争议焦点>官方回应>公众反应>关联事件
                     
            ## 上下文
            - 社媒名人名称: {user_name}
            - 发布时间： {create_time}
             
             {post}
            
            - 先前的研究,总计为{links_count}条,具体如下：
            
            {context}

            ## 操作空间
            [1] search
              描述: 在网络上查找更多信息
              参数:
                - query (str): 搜索内容

            [2] answer
              描述: 用当前知识回答问题
              参数:
                - answer (str): 问题的最终回答

            ### 下一步操作
            根据上下文、查询维度和可用操作决定下一步操作。
            
            重要：请确保：
            如先前的研究，总计大于5条，则结合已有的研究进行回答操作，不再进行深度搜索，
            
            请以以下格式返回你的响应：

            ```yaml
            thinking: |
                <你的逐步推理过程>
            action: search OR answer
            reason: <为什么选择这个操作>
            answer: <如果操作是回答>
            search_query: <具体的搜索查询如果操作是搜索>
            ```
            重要：请确保：

            1. 使用|字符表示多行文本字段
            2. 多行字段使用缩进（4个空格）
            3. 单行字段不使用|字符
            4. 不允许直接在键后嵌套另一个键（如 answer: search_query:)
            5. 非键值对不允许随意使用冒号: 
            6. 返回字段的值使用中文
            """
        # 调用 LLM 进行决策
        response, success = call_llm(prompt, logger)
        if not success:
            logger.error("LLM 响应失败，请检查你的响应格式。")
            return {"action": "finish", "reason": "LLM 响应失败"}

        # 解析响应以获取决策
        if "```yaml" not in response:
            logger.error("LLM 响应格式不正确，请检查你的响应格式。")
            return {"action": "finish", "reason": "LLM 响应格式不正确"}
        try:
            yaml_str = response.replace("\"", "").replace("\'", "").split("```yaml")[1].split("```")[0].strip()
            logger.info(f"LLM 响应: {yaml_str}")
            decision = yaml.safe_load(yaml_str)
        except Exception as e:
            return {"action": "finish", "reason": "LLM 响应格式不正确"}

        return decision

    def post(self, shared, prep_res, exec_res):
        """保存决策并确定流程中的下一步。"""
        # 如果 LLM 决定搜索，则保存搜索查询
        logger = shared["logger"]
        if exec_res["action"] == "search":
            shared["search_query"] = exec_res["search_query"]
            logger.info(f"🔍 代理决定搜索: {exec_res['search_query']}")
        else:
            shared["search_history"] = shared["context"]  # 保存上下文，如果 LLM 在不搜索的情况下给出回答。
            shared["context"] = exec_res["answer"]
            logger.info(f"💡 代理决定回答问题")

        # 返回操作以确定流程中的下一个节点
        return exec_res["action"]


total_links_count = 0


class SearchWeb(Node):
    def prep(self, shared):
        """从共享存储中获取搜索查询。"""
        return shared["search_query"],  shared["logger"]

    def exec(self, inputs):
        """搜索网络上的给定查询。"""
        # 调用搜索实用函数
        global total_links_count  # 声明使用全局变量
        search_query,  logger = inputs
        logger.info(f"🌐 在网络上搜索: {search_query}")
        _, results_dict = search_web(search_query,  logger)
        analyzed_results = []
        if results_dict is None:
            logger.info(f"🌐 深度搜索失败。")
            return {"action": "finish", "reason": "搜索失败"}
        for i in results_dict:
            title = i['title']
            snippet = i['snippet']
            link = i['link']

            logger.info(f"🌐 对搜索的内容进项深度扫描")
            logger.info(f"🌐 标题:{title}")
            logger.info(f"🌐 摘要:{snippet}")
            # 统计链接数量
            total_links_count += 1
            logger.info(f"🌐 源链接:{link}")
            content_list = WebCrawler(link).crawl()

            analyzed_results.append(analyze_site(content_list, logger))

        results = []
        for analyzed_result in analyzed_results:
            for content in analyzed_result:

                result = (f"标题：{content.get('title', '无')}\n" +
                          f"链接：{content.get('url', '无')}\n" +
                          f"汇总：{content['analysis']['summary']}\n" +
                          f"话题：{content['analysis']['topics']}\n" +
                          f"类型：{content['analysis']['content_type']}\n"
                          )
                results.append(result)

        logger.info(f"✅ 当前已采集链接总数: {total_links_count}")

        return '\n\n'.join(results), total_links_count

    def post(self, shared, prep_res, exec_res):
        """保存搜索结果并返回决策节点。"""
        # 将搜索结果添加到共享存储中的上下文中
        results, links_count = exec_res
        previous = shared.get("context", "")
        # 搜索记忆功能
        shared["context"] = previous + "\n\n搜索条件: " + shared["search_query"] + "\n搜索结果(多条):\n " + results
        logger = shared["logger"]
        shared["links_count"] = links_count
        logger.info(f"📚 找到信息，分析结果...")

        # 搜索后始终返回决策节点
        return "decide"



if __name__ == "__main__":
    pass
