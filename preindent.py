"""
Ef Reindenter / Python Formatter — Unified Strong Edition
Version 3.2-B — by Dr. Eric O. Flores (Ef-brand)

Features:
• AST-assisted validation and safe transformations
• Stable indentation reconstruction engine
• Heuristic block repair for badly-indented code
• PEP 8 formatting pipeline (tokenized)
• Organize imports (stdlib / third-party / local grouping)
• Remove unused imports
• Simplify boolean-return patterns
• Convert % and .format to f-strings (safe subset)
• Token-safe operator and keyword spacing
• Long-line wrapping (tokens + brackets scanning)
• Multi-line string awareness
• Parenthesis-aware hanging indentation
• Tkinter GUI with structure tree navigation
• External formatter integration (ruff / black / autopep8)
• Project settings support via pyproject.toml

GPL-3 License
"""

from __future__ import annotations

import ast
import builtins
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import tokenize
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from typing import Iterable, List, Optional, Tuple, Dict, Set

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore


# -----------------------------
# Utility: Standard library set
# -----------------------------
try:  # Python ≥3.10
    STDLIB_NAMES: Set[str] = set(sys.stdlib_module_names)  # type: ignore[attr-defined]
except Exception:
    STDLIB_NAMES = {
        "sys", "os", "re", "math", "json", "pathlib", "itertools", "functools",
        "collections", "subprocess", "typing", "asyncio", "dataclasses", "datetime",
        "time", "logging", "argparse", "shutil", "hashlib", "inspect", "tokenize",
        "token", "io", "ast", "site", "importlib",
    }

BUILTIN_NAMES: Set[str] = set(dir(builtins))


def _classify_top_name(name: str) -> str:
    if name.startswith('.'):
        return 'local'
    root = name.split('.')[0]
    if root in STDLIB_NAMES or root in BUILTIN_NAMES:
        return 'stdlib'
    try:
        spec = importlib.util.find_spec(root)
    except Exception:
        spec = None
    if spec and spec.origin:
        origin = (spec.origin or "").lower()
        if "site-packages" in origin or "dist-packages" in origin:
            return 'thirdparty'
        if origin == 'built-in' or ("python" in origin and "lib" in origin and "site-packages" not in origin):
            return 'stdlib'
    return 'local'


@dataclass(order=True)
class ImportLine:
    group: str
    text: str
    key: str


@dataclass
class Settings:
    line_length: int = 79
    comment_width: int = 72
    quote_style: str = "auto"  # auto | single | double


