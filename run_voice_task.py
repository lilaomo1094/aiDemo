#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语音任务入口：将语音指令转换为文本后，通过 Function Calling 编排执行测试任务.

用法:
    python run_voice_task.py --audio task.mp3 [--config config/project_config.py]
    python run_voice_task.py --audio-url https://example.com/voice.mp3
"""

import argparse
import sys
from pathlib import Path

from automation.agents.orchestrator import FunctionCallingOrchestrator
from automation.core.config import load_config
from automation.core.voice import create_asr_provider
from automation.workflow.engine import WorkflowTask


def main():
    parser = argparse.ArgumentParser(description="智测 语音任务入口")
    parser.add_argument("--audio", help="本地音频文件路径")
    parser.add_argument("--audio-url", help="音频文件 URL")
    parser.add_argument("--config", default="config/project_config.py", help="项目配置文件路径")
    parser.add_argument("--text", help="直接提供文字指令（跳过语音识别）")
    args = parser.parse_args()

    if not args.text and not args.audio and not args.audio_url:
        parser.print_help()
        sys.exit(1)

    config = load_config(args.config)

    # 1. 获取指令文本
    instruction = args.text
    if not instruction:
        voice_config = getattr(config, "voice", None)
        if not voice_config or not voice_config.enabled:
            print("错误：未在配置中启用 voice，或缺少 --text 参数")
            sys.exit(1)
        asr = create_asr_provider(voice_config.model_dump())
        if args.audio:
            result = asr.transcribe(args.audio)
        else:
            result = asr.transcribe_from_url(args.audio_url)
        instruction = result.text
        print(f"🎤 识别结果: {instruction}")

    # 2. Function Calling 编排执行
    orchestrator = FunctionCallingOrchestrator(config)
    task = WorkflowTask(
        task_id="voice-task",
        agent_type=None,
        name="语音任务",
        description=instruction,
        input_data={"instruction": instruction},
    )
    result = orchestrator.execute(task, None)

    print("\n=== 执行结果 ===")
    print(result.get("final_answer", ""))
    print(f"\n工具调用次数: {len(result.get('tool_results', []))}")
    for tr in result.get("tool_results", []):
        print(f"  - {tr.get('tool')}: {tr.get('status')}")


if __name__ == "__main__":
    main()
