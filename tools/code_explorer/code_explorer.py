#!/usr/bin/env python3
"""
Code Dependency Explorer
A WYSIWYG visual tool for exploring Python code dependencies.
"""
import sys
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Literal
from dataclasses import dataclass, field
from collections import defaultdict

CONFIG_FILE = Path.home() / ".code_explorer_config.json"

def load_last_folder() -> str:
    """Load last opened folder from config."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                return data.get("last_folder", "src")
        except:
            return "src"
    return "src"

def save_last_folder(folder: str):
    """Save last opened folder to config."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"last_folder": folder}, f)
    except:
        pass  # Ignore config errors

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QTreeWidget, QTreeWidgetItem,
    QSplitter, QToolBar, QLineEdit, QLabel, QPushButton, QFileDialog,
    QMessageBox, QMenu, QGraphicsRectItem, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QAction, QKeySequence

# --- INDUSTRIAL AMBER PALETTE ---
COLOR_VOID = QColor("#000000")
COLOR_PANEL = QColor("#111111")
COLOR_BORDER = QColor("#333333")
COLOR_TEXT = QColor("#DDDDDD")
COLOR_AMBER = QColor("#FFC66D")
COLOR_AMBER_DIM = QColor("#FF8C00")
COLOR_CYAN = QColor("#00E5FF")
COLOR_RED = QColor("#FF4444")
COLOR_GRAY = QColor("#666666")

STYLESHEET = """
QMainWindow { background-color: #000000; color: #DDDDDD; }
QWidget { background-color: #111111; color: #DDDDDD; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QSplitter::handle { background-color: #222222; }
QTreeWidget { background-color: #0A0A0A; border: 1px solid #333333; color: #CCCCCC; }
QTreeWidget::item:selected { background-color: #333333; color: #FFC66D; }
QHeaderView::section { background-color: #1A1A1A; color: #AA9977; border: 1px solid #333333; padding: 4px; font-weight: bold; }
QLabel { color: #DDDDDD; background: transparent; }
QLineEdit { 
    background-color: #0A0A0A; border: 1px solid #333333; color: #FFC66D; padding: 4px; border-radius: 4px;
    font-family: 'Consolas', monospace;
}
QLineEdit:focus { border: 1px solid #FFC66D; }
QPushButton {
    background-color: #1A1A1A; border: 1px solid #FFC66D; color: #FFC66D; padding: 6px 12px; border-radius: 4px; font-weight: bold;
}
QPushButton:hover { background-color: #2A2A2A; color: #FFFFFF; }
QPushButton:pressed { background-color: #000000; border-color: #AA8844; }
QPushButton:disabled { border-color: #444444; color: #666666; }
QToolBar { background-color: #111111; border-bottom: 2px solid #333333; spacing: 10px; padding: 5px; }
QToolBar QToolButton { color: #DDDDDD; background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px; }
QToolBar QToolButton:hover { border: 1px solid #666666; background-color: #222222; }
"""


@dataclass
class MethodNode:
    """Represents a method/function in the codebase."""
    name: str
    file_path: str
    line_number: int
    is_method: bool = False
    class_name: str = None
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)
    has_audit: bool = False
    crud_type: str = None  # 'INSERT', 'UPDATE', 'DELETE', or None
    is_property: bool = False
    is_override: bool = False  # Overrides parent class method
    is_signal: bool = False  # Qt signal
    is_slot: bool = False   # Qt slot
    decorators: Set[str] = field(default_factory=set)
    is_test: bool = False
    
    @property
    def full_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name
    
    @property
    def is_dead(self) -> bool:
        """Method is dead if nothing calls it."""
        return len(self.called_by) == 0
    
    def get_dead_flags(self) -> List[str]:
        """Return list of flags explaining why this might appear dead."""
        flags = []
        
        if self.called_by:
            flags.append(f"✓ Has {len(self.called_by)} caller(s)")
            return flags
        
        flags.append("✗ No callers found")
        
        if self.name in ASTParser.CALLBACKS:
            flags.append("→ Known callback (may be invoked by framework)")
        
        if self._is_entry_point():
            flags.append("→ Could be entry point")
        
        if self.is_signal or self.is_slot:
            flags.append("→ Qt signal/slot")
        
        if self.is_override:
            flags.append("→ Overrides parent class")
        
        if self.name.startswith('__') and self.name.endswith('__'):
            flags.append("→ Dunder method")
        
        if self.name.startswith('test_') or self.name.endswith('_test'):
            flags.append("→ Test method")
        
        if self.is_method and not self.name.startswith('_'):
            flags.append("→ Public method (API)")
        
        if self.decorators:
            flags.append(f"→ Has decorators: {', '.join(self.decorators)}")
        
        return flags
    
    def _is_likely_used(self) -> bool:
        """Check if method is likely used even without explicit callers."""
        name = self.name
        
        if name.startswith('__') and name.endswith('__'):
            return True
        
        if name.startswith('test_') or name.endswith('_test'):
            return True
        if self.is_test:
            return True
        
        for pattern in ASTParser.LIKELY_USED_PATTERNS:
            if pattern in name:
                return True
        
        if self.is_method and not name.startswith('_'):
            return True
        
        return False
    
    def _is_entry_point(self) -> bool:
        """Check if this method is likely an entry point."""
        name_lower = self.name.lower()
        path_lower = self.file_path.lower()
        
        if 'main' in name_lower or 'window' in name_lower:
            return True
        if name_lower in ('run', 'start', 'execute', 'init', '__init__'):
            return True
        if 'cli' in path_lower or 'command' in path_lower:
            if name_lower not in ('help', 'parse'):
                return True
        return False