# -----------------------------
# Main Application
# -----------------------------
class PythonReindenterApp:
    """GUI application for PEP 8 formatting + light refactoring."""

    def __init__(self, root):
        self.root = root
        self.root.title("Ef Reindenter / Python Formatter v3.2-B")

        self.filename: Optional[str] = None
        self.indentation_applied = False
        self.version = "3.2-B"
        self.indent_spaces_var = tk.IntVar(value=4)
        self.wrap_lines_var = tk.BooleanVar(value=True)
        self.settings = Settings()

        self._load_project_settings()

        # UI: Paned window with structure tree + editor
        self.pane = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        self.sidebar = ttk.Frame(self.pane, width=260)
        self.pane.add(self.sidebar, weight=0)
        self.editor_frame = ttk.Frame(self.pane)
        self.pane.add(self.editor_frame, weight=1)
        self.pane.pack(expand=True, fill="both")

        self.create_menu()

        # Structure tree
        self.tree = ttk.Treeview(self.sidebar, columns=("line",), show="tree")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Editor
        self.text_display = tk.Text(
            self.editor_frame,
            wrap="none",
            state="disabled",
            font=("Courier", 12),
        )
        self.text_display.pack(expand=True, fill="both")

        # Status
        self.status_label = tk.Label(self.root, text="Ready", anchor="w")
        self.status_label.pack(fill="x")

    # --------------- UI ---------------
    def create_menu(self):
        menubar = tk.Menu(self.root)

        # File
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="Load", command=self.load_file)
        self.file_menu.add_command(label="Save", command=self.save_file, state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=0)
        indent_menu = tk.Menu(edit_menu, tearoff=0)
        indent_menu.add_radiobutton(
            label="2 Spaces",
            variable=self.indent_spaces_var,
            value=2,
            command=self._status_indent_setting,
        )
        indent_menu.add_radiobutton(
            label="4 Spaces",
            variable=self.indent_spaces_var,
            value=4,
            command=self._status_indent_setting,
        )
        edit_menu.add_cascade(label="Set Indent Spaces", menu=indent_menu)
        edit_menu.add_checkbutton(
            label="Wrap long lines to 79 chars",
            variable=self.wrap_lines_var,
            onvalue=True,
            offvalue=False,
        )
        edit_menu.add_command(label="Apply Indent", command=self.apply_indent_from_menu)
        edit_menu.add_separator()
        edit_menu.add_command(label="Format (PEP 8)", command=self.apply_pep8_format)
        edit_menu.add_command(label="Organize Imports (PEP 8)", command=self.organize_imports)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Refactor
        ref_menu = tk.Menu(menubar, tearoff=0)
        ref_menu.add_command(label="Remove Unused Imports", command=self.remove_unused_imports)
        ref_menu.add_command(label="Simplify Boolean Returns", command=self.simplify_boolean_returns)
        ref_menu.add_command(label="Convert to f-strings (safe)", command=self.convert_to_fstrings)
        menubar.add_cascade(label="Refactor", menu=ref_menu)

        # Tools (external formatters)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="External Formatters…", command=self.run_external_formatter)
        tools_menu.add_command(label="Settings…", command=self.open_settings_dialog)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _status_indent_setting(self):
        self.set_status(f"Indentation = {self.indent_spaces_var.get()} spaces")

    # --------------- Settings ---------------
    def _load_project_settings(self):
        # Look for pyproject.toml next to opened file (later), or current cwd now
        cfg = None
        search_dirs = [os.getcwd()]
        if self.filename:
            search_dirs.insert(0, os.path.dirname(self.filename))

        for d in search_dirs:
            path = os.path.join(d, "pyproject.toml")
            if os.path.isfile(path) and tomllib is not None:
                try:
                    with open(path, "rb") as f:
                        data = tomllib.load(f)
                    tool = data.get("tool", {}).get("pep8fmt", {})
                    if isinstance(tool, dict):
                        cfg = tool
                        break
                except Exception:
                    pass
        if cfg:
            self.settings.line_length = int(cfg.get("line-length", self.settings.line_length))
            self.settings.comment_width = int(cfg.get("comment-width", self.settings.comment_width))
            self.settings.quote_style = str(cfg.get("quote-style", self.settings.quote_style))

    def open_settings_dialog(self):
        top = tk.Toplevel(self.root)
        top.title("Settings")
        tk.Label(top, text="Max line length:").grid(row=0, column=0, sticky="w")
        e_len = tk.Entry(top)
        e_len.insert(0, str(self.settings.line_length))
        e_len.grid(row=0, column=1, padx=6, pady=4)
        tk.Label(top, text="Comment width:").grid(row=1, column=0, sticky="w")
        e_cw = tk.Entry(top)
        e_cw.insert(0, str(self.settings.comment_width))
        e_cw.grid(row=1, column=1, padx=6, pady=4)
        tk.Label(top, text="Quote style (auto/single/double):").grid(row=2, column=0, sticky="w")
        e_q = tk.Entry(top)
        e_q.insert(0, self.settings.quote_style)
        e_q.grid(row=2, column=1, padx=6, pady=4)

        def ok():
            try:
                self.settings.line_length = int(e_len.get() or self.settings.line_length)
                self.settings.comment_width = int(e_cw.get() or self.settings.comment_width)
                self.settings.quote_style = (e_q.get() or self.settings.quote_style).strip().lower()
                top.destroy()
                self.set_status("Settings updated")
            except Exception as e:
                messagebox.showerror("Invalid settings", str(e))

        tk.Button(top, text="OK", command=ok).grid(row=3, column=0, columnspan=2, pady=6)
        top.transient(self.root)
        top.grab_set()
        self.root.wait_window(top)

    # --------------- File ops ---------------
    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            self.filename = path
            self._load_project_settings()  # Re-load settings based on new file location
            self.display_code(code)
            self.indentation_applied = False
            self.update_save_state()
            self.set_status(f"Loaded: {path}")
            self._refresh_structure_tree(code)
        except Exception as e:
            messagebox.showerror("Error Loading File", f"Could not read file:\n{e}")
            self.set_status("Error loading file")

    def save_file(self):
        if not self.filename:
            path = filedialog.asksaveasfilename(
                defaultextension=".py",
                filetypes=[("Python Files", "*.py")],
            )
            if not path:
                return
            self.filename = path
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(self._get_buffer().rstrip() + "\n")
            messagebox.showinfo("Save", f"File saved: {self.filename}")
            self.set_status(f"Saved: {self.filename}")
            self.indentation_applied = False
            self.update_save_state()
        except Exception as e:
            messagebox.showerror("Error Saving File", f"Could not save file:\n{e}")
            self.set_status("Error saving file")

    # --------------- Buffer helpers ---------------
    def display_code(self, code: str):
        self.text_display.config(state="normal")
        self.text_display.delete("1.0", tk.END)
        self.text_display.insert("1.0", code)
        self.text_display.config(state="disabled")
        self._refresh_structure_tree(code)

    def _get_buffer(self) -> str:
        self.text_display.config(state="normal")
        code = self.text_display.get("1.0", tk.END)
        self.text_display.config(state="disabled")
        return code

    # --------------- Structure pane ---------------
    def _refresh_structure_tree(self, code: str):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        root = self.tree.insert(
            "",
            "end",
            text=os.path.basename(self.filename or "<buffer>"),
            values=(1,),
        )

        def walk(parent, node):
            for n in getattr(node, "body", []):
                if isinstance(n, ast.ClassDef):
                    ci = self.tree.insert(
                        parent,
                        "end",
                        text=f"class {n.name}",
                        values=(getattr(n, "lineno", 1),),
                    )
                    walk(ci, n)
                elif isinstance(n, ast.FunctionDef):
                    self.tree.insert(
                        parent,
                        "end",
                        text=f"def {n.name}()",
                        values=(getattr(n, "lineno", 1),),
                    )
                elif isinstance(n, ast.AsyncFunctionDef):
                    self.tree.insert(
                        parent,
                        "end",
                        text=f"async def {n.name}()",
                        values=(getattr(n, "lineno", 1),),
                    )

        walk(root, tree)

    def _on_tree_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        line = self.tree.set(sel[0], "line")
        try:
            lno = int(line)
        except Exception:
            return
        self._highlight_line(lno)

    def _highlight_line(self, lno: int):
        self.text_display.config(state="normal")
        index = f"{lno}.0"
        self.text_display.see(index)
        self.text_display.tag_remove("hi", "1.0", tk.END)
        self.text_display.tag_add("hi", index, f"{lno}.0 lineend")
        self.text_display.tag_config("hi", background="#ffeeaa")
        self.text_display.config(state="disabled")

    # --------------- Indentation (logic + heuristic repair) ---------------
    def apply_indent_from_menu(self):
        """
        Applies heuristic block repair + reindent.

        NOTE:
        This does NOT require the code to be syntactically valid.
        It will best-effort normalize indentation even if the AST
        parser would fail.
        """
        code = self._get_buffer()
        spaces = self.indent_spaces_var.get()
        code = self._normalize_newlines(code)
        code = self._detab(code, spaces)
        code = self._heuristic_block_repair(code, spaces)
        code = self._reindent_only(code, spaces)
        code = self._strip_trailing_whitespace(code).rstrip() + "\n"

        self.display_code(code)
        self.indentation_applied = True
        self.update_save_state()
        self.set_status("Indentation applied (with heuristic repair)")

    def _heuristic_block_repair(self, s: str, spaces: int) -> str:
        """
        Best-effort structural repair before reindent:

        • Re-aligns elif/else/except/finally under their controlling
          if/try/except.
        • Fixes obviously wrong top-level returns/breaks/etc that
          should be inside a block.
        • Indents def under an active class when it looks like a
          mis-dedented method.

        The goal is to give _reindent_only a more sensible starting
        structure without being overly aggressive on already-valid code.
        """
        lines = s.splitlines()
        if not lines:
            return s

        # (keyword, indent, line_index)
        colon_stack: List[Tuple[str, int, int]] = []
        control_keywords = {
            "if",
            "elif",
            "else",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
            "def",
            "class",
        }
        repair_keywords = {"return", "break", "continue", "raise", "pass"}

        def leading_spaces(line: str) -> int:
            return len(line) - len(line.lstrip(" "))

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            indent = leading_spaces(line)

            # Pop colon_stack when indentation decreases clearly
            while colon_stack and indent < colon_stack[-1][1]:
                colon_stack.pop()

            m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", stripped)
            token = m.group(1) if m else ""

            # ----- 1) Align elif/else/except/finally with proper opener -----
            if token in {"elif", "else", "except", "finally"}:
                target_indent: Optional[int] = None
                for kw, kw_indent, _ in reversed(colon_stack):
                    if token in {"elif", "else"} and kw in {"if", "elif"}:
                        target_indent = kw_indent
                        break
                    if token in {"except", "finally"} and kw in {"try", "except"}:
                        target_indent = kw_indent
                        break
                if target_indent is not None and indent != target_indent:
                    # Be conservative: only adjust if current indent is smaller
                    # or obviously misaligned.
                    if indent < target_indent or indent % spaces != 0:
                        lines[idx] = " " * target_indent + stripped
                        indent = target_indent

            # ----- 2) Fix top-level returns/breaks/etc that belong in a block -----
            if token in repair_keywords and indent == 0 and colon_stack:
                # Find nearest block-like opener
                for kw, kw_indent, _ in reversed(colon_stack):
                    if kw in {"def", "for", "while", "if", "try", "with", "class"}:
                        target_indent = kw_indent + spaces
                        if target_indent > 0:
                            lines[idx] = " " * target_indent + stripped
                            indent = target_indent
                        break

            # ----- 3) Methods inside a class: def at same level as class -----
            if token == "def" and colon_stack:
                # Look up nearest class
                for kw, kw_indent, _ in reversed(colon_stack):
                    if kw == "class":
                        class_indent = kw_indent
                        if indent <= class_indent:
                            target_indent = class_indent + spaces
                            lines[idx] = " " * target_indent + stripped
                            indent = target_indent
                        break

            # ----- Track colon-based blocks for later lines -----
            if stripped.endswith(":") and token in control_keywords:
                colon_stack.append((token, indent, idx))

        return "\n".join(lines)

    def _reindent_only(self, s: str, spaces: int) -> str:
        """
        Re-indents code based on original indentation structure.
        Uses a stack to track the original file's indent/dedent levels.
        """
        code = s.strip("\n")
        lines = code.splitlines()
        indented_lines: List[str] = []

        level = 0               # Current logical indent level (0, 1, 2...)
        indent_stack = [0]      # Stack of original character counts (e.g., [0, 4, 8])
        paren_balance = 0
        in_triple = False
        prev_backslash = False

        for line in lines:
            original = line
            stripped = line.strip()
            logic = re.sub(r"#.*$", "", stripped).strip()

            if not logic:
                indented_lines.append("")
                prev_backslash = False
                continue

            # Multi-line string handling
            if '"""' in logic or "'''" in logic:
                if logic.count('"""') % 2 == 1 or logic.count("'''") % 2 == 1:
                    in_triple = not in_triple

            if in_triple:
                indented_lines.append(" " * (level * spaces) + original.lstrip())
                prev_backslash = False
                continue

            # Paren balance
            paren_balance += logic.count("(") + logic.count("[") + logic.count("{")
            paren_balance -= logic.count(")") + logic.count("]") + logic.count("}")

            # Indent/Dedent logic based on original spacing
            if paren_balance == 0 and not prev_backslash:
                original_indent_len = len(original) - len(original.lstrip(" "))

                if original_indent_len > indent_stack[-1]:
                    indent_stack.append(original_indent_len)
                    level += 1
                elif original_indent_len < indent_stack[-1]:
                    while original_indent_len < indent_stack[-1] and len(indent_stack) > 1:
                        indent_stack.pop()
                        level = max(0, level - 1)
                    # If it still doesn't match, reset stack heuristically
                    if original_indent_len != indent_stack[-1]:
                        steps = max(0, original_indent_len // spaces)
                        indent_stack = [i * spaces for i in range(steps + 1)]
                        level = steps

            eff = level
            if re.match(r"^(elif|else|except|finally)\b", logic):
                eff = max(0, eff - 1)

            visual = eff * spaces

            if paren_balance > 0 or prev_backslash:
                visual = (eff + 1) * spaces
                if re.match(r"^[)\]}]", logic) and paren_balance == 0:
                    visual = eff * spaces

            indented_lines.append(" " * visual + original.lstrip())

            prev_backslash = stripped.endswith("\\")

        return "\n".join(indented_lines)

    # --------------- PEP 8 formatting pipeline ---------------
    def apply_pep8_format(self):
        code = self._get_buffer()
        ok, err = self._ast_valid(code)
        if not ok:
            messagebox.showwarning("Syntax error", f"Parsing failed; not formatting.\n\n{err}")
            return
        spaces = self.indent_spaces_var.get()
        code = self._normalize_newlines(code)
        code = self._detab(code, spaces)
        code = self._strip_trailing_whitespace(code)
        code = self._fix_whitespace_pet_peeves_tokenized(code)
        code = self._fix_operator_spacing_tokenized(code)
        code = self._fix_keyword_equals_tokenized(code)
        code = self._normalize_comments(code)
        code = self._enforce_blank_lines(code)
        code = self._reindent_only(code, spaces)
        if self.wrap_lines_var.get():
            code = self._wrap_long_lines_tokenized(
                code,
                width=self.settings.line_length,
                comment_width=self.settings.comment_width,
            )
        code = self._strip_trailing_whitespace(code).rstrip() + "\n"
        self.display_code(code)
        self.indentation_applied = True
        self.update_save_state()
        self.set_status("PEP 8 formatting applied")

    # --------------- Import organization ---------------
    def organize_imports(self):
        code = self._get_buffer()
        ok, err = self._ast_valid(code)
        if not ok:
            messagebox.showwarning("Syntax error", f"Parsing failed; cannot organize imports.\n\n{err}")
            return
        new_code = self._reorder_top_level_imports(code)
        if new_code != code:
            self.display_code(new_code)
            self.indentation_applied = True
            self.update_save_state()
            self.set_status("Imports organized (top-level)")
        else:
            self.set_status("No top-level import changes detected")

    def _reorder_top_level_imports(self, code: str) -> str:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code
        src_lines = code.splitlines()
        docstring_span = self._module_docstring_span(tree)
        fut_spans = self._future_import_spans(tree)
        imports: List[Tuple[int, int, ImportLine]] = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    continue
                start, end = self._node_line_span(node)
                text = "\n".join(src_lines[start - 1: end])
                for one in text.splitlines():
                    if not one.strip() or one.strip().startswith("#"):
                        continue
                    norm = one.rstrip()
                    root_name = self._top_import_root(norm)
                    group = _classify_top_name(root_name) if root_name else "local"
                    key = self._import_sort_key(norm)
                    imports.append((start, end, ImportLine(group, norm, key)))
        if not imports:
            return code
        stdlib = sorted([im for _, _, im in imports if im.group == 'stdlib'], key=lambda i: i.key)
        thirdp = sorted([im for _, _, im in imports if im.group == 'thirdparty'], key=lambda i: i.key)
        local = sorted([im for _, _, im in imports if im.group == 'local'], key=lambda i: i.key)
        new_block_lines: List[str] = []
        if stdlib:
            new_block_lines.extend([im.text for im in stdlib])
        if thirdp:
            if new_block_lines:
                new_block_lines.append("")
            new_block_lines.extend([im.text for im in thirdp])
        if local:
            if new_block_lines:
                new_block_lines.append("")
            new_block_lines.extend([im.text for im in local])
        new_block = "\n".join(new_block_lines)
        block_start = None
        block_end = None
        for start, end, _ in imports:
            block_start = start if block_start is None else min(block_start, start)
            block_end = end if block_end is None else max(block_end, end)
        after_line = 0
        if docstring_span:
            after_line = max(after_line, docstring_span[1])
        for sp in fut_spans:
            after_line = max(after_line, sp[1])

        if block_start is None:
            return code

        block_start = max(block_start, after_line + 1)
        i = block_start - 1
        while i < len(src_lines) and (
            src_lines[i].strip().startswith(("import ", "from "))
            or not src_lines[i].strip()
            or src_lines[i].lstrip().startswith("#")
        ):
            i += 1
        block_end = i
        header = src_lines[:after_line]
        tail = src_lines[block_end:]
        rebuilt: List[str] = []
        rebuilt.extend(header)
        if rebuilt and rebuilt[-1].strip():
            rebuilt.append("")
        if new_block:
            rebuilt.extend(new_block.splitlines())
        if tail and tail[0].strip():
            rebuilt.append("")
        rebuilt.extend(tail)
        return "\n".join(line.rstrip() for line in rebuilt)

    def _module_docstring_span(self, tree: ast.Module) -> Optional[Tuple[int, int]]:
        if not tree.body:
            return None
        node0 = tree.body[0]
        if (
            isinstance(node0, ast.Expr)
            and isinstance(getattr(node0, "value", None), ast.Constant)
            and isinstance(node0.value.value, str)
        ):
            return self._node_line_span(node0)
        return None

    def _future_import_spans(self, tree: ast.Module) -> List[Tuple[int, int]]:
        spans: List[Tuple[int, int]] = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                spans.append(self._node_line_span(node))
        return spans

    def _node_line_span(self, node: ast.AST) -> Tuple[int, int]:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        return (start, end)

    def _top_import_root(self, line: str) -> str:
        m = re.match(r"\s*import\s+([A-Za-z_][A-Za-z0-9_\.]*)(\s+as\s+\w+)?", line)
        if m:
            return m.group(1).split(".")[0]
        m = re.match(r"\s*from\s+([\.A-Za-z_][A-Za-z0-9_\.]*)\s+import\s+", line)
        if m:
            return m.group(1)
        return ""

    def _import_sort_key(self, line: str) -> str:
        return re.sub(r"\s+", " ", line.strip()).lower()

    # --------------- Tokenize-aware whitespace fixes ---------------
    @staticmethod
    def _normalize_newlines(s: str) -> str:
        return s.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _detab(s: str, spaces: int) -> str:
        return s.expandtabs(spaces)

    @staticmethod
    def _strip_trailing_whitespace(s: str) -> str:
        return "\n".join(line.rstrip() for line in s.splitlines())

    def _fix_whitespace_pet_peeves_tokenized(self, s: str) -> str:
        out_lines: List[str] = []
        for line in s.splitlines():
            line = re.sub(r"([A-Za-z0-9_\]\)])\s+\(", r"\1(", line)   # func (x) -> func(x)
            line = re.sub(r"\s+\[", "[", line)                        # a [i] -> a[i]
            line = re.sub(r"\s+,", ",", line)                         # no space before comma
            line = re.sub(r",\s*", ", ", line)
            line = re.sub(r",\s+([)\]}])", r",\1", line)
            line = re.sub(r"\s+:\s*", ": ", line)                     # dict/kwargs colon
            prefix = re.match(r"\s*", line).group(0)
            rest = line[len(prefix):]
            rest = re.sub(r"\s{2,}", " ", rest)
            out_lines.append(prefix + rest)
        return "\n".join(out_lines)

    def _fix_operator_spacing_tokenized(self, s: str) -> str:
        ops = {
            "+=", "-=", "*=", "/=", "%=", "**=", "//=", "==", "!=", "<=",
            ">=", "<<=", ">>=", "<<", ">>", "+", "-", "*", "//", "/", "%", "**",
            "=", "<", ">",
        }
        keywords = {"and", "or", "in", "is"}

        def fix_line(line: str) -> str:
            if not line.strip() or line.lstrip().startswith("#"):
                return line.rstrip()
            if "#" in line:
                code_part, comment = line.split("#", 1)
            else:
                code_part, comment = line, None

            # Don't add spaces around = in kwargs
            if "(" in code_part or "def " in code_part:
                code_part = re.sub(
                    r"(\b[A-Za-z_][A-Za-z0-9_]*)\s*=\s*",
                    r"\1=",
                    code_part,
                )

            buff = io.StringIO(code_part)
            new_parts: List[str] = []
            prev_end = (1, 0)
            try:
                for tok in tokenize.generate_tokens(buff.readline):
                    ttype, tstr, start, end, _ = tok
                    gap_start = self._pos_to_idx(code_part, prev_end)
                    gap_end = self._pos_to_idx(code_part, start)
                    gap = code_part[gap_start:gap_end]

                    new_parts.append(gap)

                    if ttype == tokenize.OP and tstr in ops:
                        # Don't add space for '=' if it's a kwarg (handled above)
                        if tstr == "=" and gap_start > 0 and code_part[gap_start - 1].isalnum():
                            new_parts.append(tstr)
                        else:
                            new_parts.append(f" {tstr} ")
                    elif ttype == tokenize.NAME and tstr in keywords:
                        new_parts.append(f" {tstr} ")
                    else:
                        new_parts.append(tstr)
                    prev_end = end
            except tokenize.TokenError:
                # Fallback if tokenizing fails (e.g., incomplete line)
                code_part = re.sub(
                    r"\s*([+\-*/%]=|\*\*=?|//=|==|!=|<=|>=|<<=?|>>=?|[+\-*/%]|/|=|<|>)\s*",
                    lambda m: f" {m.group(1)} ",
                    code_part,
                )
                code_part = re.sub(r"\s{2,}", " ", code_part)
                result = code_part
            else:
                result = "".join(new_parts)
                result = re.sub(r"\s{2,}", " ", result)

            if comment is not None:
                result = result.rstrip() + "  # " + comment.strip()
            return result.rstrip()

        return "\n".join(fix_line(l) for l in s.splitlines())

    def _fix_keyword_equals_tokenized(self, s: str) -> str:
        def fix_line(line: str) -> str:
            if not line.strip() or line.lstrip().startswith("#"):
                return line
            if "#" in line:
                code, comment = line.split("#", 1)
                comment = "  # " + comment.strip()
            else:
                code, comment = line, ""
            if "def " in code or "(" in code:
                code = re.sub(r":\s*=", ":=", code)  # protect walrus
                code = re.sub(
                    r"(\b[A-Za-z_][A-Za-z0-9_]*)\s*=\s*",
                    r"\1=",
                    code,
                )
                code = code.replace(":=", ":= ")  # Add space back for walrus
            result = code.rstrip() + comment
            return result.rstrip()

        return "\n".join(fix_line(l) for l in s.splitlines())

    @staticmethod
    def _normalize_comments(s: str) -> str:
        lines = s.splitlines()
        out: List[str] = []
        for line in lines:
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            if stripped.startswith("#") and not stripped.startswith("#!"):
                if stripped.startswith("# -*-") or stripped.startswith("# coding"):
                    out.append(line.rstrip())
                    continue
                content = stripped[1:]
                if content and not content.startswith(" "):
                    content = " " + content
                wrapped = textwrap.fill(
                    content.lstrip(),
                    width=72,
                    initial_indent="",
                    subsequent_indent="",
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                for w in wrapped.split("\n"):
                    out.append((indent + "#" + (" " if w else "") + w).rstrip())
            else:
                if "#" in line and not stripped.startswith("#"):
                    code, comment = line.split("#", 1)
                    code = code.rstrip()
                    comment = "  # " + comment.strip()
                    out.append((code + comment).rstrip())
                else:
                    out.append(line.rstrip())
        return "\n".join(out)

    @staticmethod
    def _enforce_blank_lines(s: str) -> str:
        lines = s.splitlines()
        out: List[str] = []
        i = 0

        def is_toplevel_def_or_class(idx: int) -> bool:
            if idx >= len(lines):
                return False
            line = lines[idx]
            if line.lstrip().startswith("@"):
                j = idx + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    return lines[j].startswith("def ") or lines[j].startswith("class ")
                return False
            return line.startswith("def ") or line.startswith("class ")

        def is_method_def(line: str) -> bool:
            return re.match(r"\s+def\s+\w", line) is not None

        while i < len(lines):
            line = lines[i]
            if is_toplevel_def_or_class(i):
                while out and out[-1].strip() == "":
                    out.pop()
                if out:
                    out.append("")
                    out.append("")
                while i < len(lines) and lines[i].lstrip().startswith("@"):
                    out.append(lines[i].rstrip())
                    i += 1
                if i < len(lines):
                    out.append(lines[i].rstrip())
                    i += 1
                    continue
            if is_method_def(line) and out and out[-1].strip():
                out.append("")
            out.append(line.rstrip())
            i += 1
        while out and out[-1].strip() == "":
            out.pop()
        return "\n".join(out)

    def _wrap_long_lines_tokenized(self, s: str, width: int = 79, comment_width: int = 72) -> str:
        out: List[str] = []
        for line in s.splitlines():
            if len(line) <= width:
                out.append(line)
                continue
            if line.lstrip().startswith("#"):
                indent = re.match(r"\s*", line).group(0)
                text = line.strip()[1:].lstrip()
                wrapped = textwrap.fill(
                    text,
                    width=comment_width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                out.extend((indent + "# " + w).rstrip() for w in wrapped.split("\n"))
                continue
            if not any(ch in line for ch in "([{"):
                out.append(line)
                continue
            try:
                tokens = list(tokenize.generate_tokens(io.StringIO(line).readline))
            except tokenize.TokenError:
                out.append(line)
                continue
            breaks: List[int] = []
            level = 0
            for tok in tokens:
                ttype, tstr, start, end, _ = tok
                if ttype == tokenize.OP:
                    if tstr in "([{":
                        level += 1
                    elif tstr in ")]}":
                        level = max(0, level - 1)
                    elif tstr == "," and level > 0:
                        idx = self._pos_to_idx(line, end)
                        breaks.append(idx)
            if not breaks:
                out.append(line)
                continue
            indent = re.match(r"\s*", line).group(0)
            hang = indent + " " * 4
            remainder = line.strip()
            pieces: List[str] = []
            current = remainder
            while len((hang if pieces else indent) + current) > width:
                limit = width - len((hang if pieces else indent))
                base_offset = len(line) - len(remainder)
                candidate_positions = [b for b in breaks if b - base_offset < limit]
                if not candidate_positions:
                    break
                cut_idx_src = max(candidate_positions)
                rel_cut = cut_idx_src - base_offset
                first = current[:rel_cut].rstrip()
                rest = current[rel_cut:].lstrip()
                pieces.append(((indent if not pieces else hang) + first).rstrip())
                current = rest
            if current:
                pieces.append(((indent if not pieces else hang) + current).rstrip())
            out.extend(pieces)
        return "\n".join(out)

    # --------------- Refactor: Remove Unused Imports ---------------
    def remove_unused_imports(self):
        code = self._get_buffer()
        ok, err = self._ast_valid(code)
        if not ok:
            messagebox.showwarning("Syntax error", f"Parsing failed; cannot refactor.\n\n{err}")
            return
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            messagebox.showwarning("Syntax error", f"Parsing failed; cannot refactor.\n\n{e}")
            return

        used: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                used.add(node.value.id)

        lines = code.splitlines()
        new_lines: List[str] = []
        modified = False

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                new_lines.append(line)
                continue

            # Check if line is part of a multi-line import
            if i > 1 and (
                lines[i - 2].strip().endswith(",")
                or lines[i - 2].strip().endswith("\\")
                or (
                    lines[i - 2].strip().startswith("from ")
                    and lines[i - 2].strip().endswith("(")
                )
            ):
                new_lines.append(line)
                continue
            if i < len(lines) and (
                stripped.endswith(",")
                or stripped.endswith("\\")
                or (stripped.startswith("from ") and stripped.endswith("("))
            ):
                new_lines.append(line)
                continue

            code_part, comment = (line.split("#", 1) + [""])[:2]
            comment_str = ("  #" + comment) if comment else ""

            if stripped.startswith("import "):
                try:
                    names = [p.strip() for p in code_part[len("import ") :].split(",")]
                    kept = []
                    for n in names:
                        alias = n.split(" as ")[-1].strip()
                        root = alias.split(".")[0]
                        if root in used or n.startswith("__future__"):
                            kept.append(n)
                    if kept:
                        new_lines.append(
                            f"{line.split('import ')[0]}import " + ", ".join(kept) + comment_str
                        )
                        if len(kept) < len(names):
                            modified = True
                    else:
                        modified = True
                except Exception:
                    new_lines.append(line)

            elif stripped.startswith("from "):
                m = re.match(r"(\s*from\s+[\.\w]+)\s+import\s+(.*)$", code_part)
                if m:
                    header, namestr = m.group(1), m.group(2)
                    if namestr.strip().startswith("("):
                        new_lines.append(line)
                        continue
                    parts = [p.strip() for p in namestr.split(",")]
                    kept = []
                    for p in parts:
                        alias = re.split(r"\s+as\s+", p)[-1]
                        name = re.split(r"\s+as\s+", p)[0]
                        symbol = alias if alias != p else name
                        if name == "*" or symbol in used or header.strip().endswith("__future__"):
                            kept.append(p)
                    if kept:
                        new_lines.append(
                            f"{header} import " + ", ".join(kept) + comment_str
                        )
                        if len(kept) < len(parts):
                            modified = True
                    else:
                        modified = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        out = "\n".join(new_lines)
        if modified:
            self.display_code(out)
            self.set_status("Removed unused imports (conservative)")
            self.indentation_applied = True
            self.update_save_state()
        else:
            self.set_status("No unused imports found (conservative)")

    # --------------- Refactor: Simplify Boolean Returns ---------------
    def simplify_boolean_returns(self):
        code = self._get_buffer()
        ok, err = self._ast_valid(code)
        if not ok:
            messagebox.showwarning("Syntax error", f"Parsing failed; cannot refactor.\n\n{err}")
            return

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            messagebox.showwarning("Syntax error", f"Parsing failed; cannot refactor.\n\n{e}")
            return

        replacements: List[Tuple[Tuple[int, int], str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                body = node.body
                orelse = node.orelse
                if (
                    len(body) == 1
                    and len(orelse) == 1
                    and isinstance(body[0], ast.Return)
                    and isinstance(orelse[0], ast.Return)
                ):
                    rt = getattr(body[0], "value", None)
                    rf = getattr(orelse[0], "value", None)
                    if isinstance(rt, ast.Constant) and isinstance(rf, ast.Constant):
                        rt_val = rt.value
                        rf_val = rf.value
                    else:
                        continue
                    if rt_val is True and rf_val is False:
                        seg = ast.get_source_segment(code, node)
                        test_seg = ast.get_source_segment(code, node.test)
                        if seg and test_seg:
                            indent = re.match(r"\s*", seg).group(0)
                            repl = f"{indent}return bool({test_seg})"
                            replacements.append(
                                ((node.lineno, node.end_lineno or node.lineno), repl)
                            )
                    elif rt_val is False and rf_val is True:
                        seg = ast.get_source_segment(code, node)
                        test_seg = ast.get_source_segment(code, node.test)
                        if seg and test_seg:
                            indent = re.match(r"\s*", seg).group(0)
                            repl = f"{indent}return not bool({test_seg})"
                            replacements.append(
                                ((node.lineno, node.end_lineno or node.lineno), repl)
                            )

        if not replacements:
            self.set_status("No boolean return patterns found")
            return

        lines = code.splitlines()
        modified = False
        for (start, end), text in sorted(replacements, key=lambda x: x[0][0], reverse=True):
            if start <= end:
                lines[start - 1 : end] = [text]
                modified = True

        if modified:
            out = "\n".join(lines)
            self.display_code(out)
            self.set_status("Simplified boolean returns (conservative)")
            self.indentation_applied = True
            self.update_save_state()
        else:
            self.set_status("No boolean return patterns found")

    # --------------- Refactor: Convert to f-strings (safe) ---------------
    def convert_to_fstrings(self):
        code = self._get_buffer()
        ok, err = self._ast_valid(code)
        if not ok:
            messagebox.showwarning("Syntax error", f"Parsing failed; cannot refactor.\n\n{err}")
            return

        out_lines: List[str] = []
        modified = False

        for line in code.splitlines():
            new_line = line

            # .format case
            m = re.search(
                r"([rubf]*['\"])((?:[^\\]|\\.)*?)\1\.format\(([^)]*)\)",
                line,
                re.IGNORECASE,
            )
            if m and "f" not in m.group(1).lower():
                quote = m.group(1)
                template = m.group(2)
                args_str = m.group(3)

                if re.search(r"[\(\)\[\]\{\}]", args_str):
                    out_lines.append(line)
                    continue

                args = [a.strip() for a in args_str.split(",") if a.strip()]
                kwargs: Dict[str, str] = {}
                pos_args: List[str] = []
                try:
                    for arg in args:
                        if "=" in arg:
                            k, v = arg.split("=", 1)
                            kwargs[k.strip()] = v.strip()
                        else:
                            pos_args.append(arg)
                except Exception:
                    out_lines.append(line)
                    continue

                if all(
                    re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v)
                    for v in kwargs.values()
                ) and all(
                    re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v)
                    for v in pos_args
                ):
                    try:
                        def repl_field(mf: re.Match) -> str:
                            key = mf.group(1).strip()
                            fmt = mf.group(2) or ""
                            if key.isdigit():
                                idx = int(key)
                                if 0 <= idx < len(pos_args):
                                    return "{" + pos_args[idx] + fmt + "}"
                            elif key in kwargs:
                                return "{" + kwargs[key] + fmt + "}"
                            elif key in pos_args:
                                return "{" + key + fmt + "}"
                            raise ValueError("Cannot map field")

                        templ = re.sub(
                            r"\{\s*([^\}:!]+)\s*([:!][^\}]*)?\}",
                            repl_field,
                            template,
                        )
                        templ = templ.replace("{", "{{").replace("}", "}}")

                        new_line = (
                            line[: m.start()]
                            + f"f{quote}"
                            + templ
                            + f"{quote}"
                            + line[m.end() :]
                        )
                        modified = True
                    except Exception:
                        new_line = line

            # % formatting
            mp = re.search(
                r"([rubf]*['\"])((?:[^\\]|\\.)*?)\1\s*%\s*(\(([^\)]*)\)|[A-Za-z_][A-Za-z0-9_]*)",
                new_line,
            )
            if mp and "f" not in mp.group(1).lower():
                quote = mp.group(1)
                template = mp.group(2)
                rhs = mp.group(3)
                names: List[str] = []

                if rhs.startswith("("):
                    parts = [p.strip() for p in mp.group(4).split(",") if p.strip()]
                    if all(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p) for p in parts):
                        names = parts
                else:
                    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rhs):
                        names = [rhs]

                if names:
                    idx = 0

                    def repl_pct(mt: re.Match) -> str:
                        nonlocal idx
                        spec = mt.group(0)
                        if idx < len(names):
                            fmt = ""
                            if spec.endswith("r"):
                                fmt = "!r"
                            s = "{" + names[idx] + fmt + "}"
                            idx += 1
                            return s
                        return spec

                    templ = re.sub(r"%%", "@@PERCENT@@", template)
                    templ = re.sub(r"%(?:\.\d+)?[srdfige]", repl_pct, templ)
                    templ = templ.replace("@@PERCENT@@", "%")
                    templ = templ.replace("{", "{{").replace("}", "}}")

                    new_line = (
                        new_line[: mp.start()]
                        + f"f{quote}"
                        + templ
                        + f"{quote}"
                        + new_line[mp.end() :]
                    )
                    modified = True

            out_lines.append(new_line)

        if modified:
            out = "\n".join(out_lines)
            self.display_code(out)
            self.set_status("Converted some strings to f-strings (safe subset)")
            self.indentation_applied = True
            self.update_save_state()
        else:
            self.set_status("No safe f-string conversions found")

    # --------------- External formatters ---------------
    def run_external_formatter(self):
        fmt = self._choose_formatter()
        if not fmt:
            return
        tool = fmt
        code = self._get_buffer()
        with tempfile.TemporaryDirectory() as td:
            tmp = os.path.join(td, "buf.py")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(code)
            try:
                if tool == "ruff":
                    cmd = ["ruff", "format", tmp]
                elif tool == "black":
                    cmd = ["black", "--quiet", tmp]
                elif tool == "autopep8":
                    cmd = ["autopep8", "-a", "-a", "--in-place", tmp]
                else:
                    messagebox.showinfo("External Formatter", f"Unsupported: {tool}")
                    return
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                if proc.returncode != 0:
                    messagebox.showerror(
                        "Formatter Error",
                        proc.stderr or proc.stdout or f"{tool} failed",
                    )
                    return
                with open(tmp, "r", encoding="utf-8") as f:
                    new_code = f.read()
                self.display_code(new_code)
                self.indentation_applied = True
                self.update_save_state()
                self.set_status(f"Applied external formatter: {tool}")
            except FileNotFoundError:
                messagebox.showwarning("Not Found", f"{tool} not found on PATH.")

    def _choose_formatter(self) -> Optional[str]:
        tools = [t for t in ("ruff", "black", "autopep8") if self._is_on_path(t)]
        if not tools:
            messagebox.showinfo(
                "External Formatters",
                "No supported formatter found on PATH (ruff, black, autopep8).",
            )
            return None
        top = tk.Toplevel(self.root)
        top.title("Choose Formatter")
        var = tk.StringVar(value=tools[0])
        for t in tools:
            tk.Radiobutton(top, text=t, variable=var, value=t).pack(anchor="w")
        tk.Button(top, text="OK", command=top.destroy).pack(pady=6)
        top.transient(self.root)
        top.grab_set()
        self.root.wait_window(top)
        return var.get()

    @staticmethod
    def _is_on_path(exe: str) -> bool:
        for p in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(p, exe)
            exts = (".exe", ".bat", ".cmd", "") if os.name == "nt" else ("",)
            for e in exts:
                if os.path.isfile(candidate + e) and os.access(candidate + e, os.X_OK):
                    return True
        return False

    # --------------- AST helpers ---------------
    def _ast_valid(self, code: str) -> Tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Line {e.lineno}, col {e.offset}: {e.msg}"

    # --------------- Misc helpers ---------------
    @staticmethod
    def _pos_to_idx(text: str, pos: Tuple[int, int]) -> int:
        line_no, col = pos
        lines = text.splitlines(True)
        if line_no - 1 < 0 or line_no - 1 >= len(lines):
            return len(text)
        return sum(len(lines[i]) for i in range(line_no - 1)) + col

    def update_save_state(self):
        state = "normal" if self.indentation_applied else "disabled"
        self.file_menu.entryconfig("Save", state=state)

    def show_about(self):
        about_text = (
            f"Ef Reindenter / Python Formatter — v{self.version}\n\n"
            "• PEP 8 formatting, wrapping, import organization\n"
            "• Heuristic block repair + reindent\n"
            "• Refactors: remove unused imports, simplify boolean returns,\n"
            "  convert simple %/.format to f-strings\n"
            "• Structure tree navigator\n"
            "• Project settings (pyproject.toml) + Settings dialog\n"
            "• External formatters (ruff/black/autopep8)\n\n"
            "AST-assisted, token-aware, Ef-brand tool.\n"
        )
        messagebox.showinfo("About", about_text)

    def set_status(self, msg: str):
        self.status_label.config(text=msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = PythonReindenterApp(root)
    root.mainloop()
