#!/usr/bin/env python3
"""
Dead Code Explorer
A focused tool for finding genuinely dead Python methods with confidence scoring.
"""
import sys
import ast
import csv
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QLineEdit, QLabel, QPushButton, QFileDialog,
    QMessageBox, QProgressBar, QComboBox, QMenu,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QColor, QAction, QKeySequence, QShortcut, QFont, QSyntaxHighlighter,
    QTextCharFormat,
)

CONFIG_FILE = Path.home() / ".code_explorer_config.json"


def _load_config() -> dict:
    """Load the full config dict from disk."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_config(cfg: dict):
    """Persist the full config dict to disk."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


def load_last_folder() -> str:
    return _load_config().get("last_folder", "src")


def save_last_folder(folder: str):
    cfg = _load_config()
    cfg["last_folder"] = folder
    _save_config(cfg)


def load_dismissed() -> Set[str]:
    """Load the set of dismissed node IDs from config."""
    return set(_load_config().get("dismissed", []))


def save_dismissed(dismissed: Set[str]):
    """Save the set of dismissed node IDs to config."""
    cfg = _load_config()
    cfg["dismissed"] = sorted(dismissed)
    _save_config(cfg)


# --- CONFIDENCE LEVELS ---
# Higher = more likely ACTUALLY dead. Lower = more likely false positive.
CONF_DEAD = 100       # Strong evidence of dead code
CONF_HIGH = 85        # Probably dead
CONF_MEDIUM = 50      # Uncertain — needs human review
CONF_LOW = 25         # Probably a false positive
CONF_FALSE_POS = 0    # Almost certainly a false positive


# --- THEME ---
STYLESHEET = (  # noqa: E501
    "QMainWindow { background-color: #000000; color: #DDDDDD; }"
    "QWidget { background-color: #111111; color: #DDDDDD;"
    " font-family: 'Segoe UI', sans-serif; font-size: 10pt; }"
    "QSplitter::handle { background-color: #222222; }"
    "QHeaderView::section { background-color: #1A1A1A; color: #AA9977;"
    " border: 1px solid #333333; padding: 4px; font-weight: bold; }"
    "QLabel { color: #DDDDDD; background: transparent; }"
    "QLineEdit { background-color: #0A0A0A; border: 1px solid #333333;"
    " color: #FFC66D; padding: 4px; border-radius: 4px;"
    " font-family: 'Consolas', monospace; }"
    "QLineEdit:focus { border: 1px solid #FFC66D; }"
    "QPushButton { background-color: #1A1A1A; border: 1px solid #FFC66D;"
    " color: #FFC66D; padding: 6px 12px; border-radius: 4px;"
    " font-weight: bold; }"
    "QPushButton:hover { background-color: #2A2A2A; color: #FFFFFF; }"
    "QPushButton:pressed { background-color: #000000; border-color: #AA8844; }"
    "QPushButton:disabled { border-color: #444444; color: #666666; }"
    "QToolBar { background-color: #111111;"
    " border-bottom: 2px solid #333333; spacing: 10px; padding: 5px; }"
    "QToolBar QToolButton { color: #DDDDDD; background: transparent;"
    " border: 1px solid transparent; border-radius: 4px; padding: 4px; }"
    "QToolBar QToolButton:hover {"
    " border: 1px solid #666666; background-color: #222222; }"
    "QComboBox { background-color: #0A0A0A; border: 1px solid #333333;"
    " color: #FFC66D; padding: 4px; border-radius: 4px; }"
    "QComboBox:hover { border: 1px solid #666666; }"
    "QComboBox::drop-down { border: none; }"
    "QComboBox QAbstractItemView { background-color: #1A1A1A;"
    " color: #DDDDDD; selection-background-color: #333333; }"
)


@dataclass
class MethodNode:
    """Represents a method/function in the codebase."""
    name: str
    file_path: str
    line_number: int
    line_count: int = 1
    is_method: bool = False
    class_name: Optional[str] = None
    base_classes: List[str] = field(default_factory=list)
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)
    is_property: bool = False
    is_setter: bool = False
    is_deleter: bool = False
    is_override: bool = False
    is_abstract: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_test: bool = False
    is_dunder: bool = False
    is_private: bool = False
    is_init: bool = False
    docstring: str = ""
    decorators: Set[str] = field(default_factory=set)
    # Detected dynamic usage
    referenced_as_string: bool = False
    passed_as_callback: bool = False
    connected_to_signal: bool = False
    is_qt_property: bool = False
    is_dataclass_special: bool = False

    @property
    def full_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    @property
    def rel_path(self) -> str:
        """Relative path — set after parsing."""
        return self._rel_path if hasattr(self, '_rel_path') else self.file_path

    @rel_path.setter
    def rel_path(self, value):
        self._rel_path = value

    def compute_confidence(self) -> int:
        """
        Compute confidence that this method is ACTUALLY dead code.
        100 = almost certainly dead. 0 = almost certainly a false positive.
        """
        # If it has callers, it's not dead at all
        if self.called_by:
            return 0

        # --- Strong false-positive indicators (confidence drops a lot) ---

        # Dunder methods are called by Python itself
        if self.is_dunder:
            return CONF_FALSE_POS

        # Abstract methods are implemented by subclasses and called via interface
        if self.is_abstract:
            return CONF_FALSE_POS

        # __init__ is always called on instantiation
        if self.is_init:
            return CONF_FALSE_POS

        # Test methods are invoked by pytest
        if self.is_test:
            return CONF_FALSE_POS

        # Property setters/deleters are called by descriptor protocol
        if self.is_setter or self.is_deleter:
            return CONF_FALSE_POS

        # Qt properties invoked by animation system
        if self.is_qt_property:
            return CONF_FALSE_POS

        # Connected to a Qt signal
        if self.connected_to_signal:
            return CONF_FALSE_POS

        # Dataclass special methods (__post_init__, etc.)
        if self.is_dataclass_special:
            return CONF_FALSE_POS

        # Referenced as a string (getattr, config-driven dispatch)
        if self.referenced_as_string:
            return CONF_LOW

        # Passed as callback argument
        if self.passed_as_callback:
            return CONF_LOW

        # Known framework callback (Qt event handlers)
        if self.name in ASTParser.FRAMEWORK_CALLBACKS:
            return CONF_LOW

        # --- Medium indicators ---

        # Property getter — could be used in templates or f-strings
        if self.is_property:
            return CONF_MEDIUM

        # Override of a parent class method (non-Qt)
        if self.is_override:
            return CONF_MEDIUM

        # Public API of a class (not prefixed with _)
        if self.is_method and not self.is_private:
            # Classmethods/staticmethods that are public
            if self.is_classmethod or self.is_staticmethod:
                return CONF_MEDIUM
            # Check docstring for debugging/internal keywords
            if hasattr(self, 'docstring') and self.docstring:
                doc_lower = self.docstring.lower()
                debug_keywords = ['debug', 'internal', 'use with caution', 'for testing',
                                  'testing only', 'deprecated', 'experimental']
                if any(kw in doc_lower for kw in debug_keywords):
                    return CONF_LOW
            return CONF_HIGH

        # Private methods with no callers — likely dead
        if self.is_private and not self.name.startswith('__'):
            return CONF_DEAD

        # Module-level functions with no callers
        if not self.is_method:
            if self.is_private:
                return CONF_DEAD
            return CONF_HIGH

        return CONF_HIGH

    def get_reason(self) -> str:
        """Single-line explanation of why it's flagged or why it might be a false positive."""
        conf = self.compute_confidence()

        if self.called_by:
            return f"Has {len(self.called_by)} caller(s)"

        if conf == CONF_FALSE_POS:
            reasons = []
            if self.is_dunder:
                reasons.append("dunder method")
            if self.is_abstract:
                reasons.append("abstract method")
            if self.is_init:
                reasons.append("constructor")
            if self.is_test:
                reasons.append("test method")
            if self.is_setter or self.is_deleter:
                reasons.append("property setter/deleter")
            if self.is_qt_property:
                reasons.append("Qt property (animation)")
            if self.connected_to_signal:
                reasons.append("signal slot")
            if self.is_dataclass_special:
                reasons.append("dataclass method")
            return "FP: " + ", ".join(reasons) if reasons else "FP: whitelisted pattern"

        if conf <= CONF_LOW:
            if self.referenced_as_string:
                return "String-referenced (getattr/config)"
            if self.passed_as_callback:
                return "Passed as callback argument"
            if self.name in ASTParser.FRAMEWORK_CALLBACKS:
                return f"Framework callback ({self.name})"

        if conf <= CONF_MEDIUM:
            if self.is_property:
                return "Property getter — check templates/f-strings"
            if self.is_override:
                return "Overrides parent class method"
            if self.is_classmethod or self.is_staticmethod:
                return "Public class/static method — check cross-module usage"

        if self.is_private:
            return "Private, no callers found — likely dead"

        if self.is_method:
            return "Public method, no callers found"

        return "Module-level function, no callers found"


