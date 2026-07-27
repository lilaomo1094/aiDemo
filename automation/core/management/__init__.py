"""测试自动化管理框架.

提供版本生命周期、任务生命周期、Agent 协作、环境画像、资产管理等能力.
"""

from .agent_coordination import AgentCoordinator
from .asset_manager import AssetManager
from .environment_profile import EnvironmentProfileManager, ExecutionProfile
from .framework_manager import TestAutomationManager
from .task_lifecycle import TaskLifecycleManager
from .version_lifecycle import VersionLifecycleManager

__all__ = [
    "AgentCoordinator",
    "AssetManager",
    "EnvironmentProfileManager",
    "ExecutionProfile",
    "TaskLifecycleManager",
    "TestAutomationManager",
    "VersionLifecycleManager",
]