class ASTParser:
    """Parses Python code and extracts method definitions and calls."""
    
    # Methods that are dynamically invoked by frameworks (Qt, etc.)
    # These won't have explicit callers in the code
    CALLBACKS = {
        # Qt widget callbacks
        'wheelEvent', 'mousePressEvent', 'mouseReleaseEvent', 'mouseMoveEvent',
        'mouseDoubleClickEvent', 'keyPressEvent', 'keyReleaseEvent',
        'paintEvent', 'resizeEvent', 'showEvent', 'hideEvent', 'closeEvent',
        'focusInEvent', 'focusOutEvent', 'enterEvent', 'leaveEvent',
        'dragEnterEvent', 'dragMoveEvent', 'dragLeaveEvent', 'dropEvent',
        'contextMenuEvent', 'timerEvent',
        # Qt layout callbacks
        'sizeHint', 'minimumSizeHint', 'heightForWidth', 'expandingDirections',
        # Qt graphics items
        'paint', 'boundingRect', 'shape',
        # Qt signals/slots
        'connect', 'disconnect',
    }
    
    # Patterns that indicate a method might be used
    LIKELY_USED_PATTERNS = {
        # Test patterns
        'test_', '_test', 'Test',
        # Dunder methods (commonly used)
        '__init__', '__str__', '__repr__', '__len__', '__getitem__',
        '__setitem__', '__delitem__', '__contains__', '__iter__', '__next__',
        '__call__', '__enter__', '__exit__', '__add__', '__sub__', '__mul__',
        '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__',
        '__hash__', '__eq__', '__bool__', '__nonzero__', '__copy__', '__deepcopy__',
        '__getattr__', '__setattr__', '__delattr__', '__getattribute__',
        '__slots__', '__class__', '__dict__',
    }
    
    def __init__(self, src_dir: str):
        self.src_dir = Path(src_dir)
        self.nodes: Dict[str, MethodNode] = {}
        self.calls: List[Tuple[str, str]] = []  # (caller, callee)
        
    def parse_all(self):
        """Parse all Python files in the source directory."""
        for py_file in self.src_dir.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue
            self._parse_file(py_file)
        
        # Second pass: Find Qt callbacks
        for py_file in self.src_dir.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                self._find_qt_callbacks(tree, py_file)
            except:
                continue
        
        # Resolve calls
        self._resolve_calls()
        
    def _parse_file(self, file_path: Path):
        """Parse a single Python file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except:
            return
        
        class FunctionCollector(ast.NodeVisitor):
            def __init__(self, parser, fp):
                self.parser = parser
                self.file_path = fp
                self.current_class = None
            
            def visit_ClassDef(self, node):
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = None
            
            def visit_FunctionDef(self, node):
                self.parser._process_function(node, self.file_path, self.current_class)
                self.generic_visit(node)
        
        visitor = FunctionCollector(self, file_path)
        visitor.visit(tree)
    
    def _process_function(self, node: ast.FunctionDef, file_path: Path, class_name: str = None):
        """Extract method info and calls from a function."""
        if class_name:
            node_id = f"{file_path}:{class_name}.{node.name}"
        else:
            node_id = f"{file_path}:{node.name}"
        
        # Check for CRUD operations
        has_audit = False
        crud_type = None
        
        method_source = ast.get_source_segment(file_path.read_text(encoding="utf-8"), node)
        if method_source:
            has_audit = 'AuditLogger' in method_source or 'auditor' in method_source.lower()
            if 'INSERT' in method_source.upper():
                crud_type = 'INSERT'
            elif 'UPDATE' in method_source.upper():
                crud_type = 'UPDATE'
            elif 'DELETE' in method_source.upper():
                crud_type = 'DELETE'
        
        # Check if it's a property
        is_property = any(
            isinstance(decorator, ast.Name) and decorator.id == 'property'
            for decorator in node.decorator_list
        )
        
        method_node = MethodNode(
            name=node.name,
            file_path=str(file_path),
            line_number=node.lineno,
            is_method=class_name is not None,
            class_name=class_name,
            has_audit=has_audit,
            crud_type=crud_type,
            is_property=is_property
        )
        
        self.nodes[node_id] = method_node
        
        # Find calls within this method
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    method_node.calls.add(child.func.attr)
                elif isinstance(child.func, ast.Name):
                    method_node.calls.add(child.func.id)
            # Also track property accesses (attribute access without call)
            elif isinstance(child, ast.Attribute):
                # This could be a property access like node.full_name
                if not isinstance(child.ctx, ast.Store):
                    method_node.calls.add(child.attr)
        
        self.nodes[node_id] = method_node
    
    def _find_qt_callbacks(self, tree: ast.AST, file_path: Path):
        """Find Qt signal/slot connections and mark callbacks as used."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Pattern: something.connect(callback)
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'connect':
                    if node.args:
                        callback = node.args[0]
                        # Extract method name from self.method_name or just method_name
                        method_name = None
                        if isinstance(callback, ast.Attribute):
                            # self._goto_source
                            method_name = callback.attr
                        elif isinstance(callback, ast.Name):
                            # some_function
                            method_name = callback.id
                        
                        if method_name:
                            # Mark this method as "dynamically called" via Qt
                            for node_id, method_node in self.nodes.items():
                                if method_node.name == method_name:
                                    # Add a fake caller to prevent "dead code" detection
                                    method_node.called_by.add(f"QtSignal:{file_path.stem}")
    
    def _resolve_calls(self):
        """Resolve method calls to their definitions."""
        name_to_nodes: Dict[str, List[MethodNode]] = defaultdict(list)
        for node in self.nodes.values():
            name_to_nodes[node.name].append(node)
            if node.full_name:
                name_to_nodes[node.full_name].append(node)
        
        for node_id, node in self.nodes.items():
            for call_name in list(node.calls):
                targets = name_to_nodes.get(call_name, [])
                for target in targets:
                    if self._is_likely_match(node, target):
                        node.calls.add(target.full_name)
                        target.called_by.add(node.full_name)
    
    def _is_likely_match(self, caller: MethodNode, callee: MethodNode) -> bool:
        """Heuristic to determine if a call likely refers to a method."""
        # Same file = likely match
        if caller.file_path == callee.file_path:
            return True
        
        caller_file = Path(caller.file_path).stem
        callee_file = Path(callee.file_path).stem
        
        if caller_file.replace('_service', '') in callee_file:
            return True
        if caller_file.replace('_repository', '') in callee_file:
            return True
        
        # Check if files share any significant word (e.g., "entity" matches "entity_click_router")
        caller_words = set(caller_file.replace('_', '').lower())
        callee_words = set(callee_file.replace('_', '').lower())
        shared = caller_words & callee_words
        
        # If they share 3+ characters, probably related
        if len(shared) >= 3:
            return True
        
        return False