class ASTParser:
    """Parses Python code and extracts method definitions, calls, and dynamic references."""

    # Qt widget/graphics/model callbacks invoked by the framework
    FRAMEWORK_CALLBACKS = {
        # Qt widget events
        'wheelEvent', 'mousePressEvent', 'mouseReleaseEvent', 'mouseMoveEvent',
        'mouseDoubleClickEvent', 'keyPressEvent', 'keyReleaseEvent',
        'paintEvent', 'resizeEvent', 'showEvent', 'hideEvent', 'closeEvent',
        'focusInEvent', 'focusOutEvent', 'enterEvent', 'leaveEvent',
        'dragEnterEvent', 'dragMoveEvent', 'dragLeaveEvent', 'dropEvent',
        'contextMenuEvent', 'timerEvent', 'changeEvent',
        'eventFilter', 'event', 'nativeEvent', 'startDrag',
        # Qt layout
        'sizeHint', 'minimumSizeHint', 'heightForWidth', 'hasHeightForWidth', 'expandingDirections',
        'setGeometry', 'count', 'itemAt', 'takeAt',
        # Qt graphics items
        'paint', 'boundingRect', 'shape',
        # QAbstractItemModel / QAbstractTableModel / QSortFilterProxyModel
        'rowCount', 'columnCount', 'data', 'headerData', 'flags',
        'setData', 'insertRows', 'removeRows', 'index', 'parent',
        'filterAcceptsRow', 'filterAcceptsColumn', 'lessThan',
        'mimeTypes', 'mimeData', 'dropMimeData', 'supportedDropActions',
        # QStyledItemDelegate
        'createEditor', 'setEditorData', 'setModelData', 'updateEditorGeometry',
        'initStyleOption',
        # QWidget overrides
        'nextCheckState', 'hitButton',
        # QThread
        'run',
        # QValidator
        'validate', 'fixup',
        # Context manager
        '__enter__', '__exit__',
        # Iterator
        '__iter__', '__next__',
    }

    # Dataclass special methods
    DATACLASS_METHODS = {'__post_init__', '__init_subclass__'}

    def __init__(self, src_dir: str):
        self.src_dir = Path(src_dir)
        self.nodes: Dict[str, MethodNode] = {}
        # Track class inheritance: class_name -> [base_class_names]
        self.class_bases: Dict[str, List[str]] = {}
        # Track all method names defined per class for override detection
        self.class_methods: Dict[str, Set[str]] = defaultdict(set)
        # Track string literals that look like method names
        self.string_refs: Set[str] = set()
        # Track names passed as function arguments (callback pattern)
        self.callback_refs: Set[str] = set()

    def parse_all(self):
        """Parse all Python files in the source directory."""
        py_files = [
            f for f in self.src_dir.rglob("*.py")
            if "test" not in str(f).lower()
            and "__pycache__" not in str(f)
        ]

        # Pass 1: Collect class hierarchies, definitions, and string refs
        for py_file in py_files:
            self._parse_file(py_file)

        # Pass 2: Find Qt signal connections
        for py_file in py_files:
            self._find_signal_connections(py_file)

        # Pass 3: Find string references (getattr, config dicts, pyqtProperty)
        for py_file in py_files:
            self._find_string_references(py_file)

        # Pass 4: Find callback-passing patterns
        for py_file in py_files:
            self._find_callback_patterns(py_file)

        # Resolve calls and mark overrides
        self._resolve_calls()
        self._detect_overrides()
        self._apply_string_refs()
        self._apply_callback_refs()

        # Compute relative paths
        for node in self.nodes.values():
            try:
                node.rel_path = str(Path(node.file_path).relative_to(self.src_dir))
            except ValueError:
                node.rel_path = node.file_path

    def _parse_file(self, file_path: Path):
        """Parse a single Python file for definitions and calls."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return

        # Collect class info first
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)
                self.class_bases[node.name] = bases

        # Collect functions
        class FunctionCollector(ast.NodeVisitor):
            def __init__(self, parser, fp):
                self.parser = parser
                self.file_path = fp
                self.current_class = None
                self.current_class_node = None

            def visit_ClassDef(self, node):
                prev_class = self.current_class
                self.current_class = node.name
                self.current_class_node = node
                self.generic_visit(node)
                self.current_class = prev_class
                self.current_class_node = None

            def visit_FunctionDef(self, node):
                self.parser._process_function(
                    node, self.file_path, self.current_class
                )
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                self.parser._process_function(
                    node, self.file_path, self.current_class
                )
                self.generic_visit(node)

        visitor = FunctionCollector(self, file_path)
        visitor.visit(tree)

    def _process_function(self, node: ast.FunctionDef, file_path: Path,
                          class_name: Optional[str] = None):
        """Extract method info and calls from a function."""
        if class_name:
            node_id = f"{file_path}:{class_name}.{node.name}"
        else:
            node_id = f"{file_path}:{node.name}"

        # Extract decorator info
        decorator_names = set()
        is_property = False
        is_setter = False
        is_deleter = False
        is_classmethod = False
        is_staticmethod = False
        is_abstract = False
        is_qt_property = False

        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorator_names.add(dec.id)
                if dec.id == 'property':
                    is_property = True
                elif dec.id == 'classmethod':
                    is_classmethod = True
                elif dec.id == 'staticmethod':
                    is_staticmethod = True
                elif dec.id == 'abstractmethod':
                    is_abstract = True
            elif isinstance(dec, ast.Attribute):
                decorator_names.add(dec.attr)
                if dec.attr == 'setter':
                    is_setter = True
                elif dec.attr == 'deleter':
                    is_deleter = True
                elif dec.attr in ('abstractmethod',):
                    is_abstract = True
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorator_names.add(dec.func.id)
                    if dec.func.id == 'pyqtProperty':
                        is_qt_property = True
                elif isinstance(dec.func, ast.Attribute):
                    decorator_names.add(dec.func.attr)

        line_count = 1
        if hasattr(node, 'end_lineno') and node.end_lineno:
            line_count = node.end_lineno - node.lineno + 1

        is_dunder = node.name.startswith('__') and node.name.endswith('__')
        is_private = node.name.startswith('_') and not is_dunder

        # Extract docstring
        docstring = ""
        if node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstring = str(first.value.value) if first.value.value else ""
            elif isinstance(first, ast.Constant) and isinstance(first.value, str):
                docstring = first.value

        method_node = MethodNode(
            name=node.name,
            file_path=str(file_path),
            line_number=node.lineno,
            line_count=line_count,
            is_method=class_name is not None,
            class_name=class_name,
            base_classes=self.class_bases.get(class_name or "", []),
            is_property=is_property,
            is_setter=is_setter,
            is_deleter=is_deleter,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_abstract=is_abstract,
            is_qt_property=is_qt_property,
            is_dunder=is_dunder,
            is_private=is_private,
            is_init=node.name == '__init__',
            is_test=node.name.startswith('test_'),
            is_dataclass_special=node.name in self.DATACLASS_METHODS,
            docstring=docstring,
            decorators=decorator_names,
        )

        # Track class methods for override detection
        if class_name:
            self.class_methods[class_name].add(node.name)

        # Find calls within this method
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    method_node.calls.add(child.func.attr)
                elif isinstance(child.func, ast.Name):
                    method_node.calls.add(child.func.id)
            # Property access (non-call attribute read)
            elif isinstance(child, ast.Attribute):
                if not isinstance(child.ctx, ast.Store):
                    method_node.calls.add(child.attr)

        self.nodes[node_id] = method_node

    def _find_signal_connections(self, file_path: Path):
        """Find signal.connect(callback) patterns."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Attribute) and node.func.attr == 'connect'):
                continue
            if not node.args:
                continue

            callback = node.args[0]
            method_name = None
            if isinstance(callback, ast.Attribute):
                method_name = callback.attr
            elif isinstance(callback, ast.Name):
                method_name = callback.id

            if method_name:
                for method_node in self.nodes.values():
                    if method_node.name == method_name:
                        method_node.connected_to_signal = True
                        method_node.called_by.add(f"signal:{file_path.stem}")

    def _find_string_references(self, file_path: Path):
        """Find method names referenced as strings (getattr, configs, pyqtProperty, QPropertyAnimation)."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return

        for node in ast.walk(tree):
            # getattr(obj, "method_name") or getattr(obj, "method_name", default)
            if isinstance(node, ast.Call):
                func = node.func
                func_name = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr

                if func_name == 'getattr' and len(node.args) >= 2:
                    str_arg = node.args[1]
                    if isinstance(str_arg, ast.Constant) and isinstance(str_arg.value, str):
                        self.string_refs.add(str_arg.value)

                # QPropertyAnimation(self, b"propertyName")
                if func_name == 'QPropertyAnimation' and len(node.args) >= 2:
                    prop_arg = node.args[1]
                    if isinstance(prop_arg, ast.Constant) and isinstance(prop_arg.value, bytes):
                        self.string_refs.add(prop_arg.value.decode('utf-8', errors='ignore'))

            # String constants in assignments that look like method/attribute names
            # e.g., service_attr="contributor_service", search_fn="search"
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value
                # Only track names that look like Python identifiers
                if re.match(r'^[a-z_][a-z0-9_]*$', val) and len(val) > 2:
                    self.string_refs.add(val)

            # Bytes constants (b"propertyName" in QPropertyAnimation)
            if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
                try:
                    val = node.value.decode('utf-8')
                    if re.match(r'^[a-z_][a-z0-9_]*$', val) and len(val) > 2:
                        self.string_refs.add(val)
                except UnicodeDecodeError:
                    pass

    def _find_callback_patterns(self, file_path: Path):
        """Find methods passed as callback arguments (fn=self.method)."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Check keyword arguments: fn=self.method, callback=some_func
            for kw in node.keywords:
                if isinstance(kw.value, ast.Attribute):
                    self.callback_refs.add(kw.value.attr)
                elif isinstance(kw.value, ast.Name):
                    self.callback_refs.add(kw.value.id)

            # Check positional arguments that are attributes (self.method)
            # but only for calls that look like they accept callbacks
            # (any keyword arg ending in _fn, _callback, _handler, _func)
            callback_kw_suffixes = ('_fn', '_callback', '_handler', '_func')
            has_callback_kw = any(
                kw.arg and any(kw.arg.endswith(s) for s in callback_kw_suffixes)
                for kw in node.keywords
            )
            if has_callback_kw:
                for arg in node.args:
                    if isinstance(arg, ast.Attribute):
                        self.callback_refs.add(arg.attr)
                    elif isinstance(arg, ast.Name):
                        self.callback_refs.add(arg.id)

    def _resolve_calls(self):
        """Resolve method calls to their definitions."""
        name_to_nodes: Dict[str, List[MethodNode]] = defaultdict(list)
        for node in self.nodes.values():
            name_to_nodes[node.name].append(node)
            if node.class_name:
                name_to_nodes[node.full_name].append(node)

        # Pre-compute which method names are unique (only one definition).
        # When a name is unique, any call to it is unambiguous — no heuristic
        # filtering needed.
        unique_names: Set[str] = {
            name for name, nodes in name_to_nodes.items() if len(nodes) == 1
        }

        for caller in self.nodes.values():
            for call_name in list(caller.calls):
                targets = name_to_nodes.get(call_name, [])
                for target in targets:
                    if target is not caller:
                        # Unique name → always match (no ambiguity)
                        if call_name in unique_names:
                            target.called_by.add(caller.full_name)
                        elif self._is_likely_match(caller, target):
                            target.called_by.add(caller.full_name)

    def _is_likely_match(self, caller: MethodNode, callee: MethodNode) -> bool:
        """Heuristic to determine if a call likely refers to this method.

        Only used when multiple definitions share the same name, so we need
        to guess which one a given call-site is targeting.
        """
        # Same file = likely match
        if caller.file_path == callee.file_path:
            return True

        # Same package (directory) = likely match
        caller_dir = str(Path(caller.file_path).parent)
        callee_dir = str(Path(callee.file_path).parent)
        if caller_dir == callee_dir:
            return True

        # Target is a service or repository — these are the data layer and are
        # designed to be called from anywhere, so treat as likely match
        callee_file = Path(callee.file_path).stem.lower()
        if callee_file.endswith('_service') or callee_file.endswith('_repository'):
            return True

        caller_file = Path(caller.file_path).stem.lower()
        callee_file = Path(callee.file_path).stem.lower()

        # Direct relationship patterns
        for suffix in ('_service', '_repository', '_dialog', '_widget',
                        '_worker', '_adapter', '_manager', '_handler',
                        '_model', '_view', '_controller', '_helper'):
            if caller_file.replace(suffix, '') in callee_file:
                return True
            if callee_file.replace(suffix, '') in caller_file:
                return True

        # Adapter → Service/Repository relationship
        # (e.g., ArtistAliasAdapter uses ContributorService)
        if '_adapter' in caller_file and ('_service' in callee_file or '_repository' in callee_file):
            # Check if caller class name relates to callee module name
            # e.g., ArtistAliasAdapter → contributor_service (Artist ↔ Contributor)
            if caller.class_name and callee_file.startswith(caller.class_name.lower().replace('adapter', '')):
                return True

        # Shared meaningful words
        noise = {'', 'a', 'an', 'the', 'is', 'to', 'in', 'of', 'base',
                 'abstract', 'generic', 'utils', 'test', 'tests'}
        caller_words = set(caller_file.split('_')) - noise
        callee_words = set(callee_file.split('_')) - noise
        if caller_words & callee_words:
            return True

        # If the callee's class name appears in the caller's file (imported),
        # it's very likely a real call
        if callee.class_name:
            try:
                caller_content = Path(caller.file_path).read_text(encoding='utf-8')
                if callee.class_name in caller_content:
                    return True
            except OSError:
                pass

        return False

    def _detect_overrides(self):
        """Detect methods that override a parent class method."""
        all_class_methods = {}
        for node in self.nodes.values():
            if node.class_name:
                key = (node.class_name, node.name)
                all_class_methods[key] = node

        for node in self.nodes.values():
            if not node.is_method or not node.base_classes:
                continue

            for base in node.base_classes:
                if (base, node.name) in all_class_methods:
                    node.is_override = True
                    break

                # Also check framework callbacks as overrides
                if node.name in self.FRAMEWORK_CALLBACKS:
                    node.is_override = True
                    break

    def _apply_string_refs(self):
        """Mark methods that are referenced as strings."""
        for node in self.nodes.values():
            if node.name in self.string_refs:
                node.referenced_as_string = True

    def _apply_callback_refs(self):
        """Mark methods that are passed as callbacks."""
        for node in self.nodes.values():
            if node.name in self.callback_refs:
                node.passed_as_callback = True


