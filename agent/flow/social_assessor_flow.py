from pocketflow import Flow, Node

from agent.nodes import DecideAction, SearchWeb, PostEvaluate, SupervisorNode

__all__ = ["context_research_flow", "social_assessor_flow"]


class NoOp(Node):
    """Node that does nothing, used to properly end the flow."""
    pass


def context_research_flow():
    """
    创建一个带有监督的代理流程，将整个代理流程视为一个节点，并将监督节点放在其外部。

    返回:
        Flow: 一个带有监督的完整研究代理流程
    """
    decide_action = DecideAction()
    search_web = SearchWeb()
    end = NoOp()

    decide_action - "search" >> search_web

    search_web - "decide" >> decide_action

    decide_action - "answer" >> end

    # 创建并返回外部流程，从 agent_flow 开始
    return Flow(start=decide_action)


def social_assessor_flow():
    """
    创建一个带有监督的代理流程，将整个代理流程视为一个节点，并将监督节点放在其外部。

    返回:
        Flow: 一个带有监督的完整研究代理流程
    """

    post_evaluate = PostEvaluate()
    supervisor = SupervisorNode()
    end = NoOp()

    # 连接组件
    post_evaluate - "evaluate" >> supervisor

    supervisor - "retry" >> post_evaluate

    supervisor - "approved" >> end

    # 创建并返回外部流程，从 agent_flow 开始
    return Flow(start=post_evaluate)
