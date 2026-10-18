"""
backend/chunker/chunker.py
==========================
AST-aware code chunker using Tree-sitter.
Reads source files and splits them into meaningful chunks:
functions, classes, and import blocks.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Node, Parser


# ---------------------------------------------------------------------------
# Language registry
# ---------------------------------------------------------------------------

LANGUAGE_MAP: dict[str, tuple[Language, str]] = {
    ".py":  (Language(tspython.language()),     "python"),
    ".js":  (Language(tsjavascript.language()), "javascript"),
    ".ts":  (Language(tsjavascript.language()), "typescript"),
    ".jsx": (Language(tsjavascript.language()), "javascript"),
    ".tsx": (Language(tsjavascript.language()), "typescript"),
}

FUNCTION_NODES: dict[str, list[str]] = {
    "python":     ["function_definition"],
    "javascript": ["function_declaration", "method_definition", "arrow_function"],
    "typescript": ["function_declaration", "method_definition", "arrow_function"],
}

CLASS_NODES: dict[str, list[str]] = {
    "python":     ["class_definition"],
    "javascript": ["class_declaration"],
    "typescript": ["class_declaration"],
}

IMPORT_NODES: dict[str, list[str]] = {
    "python":     ["import_statement", "import_from_statement"],
    "javascript": ["import_statement"],
    "typescript": ["import_statement"],
}


# ---------------------------------------------------------------------------
# CodeChunk — one meaningful piece of code
# ---------------------------------------------------------------------------

@dataclass
class CodeChunk:
    chunk_id:     str
    chunk_type:   str        # "function" | "class" | "imports"
    language:     str
    file_path:    str
    start_line:   int
    end_line:     int
    name:         str
    signature:    str
    docstring:    str
    raw_code:     str
    dependencies: list[str] = field(default_factory=list)
    git_author:   str = "unknown"

    def to_embed_text(self) -> str:
        """Text sent to the embedding model — signature + docstring + code."""
        parts = [
            f"Language: {self.language}",
            f"File: {self.file_path}",
            f"Type: {self.chunk_type}",
            f"Name: {self.name}",
        ]
        if self.signature:
            parts.append(f"Signature: {self.signature}")
        if self.docstring:
            parts.append(f"Description: {self.docstring}")
        parts.append(f"\nCode:\n{self.raw_code}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

def _get_line_numbers(node: Node) -> tuple[int, int]:
    return node.start_point[0] + 1, node.end_point[0] + 1

def _extract_python_docstring(node: Node, source: bytes) -> str:
    for child in node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "expression_statement":
                    for inner in stmt.children:
                        if inner.type == "string":
                            return _get_node_text(inner, source).strip("'\"").strip()
    return ""

def _extract_js_docstring(node: Node, source: bytes) -> str:
    parent = node.parent
    if parent is None:
        return ""
    siblings = list(parent.children)
    idx = siblings.index(node)
    if idx > 0:
        prev = siblings[idx - 1]
        if prev.type == "comment":
            return _get_node_text(prev, source).strip("/*").strip()
    return ""

def _extract_python_signature(node: Node, source: bytes) -> str:
    for child in node.children:
        if child.type == "block":
            sig_end = child.start_byte
            sig = source[node.start_byte:sig_end].decode("utf-8", errors="replace")
            return sig.strip().rstrip(":")
    return _get_node_text(node, source).split("\n")[0]

def _extract_js_signature(node: Node, source: bytes) -> str:
    return _get_node_text(node, source).split("\n")[0].strip()

def _extract_dependencies(node: Node, source: bytes, language: str) -> list[str]:
    deps: set[str] = set()
    def walk(n: Node) -> None:
        if n.type in ("call", "call_expression"):
            func_node = n.child_by_field_name("function")
            if func_node:
                deps.add(_get_node_text(func_node, source).split("(")[0])
        for child in n.children:
            walk(child)
    walk(node)
    noise = {"self", "cls", "super", "print", "len", "str", "int",
             "list", "dict", "set", "tuple", "range", "type", "isinstance"}
    return [d for d in deps if len(d) > 2 and d not in noise]

def _get_git_author(file_path: str, start_line: int) -> str:
    try:
        result = subprocess.run(
            ["git", "blame", "-L", f"{start_line},{start_line}", "--porcelain", file_path],
            capture_output=True, text=True, timeout=3,
            cwd=os.path.dirname(os.path.abspath(file_path))
        )
        for line in result.stdout.splitlines():
            if line.startswith("author "):
                return line.replace("author ", "").strip()
    except Exception:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# ASTChunker — main class
# ---------------------------------------------------------------------------

class ASTChunker:

    def __init__(self, include_git_blame: bool = True):
        self.include_git_blame = include_git_blame

    def chunk_file(self, file_path: str) -> list[CodeChunk]:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext not in LANGUAGE_MAP:
            return []

        language_obj, lang_name = LANGUAGE_MAP[ext]
        try:
            source_bytes = path.read_bytes()
        except Exception as e:
            print(f"  [error] could not read {file_path}: {e}")
            return []

        parser = Parser(language_obj)
        tree = parser.parse(source_bytes)
        root = tree.root_node
        chunks: list[CodeChunk] = []

        import_chunk = self._extract_imports(root, source_bytes, lang_name, str(path))
        if import_chunk:
            chunks.append(import_chunk)

        self._walk_tree(root, source_bytes, lang_name, str(path), chunks)

        if self.include_git_blame:
            for chunk in chunks:
                chunk.git_author = _get_git_author(str(path), chunk.start_line)

        return chunks

    def chunk_directory(self, dir_path: str, extensions: list[str] | None = None) -> list[CodeChunk]:
        allowed = set(extensions) if extensions else set(LANGUAGE_MAP.keys())
        all_chunks: list[CodeChunk] = []

        for root_dir, _, files in os.walk(dir_path):
            if any(skip in root_dir for skip in
                   [".git", "node_modules", "__pycache__", ".venv", "dist", "build"]):
                continue
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                if Path(fpath).suffix.lower() in allowed:
                    print(f"  chunking: {fpath}")
                    file_chunks = self.chunk_file(fpath)
                    all_chunks.extend(file_chunks)
                    print(f"    → {len(file_chunks)} chunks")

        print(f"\nTotal chunks: {len(all_chunks)}")
        return all_chunks

    def _walk_tree(self, node, source, lang, file_path, chunks):
        fn_types  = FUNCTION_NODES.get(lang, [])
        cls_types = CLASS_NODES.get(lang, [])
        for child in node.children:
            if child.type in fn_types:
                chunk = self._build_function_chunk(child, source, lang, file_path)
                if chunk:
                    chunks.append(chunk)
            elif child.type in cls_types:
                chunk = self._build_class_chunk(child, source, lang, file_path)
                if chunk:
                    chunks.append(chunk)
                self._walk_tree(child, source, lang, file_path, chunks)
            else:
                self._walk_tree(child, source, lang, file_path, chunks)

    def _build_function_chunk(self, node, source, lang, file_path):
        start_line, end_line = _get_line_numbers(node)
        raw_code = _get_node_text(node, source)
        name_node = node.child_by_field_name("name")
        name = _get_node_text(name_node, source) if name_node else "anonymous"
        if lang == "python":
            signature = _extract_python_signature(node, source)
            docstring = _extract_python_docstring(node, source)
        else:
            signature = _extract_js_signature(node, source)
            docstring = _extract_js_docstring(node, source)
        deps = _extract_dependencies(node, source, lang)
        return CodeChunk(
            chunk_id=f"{file_path}::function::{name}::{start_line}",
            chunk_type="function", language=lang, file_path=file_path,
            start_line=start_line, end_line=end_line, name=name,
            signature=signature, docstring=docstring, raw_code=raw_code,
            dependencies=deps,
        )

    def _build_class_chunk(self, node, source, lang, file_path):
        start_line, end_line = _get_line_numbers(node)
        raw_code = _get_node_text(node, source)
        name_node = node.child_by_field_name("name")
        name = _get_node_text(name_node, source) if name_node else "AnonymousClass"
        signature = raw_code.split("\n")[0].strip()
        docstring = _extract_python_docstring(node, source) if lang == "python" else _extract_js_docstring(node, source)
        method_names = []
        fn_types = FUNCTION_NODES.get(lang, [])
        for child in node.children:
            if child.type in fn_types:
                m = child.child_by_field_name("name")
                if m:
                    method_names.append(_get_node_text(m, source))
            for grandchild in child.children:
                if grandchild.type in fn_types:
                    m = grandchild.child_by_field_name("name")
                    if m:
                        method_names.append(_get_node_text(m, source))
        return CodeChunk(
            chunk_id=f"{file_path}::class::{name}::{start_line}",
            chunk_type="class", language=lang, file_path=file_path,
            start_line=start_line, end_line=end_line, name=name,
            signature=signature, docstring=docstring, raw_code=raw_code,
            dependencies=list(set(method_names)),
        )

    def _extract_imports(self, root, source, lang, file_path):
        import_types = IMPORT_NODES.get(lang, [])
        import_lines = []
        imported_names = []
        last_end_line = 1
        for child in root.children:
            if child.type in import_types:
                import_lines.append(_get_node_text(child, source))
                last_end_line = _get_line_numbers(child)[1]
                for sub in child.children:
                    if sub.type in ("dotted_name", "identifier", "string", "import_clause"):
                        imported_names.append(_get_node_text(sub, source).strip("'\""))
        if not import_lines:
            return None
        return CodeChunk(
            chunk_id=f"{file_path}::imports::1",
            chunk_type="imports", language=lang, file_path=file_path,
            start_line=1, end_line=last_end_line, name="imports",
            signature="", docstring=f"Imports for {Path(file_path).name}",
            raw_code="\n".join(import_lines),
            dependencies=list(set(imported_names)),
        )