class PythonHighlighter(QSyntaxHighlighter):
    """Minimal Python syntax highlighter for the source preview."""

    KEYWORDS = {
        'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while',
        'try', 'except', 'finally', 'with', 'as', 'import', 'from',
        'raise', 'pass', 'break', 'continue', 'yield', 'lambda',
        'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False',
        'self', 'cls', 'async', 'await', 'assert', 'global', 'nonlocal',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._formats: List[tuple] = []

        # Keywords
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#CC7832"))
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        kw_pattern = r'\b(' + '|'.join(self.KEYWORDS) + r')\b'
        self._formats.append((re.compile(kw_pattern), kw_fmt))

        # Strings (single and double, triple-quoted handled simply)
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#6A8759"))
        self._formats.append((re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL), str_fmt))
        self._formats.append((re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), str_fmt))
        self._formats.append((re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), str_fmt))

        # Decorators
        dec_fmt = QTextCharFormat()
        dec_fmt.setForeground(QColor("#BBB529"))
        self._formats.append((re.compile(r'@\w[\w.]*'), dec_fmt))

        # Comments
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#808080"))
        comment_fmt.setFontItalic(True)
        self._formats.append((re.compile(r'#[^\n]*'), comment_fmt))

        # Numbers
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#6897BB"))
        self._formats.append((re.compile(r'\b\d+\.?\d*\b'), num_fmt))

        # Function/method names after 'def'
        func_fmt = QTextCharFormat()
        func_fmt.setForeground(QColor("#FFC66D"))
        self._formats.append((re.compile(r'(?<=\bdef\s)\w+'), func_fmt))

    def highlightBlock(self, text: str | None):  # type: ignore[override]
        if text is None:
            return
        for pattern, fmt in self._formats:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class DeadCodeWindow(QMainWindow):
    """Main application window focused on dead code discovery."""

    def __init__(self, src_dir: Optional[str] = None):
        super().__init__()
        self.src_dir = src_dir or load_last_folder()
        self.parser = None
        self.all_filtered: List[MethodNode] = []
        self.selected_node: Optional[MethodNode] = None
        self._sort_column = 5     # Default sort: confidence descending
        self._sort_order = Qt.SortOrder.DescendingOrder
        self._source_cache: Dict[str, List[str]] = {}

        self.setWindowTitle("Dead Code Explorer")
        self.setGeometry(100, 100, 1500, 950)
        self.statusBar()

        self._create_ui()
        self._create_toolbar()
        self._create_shortcuts()

        # Load persisted dismissed items
        self.dismissed_nodes: Set[str] = load_dismissed()

        self._parse_codebase()

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _create_shortcuts(self):
        """Set up keyboard shortcuts."""
        go_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.dead_list)
        go_shortcut.activated.connect(self._goto_source)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.activated.connect(self._on_escape)

        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        find_shortcut.activated.connect(lambda: self.search_box.setFocus())

        del_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.dead_list)
        del_shortcut.activated.connect(self._dismiss_selected)

        # Ctrl+A -> select all in table
        sel_all = QShortcut(QKeySequence("Ctrl+A"), self.dead_list)
        sel_all.activated.connect(self.dead_list.selectAll)

    def _on_escape(self):
        if self.search_box.text():
            self.search_box.clear()
        else:
            self.dead_list.clearSelection()
            self.selected_node = None
            self.details_label.setText("Select a method to view details")
            self.flags_label.setText("")
            self.source_preview.clear()
            self.goto_button.setEnabled(False)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _create_ui(self):
        """Create the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Stats bar ---
        stats_container = QWidget()
        stats_container.setStyleSheet(
            "background-color: #1A1A1A; border-bottom: 1px solid #333333;"
        )
        stats_container.setFixedHeight(36)
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(10, 4, 10, 4)

        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet("color: #FFC66D; font-weight: bold;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()

        self.dead_count_label = QLabel("")
        self.dead_count_label.setStyleSheet("color: #FF4444; font-weight: bold;")
        stats_layout.addWidget(self.dead_count_label)

        main_layout.addWidget(stats_container)

        # --- Main splitter: filters | (table + preview) | details ---
        outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(outer_splitter)

        # ---- Left: Filter panel ----
        filter_panel = self._build_filter_panel()
        outer_splitter.addWidget(filter_panel)

        # ---- Center: Table + Source preview (vertical split) ----
        center_splitter = QSplitter(Qt.Orientation.Vertical)

        self.dead_list = self._build_table()
        center_splitter.addWidget(self.dead_list)

        self.source_preview = self._build_source_preview()
        center_splitter.addWidget(self.source_preview)
        center_splitter.setSizes([550, 300])

        outer_splitter.addWidget(center_splitter)

        # ---- Right: Details panel ----
        details_panel = self._build_details_panel()
        outer_splitter.addWidget(details_panel)

        outer_splitter.setSizes([200, 850, 320])

    def _build_filter_panel(self) -> QWidget:
        """Build the left-hand filter panel."""
        panel = QWidget()
        panel.setMaximumWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("<b>Filters</b>")
        layout.addWidget(title)

        layout.addWidget(QLabel("Module:"))
        self.module_combo = QComboBox()
        self.module_combo.addItem("All Modules")
        self.module_combo.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.module_combo)

        layout.addWidget(QLabel("Confidence:"))
        self.conf_combo = QComboBox()
        self.conf_combo.addItems([
            "High + Dead Only (>= 85)",
            "Medium + High (>= 50)",
            "All No-Callers",
            "False Positives Only (0)",
        ])
        self.conf_combo.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.conf_combo)

        layout.addWidget(QLabel("Kind:"))
        self.kind_combo = QComboBox()
        self.kind_combo.addItems([
            "All",
            "Private methods (_)",
            "Public methods",
            "Module functions",
            "Properties",
            "Classmethods/Staticmethods",
        ])
        self.kind_combo.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.kind_combo)

        layout.addSpacing(10)

        self.hide_dismissed = QPushButton("Hide Dismissed")
        self.hide_dismissed.setCheckable(True)
        self.hide_dismissed.setChecked(True)
        self.hide_dismissed.clicked.connect(self._apply_filters)
        layout.addWidget(self.hide_dismissed)

        layout.addSpacing(6)

        self.clear_dismissed_btn = QPushButton("Clear All Dismissed")
        self.clear_dismissed_btn.setStyleSheet(
            "QPushButton { border-color: #666666; color: #888888; }"
            "QPushButton:hover { color: #FFC66D; border-color: #FFC66D; }"
        )
        self.clear_dismissed_btn.clicked.connect(self._clear_all_dismissed)
        layout.addWidget(self.clear_dismissed_btn)

        layout.addSpacing(14)

        # Filter count summary
        self.filter_summary = QLabel("")
        self.filter_summary.setWordWrap(True)
        self.filter_summary.setStyleSheet("color: #777777; font-size: 9pt;")
        layout.addWidget(self.filter_summary)

        layout.addStretch()

        # Dismissed tracking (will be replaced by loaded set in __init__)
        self.dismissed_nodes: Set[str] = set()

        return panel

    def _build_table(self) -> QTableWidget:
        """Build the dead code table widget."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Method", "File", "Line", "Lines", "Kind", "Conf", "Reason"
        ])

        header: QHeaderView = table.horizontalHeader()  # type: ignore[assignment]
        header.setSectionsMovable(False)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 260)
        table.setColumnWidth(1, 230)

        # Multi-select support
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        table.itemSelectionChanged.connect(self._on_list_selection_changed)
        table.itemDoubleClicked.connect(lambda _: self._goto_source())

        # Right-click context menu
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        table.setStyleSheet(
            "QTableWidget { background-color: #0A0A0A; color: #CCCCCC;"
            " gridline-color: #222222;"
            " alternate-background-color: #0F0F0F; }"
            "QTableWidget::item:selected {"
            " background-color: #333333; color: #FFC66D; }"
            "QHeaderView::section { background-color: #1A1A1A;"
            " color: #AA9977; border: 1px solid #333333; padding: 4px; }"
        )
        table.setAlternatingRowColors(True)

        return table

    def _build_source_preview(self) -> QTextEdit:
        """Build the source code preview widget."""
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setFont(QFont("Consolas", 9))
        preview.setStyleSheet(
            "QTextEdit { background-color: #0A0A0A; color: #BBBBBB;"
            " border: none; border-top: 1px solid #333333;"
            " selection-background-color: #3A3A3A; }"
        )
        preview.setPlaceholderText("Select a method to preview its source code")
        # Attach syntax highlighter
        self._highlighter = PythonHighlighter(preview.document())
        return preview

    def _build_details_panel(self) -> QWidget:
        """Build the right-hand details panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(QLabel("<b>Details</b>"))

        self.details_label = QLabel("Select a method to view details")
        self.details_label.setWordWrap(True)
        self.details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.details_label.setStyleSheet(
            "QLabel { font-family: 'Consolas', monospace; font-size: 9pt; }"
        )
        layout.addWidget(self.details_label)

        # Action buttons
        btn_row = QHBoxLayout()
        self.goto_button = QPushButton("Go to Source")
        self.goto_button.setEnabled(False)
        self.goto_button.clicked.connect(self._goto_source)
        btn_row.addWidget(self.goto_button)

        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.setEnabled(False)
        self.dismiss_button.clicked.connect(self._dismiss_selected)
        btn_row.addWidget(self.dismiss_button)
        layout.addLayout(btn_row)

        layout.addSpacing(10)

        layout.addWidget(QLabel("<b>Analysis</b>"))
        self.flags_label = QLabel("")
        self.flags_label.setWordWrap(True)
        self.flags_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.flags_label)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        open_action = QAction("Open Folder", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_folder)
        toolbar.addAction(open_action)

        self.folder_label = QLabel(f"  {Path(self.src_dir).name}")
        self.folder_label.setStyleSheet(
            "QLabel { padding: 0 10px; color: #888888; }"
        )
        toolbar.addWidget(self.folder_label)

        toolbar.addSeparator()

        refresh_action = QAction("Refresh (F5)", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._parse_codebase)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search methods... (Ctrl+F)")
        self.search_box.setMaximumWidth(250)
        self.search_box.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_box)

        toolbar.addSeparator()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)

        export_action = QAction("Export CSV", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_csv)
        toolbar.addAction(export_action)

        clipboard_action = QAction("Copy List", self)
        clipboard_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        clipboard_action.triggered.connect(self._export_clipboard)
        toolbar.addAction(clipboard_action)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos):
        """Show right-click context menu on the table."""
        rows = self._selected_rows()
        if not rows:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #1A1A1A; color: #DDDDDD;"
            " border: 1px solid #333333; }"
            "QMenu::item:selected { background-color: #333333;"
            " color: #FFC66D; }"
        )

        count = len(rows)

        go_action = QAction("Go to Source (Enter)", menu)
        go_action.setEnabled(count == 1)
        go_action.triggered.connect(self._goto_source)
        menu.addAction(go_action)

        menu.addSeparator()

        dismiss_action = QAction(
            f"Dismiss ({count} item{'s' if count > 1 else ''})", menu
        )
        dismiss_action.triggered.connect(self._dismiss_selected)
        menu.addAction(dismiss_action)

        undismiss_action = QAction("Un-dismiss Selected", menu)
        undismiss_action.triggered.connect(self._undismiss_selected)
        menu.addAction(undismiss_action)

        menu.addSeparator()

        copy_name_action = QAction("Copy Method Name(s)", menu)
        copy_name_action.triggered.connect(self._copy_method_names)
        menu.addAction(copy_name_action)

        copy_path_action = QAction("Copy File:Line", menu)
        copy_path_action.triggered.connect(self._copy_file_lines)
        menu.addAction(copy_path_action)

        viewport = self.dead_list.viewport()
        if viewport:
            menu.exec(viewport.mapToGlobal(pos))

    def _selected_rows(self) -> List[int]:
        """Return sorted list of unique selected row indices."""
        indices = set()
        for item in self.dead_list.selectedItems():
            indices.add(item.row())
        return sorted(indices)

    def _selected_nodes(self) -> List[MethodNode]:
        """Return MethodNode objects for all selected rows."""
        nodes = []
        for row in self._selected_rows():
            item = self.dead_list.item(row, 0)
            if item:
                node = item.data(Qt.ItemDataRole.UserRole)
                if node:
                    nodes.append(node)
        return nodes

    def _copy_method_names(self):
        """Copy selected method full names to clipboard."""
        names = [n.full_name for n in self._selected_nodes()]
        if names:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText("\n".join(names))
            self.statusBar().showMessage(  # type: ignore[union-attr]
                f"Copied {len(names)} method name(s)", 3000
            )

    def _copy_file_lines(self):
        """Copy file:line references for selected items."""
        refs = [
            f"{n.rel_path}:{n.line_number}" for n in self._selected_nodes()
        ]
        if refs:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText("\n".join(refs))
            self.statusBar().showMessage(  # type: ignore[union-attr]
                f"Copied {len(refs)} reference(s)", 3000
            )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Directory", self.src_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.src_dir = folder
            save_last_folder(folder)
            self.folder_label.setText(f"  {Path(folder).name}")
            self._source_cache.clear()
            self._parse_codebase()

    def _parse_codebase(self):
        self.setWindowTitle("Dead Code Explorer - Parsing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        QApplication.processEvents()

        self.parser = ASTParser(self.src_dir)
        self.parser.parse_all()
        self._source_cache.clear()

        self.progress_bar.setRange(0, 1)
        self.progress_bar.setVisible(False)

        self._populate_module_filter()
        self._apply_filters()

        total = len(self.parser.nodes)
        no_callers = sum(
            1 for n in self.parser.nodes.values() if not n.called_by
        )
        high_conf = sum(
            1 for n in self.parser.nodes.values()
            if n.compute_confidence() >= CONF_HIGH
        )

        self.setWindowTitle(
            f"Dead Code Explorer - {total} methods, "
            f"{no_callers} no callers, {high_conf} likely dead"
        )

    def _populate_module_filter(self):
        modules = set()
        if not self.parser:
            return
        for node in self.parser.nodes.values():
            try:
                rel = Path(node.file_path).relative_to(self.src_dir)
                modules.add(str(rel.parent))
            except ValueError:
                pass

        self.module_combo.blockSignals(True)
        self.module_combo.clear()
        self.module_combo.addItem("All Modules")
        for mod in sorted(modules):
            self.module_combo.addItem(mod)
        self.module_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filters(self):
        if not self.parser:
            return

        query = self.search_box.text().lower()
        module_filter = self.module_combo.currentText()
        conf_filter = self.conf_combo.currentText()
        kind_filter = self.kind_combo.currentText()
        hide_dismissed = self.hide_dismissed.isChecked()

        # Determine confidence threshold
        if "85" in conf_filter:
            min_conf = CONF_HIGH
        elif "50" in conf_filter:
            min_conf = CONF_MEDIUM
        elif "False" in conf_filter:
            min_conf = -1  # special: only show 0
        else:
            min_conf = 0   # show all no-callers

        filtered: List[MethodNode] = []
        for node in self.parser.nodes.values():
            if node.called_by:
                continue

            conf = node.compute_confidence()

            # Confidence filter
            if "False" in conf_filter:
                if conf != CONF_FALSE_POS:
                    continue
            elif conf < min_conf:
                continue

            # Module filter
            if module_filter != "All Modules":
                try:
                    rel = Path(node.file_path).relative_to(self.src_dir)
                    if str(rel.parent) != module_filter:
                        continue
                except ValueError:
                    continue

            # Kind filter
            if kind_filter == "Private methods (_)":
                if not (node.is_method and node.is_private):
                    continue
            elif kind_filter == "Public methods":
                if not (node.is_method and not node.is_private
                        and not node.is_dunder):
                    continue
            elif kind_filter == "Module functions":
                if node.is_method:
                    continue
            elif kind_filter == "Properties":
                if not (node.is_property or node.is_setter
                        or node.is_deleter or node.is_qt_property):
                    continue
            elif kind_filter == "Classmethods/Staticmethods":
                if not (node.is_classmethod or node.is_staticmethod):
                    continue

            # Dismissed filter
            node_id = f"{node.file_path}:{node.full_name}"
            if hide_dismissed and node_id in self.dismissed_nodes:
                continue

            # Search filter
            if query:
                if (query not in node.name.lower()
                        and query not in node.full_name.lower()
                        and query not in node.rel_path.lower()):
                    continue

            filtered.append(node)

        # Sort
        self._sort_nodes(filtered)
        self.all_filtered = filtered
        self._populate_table(filtered)
        self._update_stats(filtered)
        self._update_header_arrows()
        self._update_filter_summary(filtered)

    def _sort_nodes(self, nodes: List[MethodNode]):
        """Sort nodes by current sort column."""
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder

        key_funcs = {
            0: lambda n: n.full_name.lower(),
            1: lambda n: n.rel_path.lower(),
            2: lambda n: n.line_number,
            3: lambda n: n.line_count,
            4: lambda n: self._get_kind_label(n),
            5: lambda n: n.compute_confidence(),
            6: lambda n: n.get_reason(),
        }
        key = key_funcs.get(self._sort_column, key_funcs[5])
        nodes.sort(key=key, reverse=reverse)

    def _get_kind_label(self, node: MethodNode) -> str:
        if node.is_property or node.is_setter or node.is_deleter:
            return "property"
        if node.is_qt_property:
            return "qt-prop"
        if node.is_classmethod:
            return "classmethod"
        if node.is_staticmethod:
            return "static"
        if node.is_dunder:
            return "dunder"
        if node.is_method and node.is_private:
            return "private"
        if node.is_method:
            return "public"
        return "function"

    def _on_header_clicked(self, logical_index: int):
        """Handle column header click for sorting."""
        if self._sort_column == logical_index:
            if self._sort_order == Qt.SortOrder.AscendingOrder:
                self._sort_order = Qt.SortOrder.DescendingOrder
            else:
                self._sort_order = Qt.SortOrder.AscendingOrder
        else:
            self._sort_column = logical_index
            if logical_index in (2, 3, 5):
                self._sort_order = Qt.SortOrder.DescendingOrder
            else:
                self._sort_order = Qt.SortOrder.AscendingOrder

        self._apply_filters()

    def _update_header_arrows(self):
        """Update column header labels with sort direction arrows."""
        base_labels = [
            "Method", "File", "Line", "Lines", "Kind", "Conf", "Reason"
        ]
        for i, label in enumerate(base_labels):
            if i == self._sort_column:
                arrow = "\u25B2" if self._sort_order == Qt.SortOrder.AscendingOrder else "\u25BC"
                base_labels[i] = f"{label} {arrow}"
        self.dead_list.setHorizontalHeaderLabels(base_labels)

    def _update_filter_summary(self, filtered: List[MethodNode]):
        """Show count breakdown in the filter panel."""
        if not self.parser:
            return

        total_no_callers = sum(
            1 for n in self.parser.nodes.values() if not n.called_by
        )
        n_priv = sum(1 for n in filtered if n.is_method and n.is_private)
        n_pub = sum(
            1 for n in filtered
            if n.is_method and not n.is_private and not n.is_dunder
        )
        n_func = sum(1 for n in filtered if not n.is_method)
        n_prop = sum(
            1 for n in filtered
            if n.is_property or n.is_setter or n.is_deleter
            or n.is_qt_property
        )

        self.filter_summary.setText(
            f"Total no-callers: {total_no_callers}\n"
            f"Showing: {len(filtered)}\n"
            f"  Private: {n_priv}\n"
            f"  Public: {n_pub}\n"
            f"  Functions: {n_func}\n"
            f"  Properties: {n_prop}"
        )

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_table(self, nodes: List[MethodNode]):
        self.dead_list.setRowCount(len(nodes))

        for i, node in enumerate(nodes):
            conf = node.compute_confidence()

            # Confidence-based color
            if conf >= CONF_HIGH:
                color = QColor("#FF4444")       # Red
            elif conf >= CONF_MEDIUM:
                color = QColor("#FFA500")       # Orange
            elif conf > CONF_FALSE_POS:
                color = QColor("#888888")       # Gray
            else:
                color = QColor("#555555")       # Dark gray

            name_item = QTableWidgetItem(node.full_name)
            name_item.setData(Qt.ItemDataRole.UserRole, node)
            name_item.setForeground(color)
            self.dead_list.setItem(i, 0, name_item)

            file_item = QTableWidgetItem(node.rel_path)
            file_item.setForeground(QColor("#777777"))
            self.dead_list.setItem(i, 1, file_item)

            line_item = QTableWidgetItem(str(node.line_number))
            line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            line_item.setForeground(QColor("#777777"))
            self.dead_list.setItem(i, 2, line_item)

            lines_item = QTableWidgetItem(str(node.line_count))
            lines_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            lines_item.setForeground(QColor("#777777"))
            self.dead_list.setItem(i, 3, lines_item)

            kind_item = QTableWidgetItem(self._get_kind_label(node))
            kind_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            kind_item.setForeground(QColor("#777777"))
            self.dead_list.setItem(i, 4, kind_item)

            # Confidence cell with colored bar background
            conf_item = QTableWidgetItem(str(conf))
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            conf_item.setForeground(color)
            bar_opacity = max(int(conf * 0.4), 10)
            conf_item.setBackground(QColor(
                color.red(), color.green(), color.blue(), bar_opacity
            ))
            self.dead_list.setItem(i, 5, conf_item)

            reason_item = QTableWidgetItem(node.get_reason())
            reason_item.setForeground(QColor("#888888"))
            self.dead_list.setItem(i, 6, reason_item)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def _update_stats(self, filtered_nodes: List[MethodNode]):
        total = len(self.parser.nodes) if self.parser else 0
        no_callers = (
            sum(1 for n in self.parser.nodes.values() if not n.called_by)
            if self.parser else 0
        )
        dead_lines = sum(n.line_count for n in filtered_nodes
                         if n.compute_confidence() >= CONF_HIGH)
        high_conf = sum(
            1 for n in filtered_nodes
            if n.compute_confidence() >= CONF_HIGH
        )

        self.stats_label.setText(
            f"Total: {total} methods  |  No callers: {no_callers}  |  "
            f"Dismissed: {len(self.dismissed_nodes)}  |  "
            f"Dead lines: ~{dead_lines}"
        )

        if high_conf > 0:
            self.dead_count_label.setText(
                f"Showing: {len(filtered_nodes)} ({high_conf} likely dead)"
            )
            self.dead_count_label.setStyleSheet(
                "color: #FF4444; font-weight: bold;"
            )
        else:
            self.dead_count_label.setText(f"Showing: {len(filtered_nodes)}")
            self.dead_count_label.setStyleSheet("color: #888888;")

    # ------------------------------------------------------------------
    # Selection & details
    # ------------------------------------------------------------------

    def _on_list_selection_changed(self):
        selected = self.dead_list.selectedItems()
        if not selected:
            return

        # Use the first selected row for details/preview
        row = selected[0].row()
        item = self.dead_list.item(row, 0)
        if not item:
            return
        node = item.data(Qt.ItemDataRole.UserRole)
        if node:
            self._show_node_details(node)
            self._show_source_preview(node)

    def _show_node_details(self, node: MethodNode):
        self.selected_node = node
        conf = node.compute_confidence()

        details = (
            f'<b style="color: #FFC66D; font-size: 11pt;">'
            f'{node.full_name}</b><br><br>'
            f'<span style="font-family: Consolas, monospace;">'
            f'<b>File:</b> {node.rel_path}<br>'
            f'<b>Line:</b> {node.line_number}'
            f' ({node.line_count} lines)<br>'
            f'<b>Kind:</b> {self._get_kind_label(node)}<br>'
            f'<br>'
            f'<b>Confidence:</b>'
            f' <span style="color: {self._conf_color(conf)}">'
            f'{conf}%</span><br>'
            f'<b>Callers:</b> {len(node.called_by)}<br>'
            f'<b>Calls out:</b> {len(node.calls)}<br>'
            f'</span>'
        )

        if node.decorators:
            decs = ', '.join(sorted(node.decorators))
            details += f"<b>Decorators:</b> {decs}<br>"

        if node.base_classes:
            bases = ', '.join(node.base_classes)
            details += f"<b>Base classes:</b> {bases}<br>"

        if node.called_by:
            details += "<br><b>Called by:</b><br>"
            for caller in sorted(node.called_by)[:15]:
                details += (
                    f'<span style="color: #6A8759;">  {caller}</span><br>'
                )
            if len(node.called_by) > 15:
                details += (
                    f"  ... and {len(node.called_by) - 15} more<br>"
                )

        self.details_label.setText(details)

        # Analysis flags
        flags_parts: List[tuple] = []

        if node.is_dunder:
            flags_parts.append(('green', "Dunder method -- called by Python"))
        if node.is_abstract:
            flags_parts.append(
                ('green', "Abstract method -- implemented by subclasses")
            )
        if node.is_init:
            flags_parts.append(
                ('green', "Constructor -- called on instantiation")
            )
        if node.is_setter or node.is_deleter:
            flags_parts.append(
                ('green', "Property setter/deleter -- descriptor protocol")
            )
        if node.is_qt_property:
            flags_parts.append(
                ('green', "Qt property -- invoked by QPropertyAnimation")
            )
        if node.connected_to_signal:
            flags_parts.append(('green', "Connected to Qt signal"))
        if node.is_dataclass_special:
            flags_parts.append(('green', "Dataclass special method"))
        if node.is_test:
            flags_parts.append(
                ('green', "Test method -- invoked by pytest")
            )
        if node.referenced_as_string:
            flags_parts.append(
                ('yellow', "Referenced as string (getattr/config dispatch)")
            )
        if node.passed_as_callback:
            flags_parts.append(('yellow', "Passed as callback argument"))
        if node.name in ASTParser.FRAMEWORK_CALLBACKS:
            flags_parts.append(
                ('yellow', f"Framework callback: {node.name}")
            )
        if node.is_property:
            flags_parts.append(
                ('orange', "Property getter -- may be used in templates")
            )
        if node.is_override:
            flags_parts.append(
                ('orange', "Overrides parent class method")
            )

        if not flags_parts and not node.called_by:
            flags_parts.append(
                ('red', "No callers found and no mitigating patterns")
            )
            if node.is_private:
                flags_parts.append(
                    ('red', "Private method -- strong candidate for removal")
                )

        colors = {
            'green': '#44FF44', 'yellow': '#FFC66D',
            'orange': '#FFA500', 'red': '#FF4444',
        }
        flags_html = ""
        for color_name, text in flags_parts:
            flags_html += (
                f'<span style="color: {colors[color_name]}">'
                f'{text}</span><br>'
            )

        self.flags_label.setText(flags_html)
        self.goto_button.setEnabled(True)
        self.dismiss_button.setEnabled(True)

    # ------------------------------------------------------------------
    # Source preview
    # ------------------------------------------------------------------

    def _read_source_lines(self, file_path: str) -> List[str]:
        """Read and cache source lines for a file."""
        if file_path not in self._source_cache:
            try:
                with open(file_path, encoding="utf-8") as f:
                    self._source_cache[file_path] = f.readlines()
            except (OSError, UnicodeDecodeError):
                self._source_cache[file_path] = []
        return self._source_cache[file_path]

    def _show_source_preview(self, node: MethodNode):
        """Show the source code of the selected method in the preview."""
        lines = self._read_source_lines(node.file_path)
        if not lines:
            self.source_preview.setPlainText(
                f"# Could not read {node.file_path}"
            )
            return

        # Show a few lines of context before and the full method
        ctx_before = 3
        start = max(0, node.line_number - 1 - ctx_before)
        end = min(len(lines), node.line_number - 1 + node.line_count)

        preview_lines = []
        for idx in range(start, end):
            lineno = idx + 1
            marker = ">" if node.line_number <= lineno < (node.line_number + node.line_count) else " "
            raw = lines[idx].rstrip("\n\r")
            preview_lines.append(f"{marker} {lineno:4d} | {raw}")

        self.source_preview.setPlainText("\n".join(preview_lines))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _conf_color(self, conf: int) -> str:
        if conf >= CONF_HIGH:
            return "#FF4444"
        if conf >= CONF_MEDIUM:
            return "#FFA500"
        if conf > CONF_FALSE_POS:
            return "#888888"
        return "#555555"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _goto_source(self):
        if not self.selected_node:
            return

        import subprocess
        import platform

        node = self.selected_node
        try:
            if platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        ["code", "-g",
                         f"{node.file_path}:{node.line_number}"],
                        capture_output=True
                    )
                    if result.returncode != 0:
                        raise FileNotFoundError
                except FileNotFoundError:
                    subprocess.Popen(["notepad", node.file_path])
            else:
                subprocess.run(
                    ["code", "-g",
                     f"{node.file_path}:{node.line_number}"]
                )
        except Exception:
            QMessageBox.information(
                self, "Open Source",
                f"Could not open editor.\n"
                f"File: {node.file_path}\nLine: {node.line_number}"
            )

    def _dismiss_selected(self):
        """Dismiss all selected rows (batch support)."""
        nodes = self._selected_nodes()
        if not nodes:
            return

        current_row = self.dead_list.currentRow()
        for node in nodes:
            node_id = f"{node.file_path}:{node.full_name}"
            self.dismissed_nodes.add(node_id)

        save_dismissed(self.dismissed_nodes)
        self._apply_filters()

        # Select next row
        if current_row < self.dead_list.rowCount():
            self.dead_list.selectRow(current_row)
        elif self.dead_list.rowCount() > 0:
            self.dead_list.selectRow(self.dead_list.rowCount() - 1)

    def _undismiss_selected(self):
        """Un-dismiss all selected rows."""
        nodes = self._selected_nodes()
        for node in nodes:
            node_id = f"{node.file_path}:{node.full_name}"
            self.dismissed_nodes.discard(node_id)

        save_dismissed(self.dismissed_nodes)
        self._apply_filters()

    def _clear_all_dismissed(self):
        """Clear all dismissed items after confirmation."""
        if not self.dismissed_nodes:
            return
        reply = QMessageBox.question(
            self, "Clear Dismissed",
            f"Clear all {len(self.dismissed_nodes)} dismissed items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.dismissed_nodes.clear()
            save_dismissed(self.dismissed_nodes)
            self._apply_filters()

    def _export_csv(self):
        """Export current filtered list to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Dead Code Report", "dead_code_report.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Method", "File", "Line", "Lines",
                    "Kind", "Confidence", "Reason",
                ])
                for node in self.all_filtered:
                    writer.writerow([
                        node.full_name,
                        node.rel_path,
                        node.line_number,
                        node.line_count,
                        self._get_kind_label(node),
                        node.compute_confidence(),
                        node.get_reason(),
                    ])
            self.statusBar().showMessage(  # type: ignore[union-attr]
                f"Exported {len(self.all_filtered)} items to {file_path}",
                5000,
            )
        except OSError as e:
            QMessageBox.warning(
                self, "Export Error", f"Could not write file:\n{e}"
            )

    def _export_clipboard(self):
        """Export current filtered list to clipboard."""
        lines = []
        for node in self.all_filtered:
            conf = node.compute_confidence()
            lines.append(
                f"[{conf:3d}] {node.full_name}"
                f" | {node.rel_path}:{node.line_number}"
            )

        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
        self.statusBar().showMessage(  # type: ignore[union-attr]
            f"Copied {len(lines)} items to clipboard", 3000
        )


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    src_dir = sys.argv[1] if len(sys.argv) > 1 else None
    window = DeadCodeWindow(src_dir)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
