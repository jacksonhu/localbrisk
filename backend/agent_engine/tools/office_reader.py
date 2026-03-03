"""
Office365 文件读取工具

支持读取以下格式:
- Excel (.xlsx, .xls) — 使用 openpyxl
- Word (.docx) — 使用 MarkItDown / docling / python-docx
- PowerPoint (.pptx) — 使用 MarkItDown / docling / python-pptx
- PDF (.pdf) — 使用 MarkItDown / docling

策略（三级降级）:
1. Excel 优先使用 openpyxl（结构化数据保留更好）
2. Word / PowerPoint / PDF:
   a. 快速模式（默认）: 使用 MarkItDown 快速提取文字概要
   b. 详细模式: 使用 docling 进行深度解析（保留复杂表格、公式、布局）
   c. fallback: docling 不可用时降级到 python-docx / python-pptx
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ──────────────────────── 可选依赖检测 ────────────────────────

_OPENPYXL_AVAILABLE = False
_MARKITDOWN_AVAILABLE = False
_DOCLING_AVAILABLE = False
_PYTHON_DOCX_AVAILABLE = False
_PYTHON_PPTX_AVAILABLE = False

try:
    import openpyxl
    _OPENPYXL_AVAILABLE = True
except ImportError:
    pass

try:
    from markitdown import MarkItDown
    _MARKITDOWN_AVAILABLE = True
except ImportError:
    pass

try:
    from docling.document_converter import DocumentConverter
    _DOCLING_AVAILABLE = True
except ImportError:
    pass

try:
    from docx import Document as DocxDocument
    _PYTHON_DOCX_AVAILABLE = True
except ImportError:
    pass

try:
    from pptx import Presentation
    _PYTHON_PPTX_AVAILABLE = True
except ImportError:
    pass

# ──────────────────────── 支持的扩展名 ────────────────────────

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb"}
WORD_EXTENSIONS = {".docx", ".doc"}
PPTX_EXTENSIONS = {".pptx", ".ppt"}
PDF_EXTENSIONS = {".pdf"}

ALL_SUPPORTED = EXCEL_EXTENSIONS | WORD_EXTENSIONS | PPTX_EXTENSIONS | PDF_EXTENSIONS


# ══════════════════════════════════════════════════════════════
# 底层读取函数
# ══════════════════════════════════════════════════════════════

def read_excel(file_path: str, sheet_name: Optional[str] = None,
               max_rows: int = 500) -> str:
    """使用 openpyxl 读取 Excel 文件，返回 Markdown 表格格式"""
    if not _OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl 未安装。请执行: pip install openpyxl")

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    target_sheets = [sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.sheetnames

    parts: list[str] = []
    for sname in target_sheets:
        ws = wb[sname]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            parts.append(f"## Sheet: {sname}\n\n(空表)")
            continue

        # 取表头
        header = rows[0]
        col_names = [str(c) if c is not None else "" for c in header]
        data_rows = rows[1:max_rows + 1]

        # 构建 Markdown 表格
        md_lines = [f"## Sheet: {sname}", ""]
        md_lines.append("| " + " | ".join(col_names) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(col_names)) + " |")
        for row in data_rows:
            cells = [str(c) if c is not None else "" for c in row]
            md_lines.append("| " + " | ".join(cells) + " |")

        if len(rows) - 1 > max_rows:
            md_lines.append(f"\n> ⚠️ 仅显示前 {max_rows} 行，共 {len(rows) - 1} 行数据")

        parts.append("\n".join(md_lines))

    wb.close()

    summary = f"**文件**: `{os.path.basename(file_path)}`\n"
    summary += f"**Sheet 数量**: {len(target_sheets)}\n\n"
    return summary + "\n\n---\n\n".join(parts)


def read_with_markitdown(file_path: str) -> str:
    """使用 MarkItDown 快速解析文档（Word / PPT / PDF / Excel），返回 Markdown
    
    MarkItDown 是微软开源的轻量级转换工具，速度快、依赖少，
    适合文字概要提取。对复杂表格和公式的保真度不如 docling。
    """
    if not _MARKITDOWN_AVAILABLE:
        raise ImportError("markitdown 未安装。请执行: pip install markitdown")

    md = MarkItDown()
    result = md.convert(file_path)
    content = result.text_content or ""

    summary = f"**文件**: `{os.path.basename(file_path)}`\n"
    summary += f"**格式**: {Path(file_path).suffix.upper()}\n"
    summary += f"**解析引擎**: MarkItDown (快速模式)\n\n"
    return summary + content


def read_with_docling(file_path: str) -> str:
    """使用 docling 解析文档（Word / PPT / PDF），返回 Markdown"""
    if not _DOCLING_AVAILABLE:
        raise ImportError("docling 未安装。请执行: pip install docling")

    converter = DocumentConverter()
    result = converter.convert(file_path)
    md_content = result.document.export_to_markdown()

    summary = f"**文件**: `{os.path.basename(file_path)}`\n"
    summary += f"**格式**: {Path(file_path).suffix.upper()}\n"
    summary += f"**解析引擎**: Docling (详细模式)\n\n"
    return summary + md_content


def read_docx_fallback(file_path: str) -> str:
    """使用 python-docx 读取 Word 文档（docling 不可用时的 fallback）"""
    if not _PYTHON_DOCX_AVAILABLE:
        raise ImportError("python-docx 未安装。请执行: pip install python-docx")

    doc = DocxDocument(file_path)
    parts: list[str] = []

    parts.append(f"**文件**: `{os.path.basename(file_path)}`\n")

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # 映射标题级别
        if para.style and para.style.name.startswith("Heading"):
            try:
                level = int(para.style.name.replace("Heading ", "").replace("Heading", "1"))
            except ValueError:
                level = 1
            parts.append(f"{'#' * level} {text}")
        else:
            parts.append(text)

    # 提取表格
    for i, table in enumerate(doc.tables):
        parts.append(f"\n### 表格 {i + 1}\n")
        for j, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            parts.append("| " + " | ".join(cells) + " |")
            if j == 0:
                parts.append("| " + " | ".join(["---"] * len(cells)) + " |")

    return "\n\n".join(parts)


def read_pptx_fallback(file_path: str) -> str:
    """使用 python-pptx 读取 PPT（docling 不可用时的 fallback）"""
    if not _PYTHON_PPTX_AVAILABLE:
        raise ImportError("python-pptx 未安装。请执行: pip install python-pptx")

    prs = Presentation(file_path)
    parts: list[str] = []
    parts.append(f"**文件**: `{os.path.basename(file_path)}`\n")
    parts.append(f"**幻灯片数量**: {len(prs.slides)}\n")

    for idx, slide in enumerate(prs.slides, 1):
        slide_texts: list[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        slide_texts.append(text)
            if shape.has_table:
                table = shape.table
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    slide_texts.append("| " + " | ".join(cells) + " |")

        parts.append(f"## Slide {idx}")
        if slide_texts:
            parts.append("\n".join(slide_texts))
        else:
            parts.append("(空白幻灯片)")

    return "\n\n".join(parts)


# ══════════════════════════════════════════════════════════════
# LangChain Tool 定义
# ══════════════════════════════════════════════════════════════

class OfficeReaderInput(BaseModel):
    """Office 文件读取工具的输入参数"""
    file_path: str = Field(
        description="要读取的 Office 文件路径（支持 .xlsx/.xls/.docx/.pptx/.pdf）"
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="（仅 Excel）指定要读取的 Sheet 名称，不指定则读取全部 Sheet"
    )
    max_rows: int = Field(
        default=500,
        description="（仅 Excel）最多读取的数据行数，默认 500 行"
    )
    mode: str = Field(
        default="fast",
        description=(
            "解析模式: "
            "'fast' = 使用 MarkItDown 快速提取文字概要（默认，速度快）；"
            "'detailed' = 使用 Docling 深度解析（保留复杂表格、公式、布局，速度较慢）"
        )
    )


class OfficeReaderTool(BaseTool):
    """读取 Office365 文件内容（Excel / Word / PowerPoint / PDF）

    支持格式:
    - Excel (.xlsx, .xls): 以 Markdown 表格形式返回数据
    - Word (.docx): 以 Markdown 形式返回文档内容
    - PowerPoint (.pptx): 以 Markdown 形式返回幻灯片内容
    - PDF (.pdf): 以 Markdown 形式返回文档内容

    支持两种解析模式:
    - fast (默认): 使用 MarkItDown 快速提取文字概要，速度快
    - detailed: 使用 Docling 深度解析，保留复杂表格、公式和布局
    """

    name: str = "office_reader"
    description: str = (
        "读取 Office 文件内容。支持 Excel(.xlsx/.xls)、Word(.docx)、"
        "PowerPoint(.pptx)、PDF(.pdf)。返回 Markdown 格式的文件内容。"
        "支持 mode 参数：'fast'(默认) 使用 MarkItDown 快速提取文字概要；"
        "'detailed' 使用 Docling 深度解析复杂表格和公式。"
        "文件路径可以是虚拟路径（如 /asset_bundles_xxx/file.xlsx）或真实 OS 路径。"
    )
    args_schema: Type[BaseModel] = OfficeReaderInput

    # 运行时注入的 CompositeBackend 实例，用于虚拟路径解析
    _backend: Any = None

    def _run(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        max_rows: int = 500,
        mode: str = "fast",
    ) -> str:
        """同步执行"""
        return self._read_file(file_path, sheet_name, max_rows, mode)

    async def _arun(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        max_rows: int = 500,
        mode: str = "fast",
    ) -> str:
        """异步执行（在线程池中运行同步 IO）"""
        import asyncio
        return await asyncio.to_thread(self._read_file, file_path, sheet_name, max_rows, mode)

    def _read_file(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        max_rows: int = 500,
        mode: str = "fast",
    ) -> str:
        """核心读取逻辑
        
        mode:
          - "fast": 优先 MarkItDown（快速文字概要提取）
          - "detailed": 优先 Docling（深度解析，保留表格/公式/布局）
        """
        # 如果有 backend 实例，尝试将虚拟路径解析为真实 OS 路径
        resolved_path = file_path
        if self._backend is not None:
            try:
                from agent_engine.utils.path_resolver import resolve_virtual_path
                resolved_path = resolve_virtual_path(self._backend, file_path)
                if resolved_path != file_path:
                    logger.info(f"虚拟路径解析: {file_path} -> {resolved_path}")
            except Exception as e:
                logger.warning(f"虚拟路径解析失败，使用原路径: {file_path}, error={e}")
                resolved_path = file_path

        path = Path(resolved_path)
        # 验证文件存在
        if not path.exists():
            return f"❌ 文件不存在: {file_path}" + (
                f"\n(解析后路径: {resolved_path})" if resolved_path != file_path else ""
            )

        if not path.is_file():
            return f"❌ 路径不是文件: {file_path}"

        ext = path.suffix.lower()

        if ext not in ALL_SUPPORTED:
            return (
                f"❌ 不支持的文件格式: {ext}\n"
                f"支持的格式: {', '.join(sorted(ALL_SUPPORTED))}"
            )

        use_detailed = (mode == "detailed")

        try:
            # ─── Excel: 始终使用 openpyxl（结构化数据保真最好） ───
            if ext in EXCEL_EXTENSIONS:
                if _OPENPYXL_AVAILABLE:
                    return read_excel(resolved_path, sheet_name, max_rows)
                # Excel 的 fallback: MarkItDown 也能处理 xlsx
                if _MARKITDOWN_AVAILABLE:
                    return read_with_markitdown(resolved_path)
                return self._missing_deps_message("Excel", ["openpyxl", "markitdown"])

            # ─── Word / PowerPoint / PDF: 三级降级策略 ───
            return self._read_document(resolved_path, ext, use_detailed)

        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, error={e}", exc_info=True)
            return f"❌ 读取文件失败: {file_path}\n错误: {str(e)}"

    def _read_document(self, resolved_path: str, ext: str, use_detailed: bool) -> str:
        """读取文档类文件（Word / PPT / PDF）的三级降级策略
        
        详细模式: Docling → MarkItDown → python-docx/pptx
        快速模式: MarkItDown → Docling → python-docx/pptx
        """
        if use_detailed:
            # 详细模式: 优先 Docling
            if _DOCLING_AVAILABLE:
                return read_with_docling(resolved_path)
            if _MARKITDOWN_AVAILABLE:
                logger.info(f"Docling 不可用，降级到 MarkItDown: {resolved_path}")
                return read_with_markitdown(resolved_path)
        else:
            # 快速模式: 优先 MarkItDown
            if _MARKITDOWN_AVAILABLE:
                return read_with_markitdown(resolved_path)
            if _DOCLING_AVAILABLE:
                logger.info(f"MarkItDown 不可用，降级到 Docling: {resolved_path}")
                return read_with_docling(resolved_path)

        # 最终 fallback: python-docx / python-pptx
        if ext in WORD_EXTENSIONS and _PYTHON_DOCX_AVAILABLE and ext == ".docx":
            return read_docx_fallback(resolved_path)
        if ext in PPTX_EXTENSIONS and _PYTHON_PPTX_AVAILABLE and ext == ".pptx":
            return read_pptx_fallback(resolved_path)

        # 都不可用
        deps = ["markitdown", "docling"]
        if ext in WORD_EXTENSIONS:
            deps.append("python-docx")
        elif ext in PPTX_EXTENSIONS:
            deps.append("python-pptx")
        file_type = {".pdf": "PDF"}.get(ext, ext.upper().lstrip("."))
        if ext in WORD_EXTENSIONS:
            file_type = "Word"
        elif ext in PPTX_EXTENSIONS:
            file_type = "PowerPoint"
        return self._missing_deps_message(file_type, deps)

    @staticmethod
    def _missing_deps_message(file_type: str, packages: list[str]) -> str:
        cmds = " ".join(f"pip install {p}" for p in packages)
        return (
            f"❌ 无法读取 {file_type} 文件，缺少必要依赖。\n"
            f"请安装: {cmds}"
        )


def create_office_reader_tool() -> OfficeReaderTool:
    """工厂函数：创建 OfficeReaderTool 实例"""
    return OfficeReaderTool()


def get_available_formats() -> dict[str, bool]:
    """返回当前环境中各格式的可用状态"""
    return {
        "Excel (.xlsx/.xls)": _OPENPYXL_AVAILABLE,
        "Word/PPT/PDF [markitdown]": _MARKITDOWN_AVAILABLE,
        "Word (.docx) [docling]": _DOCLING_AVAILABLE,
        "Word (.docx) [python-docx]": _PYTHON_DOCX_AVAILABLE,
        "PowerPoint (.pptx) [docling]": _DOCLING_AVAILABLE,
        "PowerPoint (.pptx) [python-pptx]": _PYTHON_PPTX_AVAILABLE,
        "PDF (.pdf) [docling]": _DOCLING_AVAILABLE,
    }
