from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, \
    QColorDialog, QFileDialog, QToolBar, QSpinBox, QPushButton, QLineEdit
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor
from PyQt6.QtCore import QSize, Qt, QPoint

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.main = QLabel()
        self.setMinimumSize(640, 400)
        self.setWindowTitle("Castor")

        self.undo_stack=[]
        self.redo_stack=[]

        self.clickcount=0

        self.canva = QPixmap(QSize(600, 600))
        self.canva.fill(QColor('white'))

        self.pen = QPen()
        self.pen.setWidth(1)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.pen.setColor(QColor('black'))

        self.toolbar = QToolBar()
        self.label,self.text_label = QLabel('Width/Font:'),QLabel('Text:')
        self.color_button = QPushButton('color', self)
        self.color_button.setFixedWidth(40)
        self.color_button.setFixedHeight(30)
        open_button = QPushButton('Open', self)
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(1)
        self.width_spin.setMaximum(500)

        self.save_button = QPushButton('save', self)
        self.eraser_button = QPushButton('eraser', self)
        self.remove_button = QPushButton('X', self)
        self.undo_button,self.redo_button=QPushButton('<',self),QPushButton('>',self)
        self.line_edit=QLineEdit()

        self.color_button.clicked.connect(self.change_color)
        open_button.clicked.connect(self.open)
        self.width_spin.valueChanged.connect(lambda: self.pen.setWidth(self.width_spin.value()))
        self.save_button.clicked.connect(self.save)
        self.eraser_button.clicked.connect(self.eraser)
        self.remove_button.clicked.connect(self.remove)
        self.remove_button.setStyleSheet(f"background-color: red;"
                                             "color: white;")
        self.remove_button.setFixedSize(25,20)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)

        self.line_edit.setPlaceholderText('enter')
        self.line_edit.returnPressed.connect(self.draw_text)
        self.line_edit.setMaximumWidth(100)

        self.toolbar.addWidget(self.remove_button)
        self.toolbar.addWidget(open_button)
        self.toolbar.addWidget(self.save_button)
        self.toolbar.addWidget(self.color_button)
        self.toolbar.addWidget(self.label)
        self.toolbar.addWidget(self.width_spin)
        self.toolbar.addWidget(self.eraser_button)
        self.toolbar.addWidget(self.undo_button)
        self.toolbar.addWidget(self.redo_button)
        self.toolbar.addWidget(self.text_label)
        self.toolbar.addWidget(self.line_edit)
        self.addToolBar(self.toolbar)

        self.main.setPixmap(self.canva)
        self.setCentralWidget(self.main)

        self.last_pos = None

        self.setFocus()

    def keyPressEvent(self, event):
        self.keyPressedCall(event)

    def keyPressedCall(self, event):
        key = event.key()
        modifier = event.modifiers()
        match key:
            case Qt.Key.Key_Z if modifier == Qt.KeyboardModifier.ControlModifier:
                self.undo()
            case Qt.Key.Key_R if modifier == Qt.KeyboardModifier.ControlModifier:
                self.redo()
            case Qt.Key.Key_Up:
                self.width_spin.setValue(self.width_spin.value() + 1)
            case Qt.Key.Key_Down:
                self.width_spin.setValue(self.width_spin.value() - 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = event.position()
            self.undo_stack.append(self.canva.copy())

    def mouseMoveEvent(self, event):
        if self.last_pos:

            offset_x = self.main.geometry().x()
            offset_y = self.main.geometry().y()-14

            adjusted_last_pos = QPoint(int(self.last_pos.x() - offset_x), int(self.last_pos.y() - offset_y))
            adjusted_pos = QPoint(int(event.position().x() - offset_x), int(event.position().y() - offset_y))
            self.painter = QPainter(self.canva)
            self.painter.setPen(self.pen)

            self.painter.drawLine(adjusted_last_pos, adjusted_pos)
            self.painter.end()

            self.last_pos = event.position()

            self.main.setPixmap(self.canva)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_pos = None

    def change_color(self):
        dialog_c = QColorDialog()
        success = dialog_c.exec()
        if success:
            if self.eraser_button.text()=='Pen':
                self.eraser()
                self.remove_eraser()

            self.color = dialog_c.selectedColor()
            self.pen.setColor(self.color)
            self.color_button.setStyleSheet(f"background-color: {self.color.name()};"
                                             "color: white; border-radius: 5px;")
        else:
            pass

    def save(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "Images (*.png *.jpg *.bmp)")
        if file_name:
            self.canva.save(file_name)

    def open(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.bmp)")
        if file_name:
            image = QPixmap(file_name)
            self.canva = image.scaled(self.canva.size(), Qt.AspectRatioMode.KeepAspectRatio, \
                                      Qt.TransformationMode.SmoothTransformation)
            self.main.setPixmap(self.canva)

    def remove(self):
        self.canva = QPixmap(QSize(self.width(), self.height()))
        self.canva.fill(QColor('white'))
        self.main.setPixmap(self.canva)
        self.setCentralWidget(self.main)

    def eraser(self):
        self.clickcount+=1
        if self.clickcount==1:
            self.eraser_button.setText('Pen')
            self.eraser_button.clicked.connect(self.remove_eraser)
            self.current_color = self.pen.color()
            self.pen.setColor(QColor('white'))

    def remove_eraser(self):
        self.clickcount=0
        self.pen.setColor(self.current_color)
        self.eraser_button.setText('eraser')
        self.eraser_button.clicked.connect(self.eraser)

    def resizeEvent(self, event):
        new_size = event.size()
        new_canvas = QPixmap(new_size)
        new_canvas.fill(QColor('white'))

        self.painter = QPainter(new_canvas)
        self.painter.drawPixmap(QPoint(0, 0), self.canva)
        self.painter.end()

        self.canva = new_canvas
        self.main.setPixmap(self.canva)
        super().resizeEvent(event)

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.canva.copy())
            self.canva=self.undo_stack.pop()
            self.main.setPixmap(self.canva)

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.canva.copy())
            self.canva=self.redo_stack.pop()
            self.main.setPixmap(self.canva)

    def draw_text(self):
        text = self.line_edit.text()
        if text:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            offset_x = self.main.geometry().x()
            offset_y = self.main.geometry().y() - 8
            adjusted_pos = QPoint(int(mouse_pos.x() - offset_x), int(mouse_pos.y() - offset_y))
            self.painter = QPainter(self.canva)
            font=self.painter.font()
            font.setPointSize(self.width_spin.value())
            self.painter.setFont(font)
            self.painter.setPen(self.pen)

            if not text in ['=s','=c']:
                self.painter.drawText(adjusted_pos, text)
            else:
                size = self.width_spin.value() * 5
                if text == '=c':

                    self.painter.drawEllipse(adjusted_pos, size, size)
                else:
                    self.painter.drawRect(adjusted_pos.x(), adjusted_pos.y(), size, size)
            self.painter.end()
            self.line_edit.clear()
            self.undo_stack.append(self.canva.copy())
            self.setFocus()
            self.main.setPixmap(self.canva)

app = QApplication([])
app.setApplicationName("Castor")
window = MainWindow()
window.show()
app.exec()

'''
pyinstaller --clean --onedir --noconsole --icon=castttor.png --strip Castor.py
cd /Users/Programing/testPy/GUIframework/Paint/
'''
