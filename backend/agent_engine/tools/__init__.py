"""
Agent 工具模块
提供 Agent 可用的内置工具

内置工具:
1. OfficeReader - Office365 文件读取（Excel/Word/PPT/PDF）
2. PythonREPL - Python 代码执行（安全沙箱）[TODO]
3. FileSystem - 文件系统操作 [TODO]
4. WebSearch - 网络搜索 (DuckDuckGo) [TODO]
5. SQLDatabase - SQL 数据库查询 [TODO]
6. MathChain - 数学计算 [TODO]
7. Shell - Shell 命令执行（受限）[TODO]
"""

from .office_reader import (
    OfficeReaderTool,
    create_office_reader_tool,
    get_available_formats,
)

__all__ = [
    "OfficeReaderTool",
    "create_office_reader_tool",
    "get_available_formats",
    "get_builtin_tools",
]


def get_builtin_tools(backend=None) -> list:
    """获取所有内置工具实例列表

    Args:
        backend: CompositeBackend 实例，用于虚拟路径解析。
                 传入后工具可自动将虚拟路径转换为真实 OS 路径。

    Returns:
        List[BaseTool]: 可用的内置工具实例
    """
    tools = []

    # Office 文件读取工具
    office_tool = create_office_reader_tool()
    if backend is not None:
        office_tool._backend = backend
    tools.append(office_tool)

    return tools
