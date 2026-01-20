---
trigger: always_on
---

# PyQt6 Development Patterns

## 1. Signal/Slot Architecture
*   **Loose Coupling**: Use signals for cross-widget communication. Widgets should NEVER hold direct references to siblings.
*   **Naming Convention**:
    *   Signals: `{action}Changed` (e.g., `selectionChanged`, `filterApplied`)
    *   Slots: `on_{sender}_{signal}` or `handle_{action}` (e.g., `on_filter_changed`, `handle_selection`)
*   **Connection Safety**:
    *   ALWAYS disconnect signals before reconnecting to avoid duplicate connections
    *   Use `try/except` or existence checks before disconnecting
    *   Example:
        ```python
        try:
            self.filter_widget.filterChanged.disconnect(self.handle_filter)
        except (TypeError, RuntimeError):
            pass  # Not connected
        self.filter_widget.filterChanged.connect(self.handle_filter)
        ```

## 2. Widget Lifecycle Management
*   **Initialization Order**:
    1. Call `super().__init__()`
    2. Initialize instance variables
    3. Call `_init_ui()` to create widgets
    4. Call `_connect_signals()` to wire up signals/slots
    5. Call `_load_data()` or similar if needed
*   **Cleanup**: Override `closeEvent()` to:
    *   Disconnect signals
    *   Stop timers
    *   Release resources (database connections, file handles)
    *   Save state (window geometry, splitter positions)

## 3. Model-View Patterns
*   **QAbstractTableModel**: Use for table data instead of manual row management
    *   Override: `rowCount()`, `columnCount()`, `data()`, `headerData()`
    *   Implement `flags()` for editability
    *   Use `beginInsertRows()`/`endInsertRows()` for updates
*   **QSortFilterProxyModel**: Use for filtering/sorting instead of rebuilding tables
*   **Delegates**: Use `QStyledItemDelegate` for custom rendering/editing
    *   Set via `setItemDelegate()` or `setItemDelegateForColumn()`

## 4. Threading Rules
*   **The Golden Rule**: NEVER access widgets from worker threads
*   **Worker Pattern**:
    1. Create worker class inheriting `QObject`
    2. Move to `QThread` using `moveToThread()`
    3. Use signals to return results to main thread
    4. Example:
        ```python
        worker = ImportWorker(files)
        thread = QThread()
        worker.moveToThread(thread)
        worker.finished.connect(thread.quit)
        worker.result.connect(self.handle_import_result)
        thread.started.connect(worker.run)
        thread.start()
        ```
*   **Blocking Operations**: Use `QProgressDialog` with `processEvents()` for short tasks, workers for long tasks

## 5. Layout Best Practices
*   **Never use fixed sizes**: Use `setMinimumSize()`, `setMaximumSize()`, `sizePolicy` instead
*   **Splitters over fixed layouts**: Use `QSplitter` for resizable panels
*   **Margins & Spacing**: Set via layout, not individual widgets
    ```python
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)
    ```
*   **Stretch Factors**: Use `addWidget(widget, stretch)` to control size distribution

## 6. Dialog Standards
*   **Modal Dialogs**: Use `exec()` for forms that block workflow
*   **Modeless Dialogs**: Use `show()` for inspectors/tools
*   **Result Handling**:
    ```python
    dialog = MyDialog(self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        result = dialog.get_result()
    ```
*   **Parent Relationships**: ALWAYS pass parent to dialogs for proper memory management
    ```python
    dialog = MyDialog(self)  # 'self' is parent
    ```

## 7. Resource Management
*   **Icons**: Load once, cache in class variable or constants
*   **Fonts**: Define in `theme.qss`, use `objectName` to apply
*   **Images**: Use `QPixmap` for display, `QImage` for manipulation
*   **Memory Leaks**: Watch for:
    *   Circular references (parent-child with extra refs)
    *   Signal connections that never disconnect
    *   Timers that never stop

## 8. Event Handling
*   **Event Filters**: Use for global keyboard shortcuts or cross-widget events
    ```python
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F3:
                self.handle_search()
                return True
        return super().eventFilter(obj, event)
    ```
*   **Overriding Events**: Only override what you need, always call `super()`
*   **Accepted/Ignored**: Call `event.accept()` or `event.ignore()` appropriately

## 9. Common Anti-Patterns to Avoid
*   ❌ Creating widgets in loops without proper parenting
*   ❌ Using `QMessageBox.exec()` in non-UI threads
*   ❌ Storing widget references in service layer
*   ❌ Using `deleteLater()` on widgets you still reference
*   ❌ Connecting signals in loops without lambda scope capture
    ```python
    # BAD
    for i in range(10):
        btn.clicked.connect(lambda: self.handle(i))  # All buttons call handle(10)

    # GOOD
    for i in range(10):
        btn.clicked.connect(lambda checked, idx=i: self.handle(idx))
    ```

## 10. Testing PyQt6 Components
*   **Use pytest-qt**: Provides `qtbot` fixture for widget testing
*   **Mock QMessageBox**: Always patch in tests
    ```python
    @patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes)
    def test_delete_action(self, mock_msg, qtbot):
        # Test code
    ```
*   **Simulating Interactions**:
    ```python
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.keyClick(widget, Qt.Key.Key_Enter)
    qtbot.waitSignal(widget.mySignal, timeout=1000)
    ```