class GraphNode(QGraphicsEllipseItem):
    """Visual representation of a method node."""
    
    def __init__(self, node: MethodNode, x: float, y: float, radius: float = 20, click_callback=None):
        super().__init__(x - radius, y - radius, radius * 2, radius * 2)
        self.node = node
        self.radius = radius
        self.click_callback = click_callback
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        
        # Determine base color based on status
        if node.is_dead:
            self.base_color = COLOR_RED
        elif not node.called_by and node._is_entry_point():
            self.base_color = COLOR_CYAN
        elif node.crud_type:
            if node.has_audit:
                self.base_color = COLOR_AMBER
            else:
                self.base_color = COLOR_AMBER_DIM
        else:
            self.base_color = COLOR_GRAY
        
        # Hollow Style: Dark Void Fill, Bright Border
        self.setBrush(QBrush(QColor("#1A1A1A")))
        self.setPen(QPen(self.base_color, 2))
        
        # Add label
        self.label = QGraphicsTextItem(node.name, self)
        self.label.setDefaultTextColor(QColor("#E0E0E0"))
        
        # Try to use a condensed font if available, fallback to Segoe UI
        font = QFont("Bahnschrift Condensed", 9)
        if not font.exactMatch():
            font = QFont("Segoe UI", 9)
        font.setBold(True)
        self.label.setFont(font)
        
        # Center label
        text_rect = self.label.boundingRect()
        self.label.setPos(x - text_rect.width() / 2, y - text_rect.height() / 2)
    
    def hoverEnterEvent(self, event):
        self.setPen(QPen(self.base_color, 4))
        self.label.setDefaultTextColor(QColor("#FFFFFF"))
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.setPen(QPen(self.base_color, 2))
        self.label.setDefaultTextColor(QColor("#E0E0E0"))
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                if self.click_callback and self.node:
                    self.click_callback(self.node)
            super().mousePressEvent(event)
        except RuntimeError:
            pass


