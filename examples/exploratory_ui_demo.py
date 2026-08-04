# -*- coding: utf-8 -*-
"""探索式 UI 测试使用示例。

演示如何使用 AI 驱动的探索式 UI 测试能力，
用户只需用自然语言描述测试目标即可。

两种使用方式：
1. 直接使用 ExploratoryUIExecutor
2. 通过 Orchestrator 的 Function Calling
3. 通过 Workflow 集成
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def example_direct_executor():
    """方式 1: 直接使用 ExploratoryUIExecutor."""
    from automation.core.config import ToolConfig
    from automation.core.executor.exploratory_ui_executor import ExploratoryUIExecutor

    # 配置（需要根据实际环境调整）
    config = ToolConfig()

    executor = ExploratoryUIExecutor(config)

    # 用自然语言描述测试目标
    test_case = {
        "id": "EXP-001",
        "type": "exploratory_ui",
        "goal": "打开百度首页，搜索 'Python 测试框架'，查看搜索结果是否包含相关链接",
        "start_url": "https://www.baidu.com",
        "max_steps": 15,
        "expected_outcome": "搜索结果页面显示与 Python 测试框架相关的链接",
    }

    result = executor.execute(test_case)
    print(f"\n测试状态: {result['status']}")
    print(f"消息: {result['message']}")
    print(f"步骤数: {result.get('details', {}).get('total_steps', 0)}")
    print(f"目标达成: {result.get('details', {}).get('goal_achieved', False)}")

    # 打印步骤摘要
    for step in result.get("steps", []):
        action = step.get("action", "?")
        su = "✓" if step.get("success", True) else "✗"
        reasoning = step.get("reasoning", "")[:80]
        print(f"  {su} 步骤{step.get('step', '?')}: {action} - {reasoning}")

    executor.cleanup()
    return result


def example_orchestrator():
    """方式 2: 通过 Orchestrator Function Calling 调用."""
    from automation.agents.orchestrator import FunctionCallingOrchestrator
    from automation.core.config import ToolConfig
    from automation.workflow.engine import WorkflowTask

    config = ToolConfig()
    orchestrator = FunctionCallingOrchestrator(config)

    # 通过 WorkflowTask 传递自然语言指令
    task = WorkflowTask(
        task_id="EXP-002",
        agent_type=None,
        name="UI 探索测试",
        description="测试登录页面",
        input_data={
            "instruction": "请用 explore_ui 工具测试 https://example.com/login 登录页面，"
                           "使用 test@example.com / password123 登录，验证能否成功跳转到首页",
        },
    )

    result = orchestrator.execute(task, context=None)
    print(f"\nOrchestrator 结果: {result.get('status')}")
    return result


def example_workflow_integration():
    """方式 3: 集成到工作流中."""
    from automation.core.config import ToolConfig
    from automation.core.executor.factory import create_executor
    from automation.core.executor.exploratory_ui_executor import ExploratoryUIExecutor

    config = ToolConfig()

    # 通过工厂创建
    executor = create_executor("exploratory_ui", config)
    assert isinstance(executor, ExploratoryUIExecutor)

    # 批量执行多个探索任务
    test_cases = [
        {
            "id": "EXP-003",
            "goal": "验证百度首页搜索框是否可用",
            "start_url": "https://www.baidu.com",
            "max_steps": 10,
        },
        {
            "id": "EXP-004",
            "goal": "测试百度首页的导航链接是否都可以点击",
            "start_url": "https://www.baidu.com",
            "max_steps": 20,
        },
    ]

    for tc in test_cases:
        print(f"\n{'='*50}")
        print(f"执行: {tc['goal']}")
        print(f"{'='*50}")
        result = executor.execute(tc)
        print(f"结果: {result['status']} - {result.get('details', {}).get('conclusion', '')}")

    executor.cleanup()


def example_with_vision():
    """方式 4: 使用 Vision LLM 增强（需要配置 GPT-4V/4o API Key）."""
    from automation.core.config import LLMConfig, ToolConfig
    from automation.core.executor.exploratory_ui_executor import ExploratoryUIExecutor

    # 配置支持 Vision 的 LLM
    config = ToolConfig()
    config.llm = LLMConfig(
        provider="openai",
        api_key="your-api-key-here",  # 替换为实际 API Key
        model="gpt-4o",               # 支持 Vision 的模型
        temperature=0.3,
    )

    executor = ExploratoryUIExecutor(config)

    test_case = {
        "id": "EXP-VISION-001",
        "goal": "截图分析百度首页，判断页面是否正常加载，包含搜索框和导航栏",
        "start_url": "https://www.baidu.com",
        "max_steps": 5,
    }

    result = executor.execute(test_case)
    print(f"\nVision 模式测试结果: {result['status']}")
    print(f"截图数量: {len(result.get('screenshots', []))}")
    executor.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="探索式 UI 测试示例")
    parser.add_argument(
        "--mode",
        choices=["direct", "orchestrator", "workflow", "vision"],
        default="direct",
        help="运行模式",
    )
    args = parser.parse_args()

    modes = {
        "direct": example_direct_executor,
        "orchestrator": example_orchestrator,
        "workflow": example_workflow_integration,
        "vision": example_with_vision,
    }

    try:
        modes[args.mode]()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"执行出错: {e}")
        import traceback
        traceback.print_exc()
