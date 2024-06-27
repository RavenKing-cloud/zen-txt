import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QWidget, QVBoxLayout, QTextEdit,
                             QAction, QFileDialog, QMessageBox, QTabWidget, QInputDialog)
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QColor, QPainter, QTextFormat, QFont, QIcon, QKeySequence

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)
        self.file_path = None

        self.setStyleSheet("background-color: black; color: lightgreen;")
        self.setFont(QFont("Consolas", 11))

        self.lineNumberFont = QFont("Courier New", 12)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText("    ")  # Insert four spaces
            return
        super().keyPressEvent(event)

    def lineNumberAreaWidth(self):
        digits = 1
        max_block_count = max(1, self.blockCount())
        while max_block_count >= 10:
            max_block_count //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(20, 20, 20))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.white)
                painter.setFont(self.lineNumberFont)
                painter.drawText(0, top, self.lineNumberArea.width(), self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlightCurrentLine(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.yellow).lighter(5)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("ZenTXT - Editor")
        self.setGeometry(700, 100, 800, 600)
        
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.create_actions()
        self.create_menu()

        self.new_file()

    def create_actions(self):
        self.new_action = QAction("&New", self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.triggered.connect(self.new_file)

        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_file)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_file)

        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.triggered.connect(self.save_file_as)

        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.triggered.connect(self.undo)

    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self.undo_action)

    def new_file(self):
        new_editor = CodeEditor()
        new_index = self.tab_widget.addTab(new_editor, "Untitled")
        self.tab_widget.setCurrentIndex(new_index)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)")
        if file_path:
            with open(file_path, 'r') as file:
                content = file.read()

            new_editor = CodeEditor()
            new_editor.setPlainText(content)
            new_editor.file_path = file_path

            file_name = os.path.basename(file_path)
            new_index = self.tab_widget.addTab(new_editor, file_name)
            self.tab_widget.setCurrentIndex(new_index)

    def save_file(self):
        current_editor = self.tab_widget.currentWidget()
        if current_editor.file_path:
            self._save_to_path(current_editor.file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        current_editor = self.tab_widget.currentWidget()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "All Files (*);;Text Files (*.txt)")
        if file_path:
            current_editor.file_path = file_path
            self._save_to_path(file_path)

            file_name = os.path.basename(file_path)
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), file_name)

    def _save_to_path(self, file_path):
        current_editor = self.tab_widget.currentWidget()
        with open(file_path, 'w') as file:
            file.write(current_editor.toPlainText())

    def undo(self):
        current_editor = self.tab_widget.currentWidget()
        current_editor.undo()

    def close_tab(self, index):
        self.tab_widget.removeTab(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon", 'zen.png')
    app.setWindowIcon(QIcon(icon_path))
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())