class GraphEdge(QGraphicsLineItem):
    """Visual connection between nodes."""
    
    def __init__(self, source: GraphNode, target: GraphNode):
        super().__init__()
        self.source = source
        self.target = target
        self.update_position()
        
        pen = QPen(Qt.GlobalColor.gray)
        pen.setWidth(1)
        self.setPen(pen)
        self.setZValue(-1)  # Draw behind nodes
    
    def update_position(self):
        """Update line to connect node centers."""
        source_rect = self.source.rect()
        target_rect = self.target.rect()
        
        x1 = source_rect.center().x()
        y1 = source_rect.center().y()
        x2 = target_rect.center().x()
        y2 = target_rect.center().y()
        
        self.setLine(x1, y1, x2, y2)


class CodeGraphView(QGraphicsView):
    """Interactive graph view for code dependencies."""
    
    node_selected = pyqtSignal(MethodNode)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setBackgroundBrush(QBrush(COLOR_VOID))
        
        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.graph_nodes: Dict[str, GraphNode] = {}
        self.graph_edges: List[GraphEdge] = []
        self.all_nodes: Dict[str, MethodNode] = {}  # Keep reference to all nodes
        self.parser: ASTParser = None
        
        # Force-directed layout parameters
        self.repulsion = 1000
        self.attraction = 0.01
        self.damping = 0.9
        
    def build_graph(self, parser: ASTParser):
        """Build the visual graph from parsed data."""
        self.parser = parser
        self.all_nodes = parser.nodes.copy()
        
        self.show_all_nodes()
    
    def show_all_nodes(self):
        """Show all nodes in a simple grid layout."""
        self.scene.clear()
        self.graph_nodes.clear()
        self.graph_edges.clear()
        
        if not self.all_nodes:
            return
        
        modules = sorted(set(
            Path(node.file_path).relative_to(self.parser.src_dir).parent 
            for node in self.all_nodes.values()
        ))
        
        module_positions = {}
        module_cols = int(len(modules) ** 0.5) + 1
        for i, module in enumerate(modules):
            row = i // module_cols
            col = i % module_cols
            module_positions[module] = (col * 250, row * 200)
        
        node_list = list(self.all_nodes.items())
        
        for idx, (node_id, node) in enumerate(node_list):
            module = Path(node.file_path).relative_to(self.parser.src_dir).parent
            
            if module in module_positions:
                base_x, base_y = module_positions[module]
            else:
                base_x, base_y = 0, 0
            
            x = base_x + (idx % 8) * 25
            y = base_y + (idx // 8) * 20
            
            graph_node = GraphNode(node, x, y, click_callback=self._on_node_clicked)
            self.scene.addItem(graph_node)
            self.graph_nodes[node_id] = graph_node
        
        self._create_edges_for_visible()
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
    
    def show_neighborhood(self, center_node: MethodNode, depth: int = 1):
        """Show only nodes connected to the selected node."""
        self.scene.clear()
        self.graph_nodes.clear()
        self.graph_edges.clear()
        
        if not self.all_nodes:
            return
        
        neighbor_nodes: Dict[str, MethodNode] = {}
        center_key = f"{center_node.file_path}:{center_node.name}"
        neighbor_nodes[center_key] = center_node
        
        for _ in range(depth):
            for node in list(neighbor_nodes.values()):
                node_id = f"{node.file_path}:{node.name}"
                
                for target_full in node.calls:
                    for nid, n in self.all_nodes.items():
                        if n.full_name == target_full:
                            neighbor_nodes[nid] = n
                            break
                
                for caller_full in node.called_by:
                    for nid, n in self.all_nodes.items():
                        if n.full_name == caller_full:
                            neighbor_nodes[nid] = n
                            break
        
        nodes_to_show = list(neighbor_nodes.keys())
        
        center_idx = nodes_to_show.index(center_node.file_path + ":" + center_node.name) if (center_node.file_path + ":" + center_node.name) in nodes_to_show else 0
        
        for i, node_id in enumerate(nodes_to_show):
            node = self.all_nodes.get(node_id)
            if not node:
                continue
            
            x = 0
            y = 0
            if node_id == center_node.file_path + ":" + center_node.name:
                x, y = 200, 150
            else:
                angle = (i / (len(nodes_to_show) - 1)) * 2 * 3.14159 if len(nodes_to_show) > 1 else 0
                radius = 150
                x = 200 + int(radius * 0.7) + int(radius * 0.5 * (i % 4) / 4)
                y = 150 + int(80 * (i % 6) / 6)
            
            graph_node = GraphNode(node, x, y, click_callback=self._on_node_clicked)
            self.scene.addItem(graph_node)
            self.graph_nodes[node_id] = graph_node
        
        self._create_edges_for_visible()
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
    
    def _create_edges_for_visible(self):
        """Create edges only between visible nodes."""
        for node_id, node in self.graph_nodes.items():
            for call_name in node.node.calls:
                for target_id, target_node in self.all_nodes.items():
                    if target_node.full_name == call_name and target_id in self.graph_nodes:
                        edge = GraphEdge(self.graph_nodes[node_id], self.graph_nodes[target_id])
                        self.scene.addItem(edge)
                        self.graph_edges.append(edge)
    
    def _start_layout(self):
        """Start force-directed layout animation."""
        self.layout_timer = QTimer(self)
        self.layout_timer.timeout.connect(self._update_layout)
        self.layout_timer.start(50)  # 20 FPS
        
        # Stop after 5 seconds
        QTimer.singleShot(5000, self.layout_timer.stop)
    
    def _update_layout(self):
        """One iteration of force-directed layout."""
        # Calculate forces
        forces: Dict[str, QPointF] = {}
        
        for node_id, node in self.graph_nodes.items():
            force = QPointF(0, 0)
            
            # Repulsion from other nodes
            for other_id, other in self.graph_nodes.items():
                if node_id != other_id:
                    dx = node.x() - other.x()
                    dy = node.y() - other.y()
                    dist = max((dx ** 2 + dy ** 2) ** 0.5, 1)
                    
                    if dist > 0:
                        fx = (dx / dist) * self.repulsion / dist
                        fy = (dy / dist) * self.repulsion / dist
                        force += QPointF(fx, fy)
            
            forces[node_id] = force
        
        # Attraction along edges
        for edge in self.graph_edges:
            dx = edge.target.x() - edge.source.x()
            dy = edge.target.y() - edge.source.y()
            dist = max((dx ** 2 + dy ** 2) ** 0.5, 1)
            
            fx = dx * self.attraction * dist / 100
            fy = dy * self.attraction * dist / 100
            
            # Find node_ids for source and target
            source_id = None
            target_id = None
            for node_id, graph_node in self.graph_nodes.items():
                if graph_node == edge.source:
                    source_id = node_id
                if graph_node == edge.target:
                    target_id = node_id
            
            if source_id and source_id in forces:
                forces[source_id] += QPointF(fx, fy)
            if target_id and target_id in forces:
                forces[target_id] -= QPointF(fx, fy)
        
        # Apply forces
        for node_id, node in self.graph_nodes.items():
            if node_id in forces:
                force = forces[node_id] * self.damping
                node.setPos(node.x() + force.x(), node.y() + force.y())
                
                # Update connected edges
                for edge in self.graph_edges:
                    if edge.source == node or edge.target == node:
                        edge.update_position()
    
    def _on_node_clicked(self, node: MethodNode):
        """Handle node click."""
        if not self.graph_nodes:
            return
        for graph_node in self.graph_nodes.values():
            if graph_node.node == node:
                self.node_selected.emit(node)
                break
    
    def wheelEvent(self, event):
        """Zoom with mouse wheel."""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)


class CodeExplorerWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, src_dir: str = None):
        super().__init__()
        self.src_dir = src_dir or load_last_folder()
        self.parser = None
        
        self.setWindowTitle("Code Dependency Explorer")
        self.setGeometry(100, 100, 1400, 900)
        
        self.selected_node = None  # Initialize to avoid "dead method" detection
        
        self._create_ui()
        self._create_toolbar()
        
        # Auto-parse on startup
        self._parse_codebase()
    
    def _create_ui(self):
        """Create list-focused UI for dead code discovery."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stats bar at top
        stats_container = QWidget()
        stats_container.setStyleSheet("background-color: #1A1A1A; border-bottom: 1px solid #333333;")
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(10, 8, 10, 8)
        
        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet("color: #FFC66D; font-weight: bold;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        self.dead_count_label = QLabel("")
        self.dead_count_label.setStyleSheet("color: #FF4444; font-weight: bold;")
        stats_layout.addWidget(self.dead_count_label)
        
        main_layout.addWidget(stats_container)
        
        # Horizontal splitter: filters | list | details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left: Filter panel
        filter_panel = QWidget()
        filter_panel.setMaximumWidth(220)
        filter_layout = QVBoxLayout(filter_panel)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        filter_layout.addWidget(QLabel("<b>Filters</b>"))
        
        filter_layout.addWidget(QLabel("Module:"))
        self.module_combo = QComboBox()
        self.module_combo.addItem("All Modules")
        self.module_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.module_combo)
        
        filter_layout.addWidget(QLabel("CRUD Type:"))
        self.crud_filter_combo = QComboBox()
        self.crud_filter_combo.addItems(["All", "INSERT", "UPDATE", "DELETE"])
        self.crud_filter_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.crud_filter_combo)
        
        filter_layout.addWidget(QLabel("Show:"))
        self.show_combo = QComboBox()
        self.show_combo.addItems(["Dead Only", "All Methods", "Callbacks Only", "Entry Points"])
        self.show_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.show_combo)
        
        filter_layout.addSpacing(10)
        
        self.audit_warning_checkbox = QPushButton("Missing Audit Only")
        self.audit_warning_checkbox.setCheckable(True)
        self.audit_warning_checkbox.clicked.connect(self._apply_filters)
        filter_layout.addWidget(self.audit_warning_checkbox)
        
        filter_layout.addStretch()
        
        splitter.addWidget(filter_panel)
        
        # Center: Dead code list table
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        
        self.dead_list = QTableWidget()
        self.dead_list.setColumnCount(4)
        self.dead_list.setHorizontalHeaderLabels(["Method", "File", "Line", "CRUD"])
        self.dead_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dead_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.dead_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dead_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.dead_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.dead_list.itemDoubleClicked.connect(lambda item: self._goto_source())
        self.dead_list.setStyleSheet("""
            QTableWidget { background-color: #0A0A0A; color: #CCCCCC; gridline-color: #333333; }
            QTableWidget::item:selected { background-color: #333333; color: #FFC66D; }
            QHeaderView::section { background-color: #1A1A1A; color: #AA9977; border: 1px solid #333333; padding: 4px; }
        """)
        splitter.addWidget(self.dead_list)
        
        # Right: Details panel
        self.details_panel = QWidget()
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        details_layout.addWidget(QLabel("<b>Details</b>"))
        
        self.details_label = QLabel("Select a method to view details")
        self.details_label.setWordWrap(True)
        details_layout.addWidget(self.details_label)
        
        self.goto_button = QPushButton("Go to Source")
        self.goto_button.setEnabled(False)
        self.goto_button.clicked.connect(self._goto_source)
        details_layout.addWidget(self.goto_button)
        
        details_layout.addSpacing(10)
        
        details_layout.addWidget(QLabel("<b>Why appears dead</b>"))
        self.flags_label = QLabel("")
        self.flags_label.setWordWrap(True)
        details_layout.addWidget(self.flags_label)
        
        splitter.addWidget(self.details_panel)
        
        splitter.setSizes([200, 700, 300])
    
    def _create_toolbar(self):
        """Create toolbar with actions."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Open folder action
        open_action = QAction("Open Folder", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_folder)
        toolbar.addAction(open_action)
        
        # Current folder label
        self.folder_label = QLabel(f"📁 {Path(self.src_dir).name}")
        self.folder_label.setStyleSheet("QLabel { padding: 0 10px; }")
        toolbar.addWidget(self.folder_label)
        
        toolbar.addSeparator()
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._parse_codebase)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Search
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search dead code...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_box)
        
        toolbar.addSeparator()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)
    
    def _open_folder(self):
        """Open a folder picker dialog to select source directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Source Directory",
            self.src_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.src_dir = folder
            save_last_folder(folder)
            self.folder_label.setText(f"📁 {Path(folder).name}")
            self._parse_codebase()
    
    def _parse_codebase(self):
        """Parse the codebase and build the graph."""
        self.setWindowTitle("Code Dependency Explorer - Parsing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        QApplication.processEvents()
        
        self.parser = ASTParser(self.src_dir)
        self.parser.parse_all()
        
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setVisible(False)
        
        self._populate_dead_list()
        
        dead_count = sum(1 for n in self.parser.nodes.values() if n.is_dead)
        
        self.setWindowTitle(f"Code Dependency Explorer - {len(self.parser.nodes)} methods, {dead_count} dead")
    
    def _populate_dead_list(self):
        """Populate the dead code list table."""
        self.dead_list.setRowCount(0)
        
        modules = set()
        for node in self.parser.nodes.values():
            rel_path = Path(node.file_path).relative_to(self.src_dir)
            modules.add(str(rel_path.parent))
        
        self.module_combo.clear()
        self.module_combo.addItem("All Modules")
        for mod in sorted(modules):
            self.module_combo.addItem(mod)
        
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply filters to the dead code list."""
        if not self.parser:
            return
        
        query = self.search_box.text().lower()
        module_filter = self.module_combo.currentText()
        crud_filter = self.crud_filter_combo.currentText()
        show_filter = self.show_combo.currentText()
        audit_only = self.audit_warning_checkbox.isChecked()
        
        filtered = []
        for node in self.parser.nodes.values():
            rel_path = Path(node.file_path).relative_to(self.src_dir)
            module = str(rel_path.parent)
            
            if module_filter != "All Modules" and module != module_filter:
                continue
            
            if crud_filter != "All" and node.crud_type != crud_filter:
                continue
            
            if show_filter == "Dead Only" and not node.is_dead:
                continue
            
            if show_filter == "Callbacks Only" and node.name not in ASTParser.CALLBACKS:
                continue
            
            if show_filter == "Entry Points" and not node._is_entry_point():
                continue
            
            if audit_only and (node.crud_type and node.has_audit):
                continue
            
            if query and query not in node.name.lower() and query not in node.full_name.lower():
                continue
            
            filtered.append(node)
        
        self._populate_table(filtered)
        self._update_stats(filtered)
    
    def _populate_table(self, nodes: List[MethodNode]):
        """Populate table with filtered nodes."""
        self.dead_list.setRowCount(len(nodes))
        
        for i, node in enumerate(nodes):
            rel_path = Path(node.file_path).relative_to(self.src_dir)
            
            from PyQt6.QtWidgets import QTableWidgetItem
            
            name_item = QTableWidgetItem(node.full_name)
            name_item.setData(Qt.ItemDataRole.UserRole, node)
            if node.is_dead:
                name_item.setForeground(QColor("#FF4444"))
            self.dead_list.setItem(i, 0, name_item)
            
            file_item = QTableWidgetItem(str(rel_path))
            file_item.setForeground(QColor("#AAAAAA"))
            self.dead_list.setItem(i, 1, file_item)
            
            line_item = QTableWidgetItem(str(node.line_number))
            line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.dead_list.setItem(i, 2, line_item)
            
            crud_item = QTableWidgetItem(node.crud_type or "")
            if node.crud_type and not node.has_audit:
                crud_item.setForeground(QColor("#FF8C00"))
            else:
                crud_item.setForeground(QColor("#888888"))
            self.dead_list.setItem(i, 3, crud_item)
    
    def _update_stats(self, filtered_nodes: List[MethodNode]):
        """Update the stats display."""
        total = len(self.parser.nodes) if self.parser else 0
        dead = sum(1 for n in self.parser.nodes.values() if n.is_dead) if self.parser else 0
        filtered_dead = sum(1 for n in filtered_nodes if n.is_dead)
        
        self.stats_label.setText(f"Total: {total} methods | Dead: {dead}")
        
        if filtered_dead > 0:
            self.dead_count_label.setText(f"Showing: {filtered_dead} dead code")
            self.dead_count_label.setStyleSheet("color: #FF4444; font-weight: bold;")
        else:
            self.dead_count_label.setText(f"Showing: {len(filtered_nodes)} methods")
            self.dead_count_label.setStyleSheet("color: #888888;")
    
    def _on_list_selection_changed(self):
        """Handle selection change in the dead code list."""
        selected = self.dead_list.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        item = self.dead_list.item(row, 0)
        node = item.data(Qt.ItemDataRole.UserRole)
        
        if node:
            self._show_node_details(node)
    
    def _show_node_details(self, node: MethodNode):
        """Show details for a selected node."""
        self.selected_node = node
        
        rel_path = Path(node.file_path).relative_to(self.src_dir)
        
        details = f"""
<b>{node.full_name}</b><br>
<b>File:</b> {rel_path}<br>
<b>Line:</b> {node.line_number}<br>
<br>
<b>Status:</b> {"DEAD ❌" if node.is_dead else "Active ✓"}<br>
<b>Called by:</b> {len(node.called_by)} method(s)<br>
<b>Calls:</b> {len(node.calls)} method(s)<br>
"""

        if node.called_by:
            details += "<br><b>Called by:</b><br>"
            for caller in list(node.called_by)[:10]:
                details += f"• {caller}<br>"
            if len(node.called_by) > 10:
                details += f"... and {len(node.called_by) - 10} more<br>"
        
        if node.calls:
            details += "<br><b>Calls:</b><br>"
            for callee in list(node.calls)[:10]:
                details += f"• {callee}<br>"
            if len(node.calls) > 10:
                details += f"... and {len(node.calls) - 10} more<br>"
        
        flags_html = ""
        if node.is_dead:
            for flag in node.get_dead_flags():
                if flag.startswith("✓"):
                    flags_html += f'<span style="color: #44FF44;">{flag}</span><br>'
                elif flag.startswith("✗"):
                    flags_html += f'<span style="color: #FF4444;">{flag}</span><br>'
                else:
                    flags_html += f'<span style="color: #888888;">{flag}</span><br>'
        
        if node.crud_type:
            audit_status = "✓ Has audit" if node.has_audit else "⚠ Missing audit!"
            audit_color = "#44FF44" if node.has_audit else "#FF4444"
            details += f"<br><b>CRUD:</b> {node.crud_type}<br>"
            details += f"<b>Audit:</b> <span style='color: {audit_color}'>{audit_status}</span><br>"
        
        self.details_label.setText(details)
        self.flags_label.setText(flags_html)
        self.goto_button.setEnabled(True)
    
    def _goto_source(self):
        """Open source file at line."""
        if hasattr(self, 'selected_node'):
            import subprocess
            import platform
            import os
            
            node = self.selected_node
            try:
                if platform.system() == "Windows":
                    # Try VS Code first
                    try:
                        result = subprocess.run(
                            ["code", "-g", f"{node.file_path}:{node.line_number}"],
                            capture_output=True
                        )
                        if result.returncode != 0:
                            raise FileNotFoundError("VS Code not found")
                    except FileNotFoundError:
                        # Fallback to notepad
                        subprocess.Popen(["notepad", node.file_path])
                else:
                    # macOS/Linux
                    subprocess.run(["code", "-g", f"{node.file_path}:{node.line_number}"])
            except Exception as e:
                # If all else fails, just open the folder
                QMessageBox.information(
                    self,
                    "Open Source",
                    f"Could not open editor. File:\n{node.file_path}\nLine: {node.line_number}"
                )
    
    def _goto_source(self):
        """Open source file at line."""
        if not hasattr(self, 'selected_node') or not self.selected_node:
            return
        
        import subprocess
        import platform
        
        node = self.selected_node
        try:
            if platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        ["code", "-g", f"{node.file_path}:{node.line_number}"],
                        capture_output=True
                    )
                    if result.returncode != 0:
                        raise FileNotFoundError("VS Code not found")
                except FileNotFoundError:
                    subprocess.Popen(["notepad", node.file_path])
            else:
                subprocess.run(["code", "-g", f"{node.file_path}:{node.line_number}"])
        except Exception:
            QMessageBox.information(
                self,
                "Open Source",
                f"Could not open editor. File:\n{node.file_path}\nLine: {node.line_number}"
            )


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    src_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    window = CodeExplorerWindow(src_dir)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
