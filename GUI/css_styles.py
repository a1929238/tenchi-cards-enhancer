"""
用于存放css样式表的模块
"""

TAB_BAR_LIGHT = """
QTabBar::tab {
    background: rgb(170, 255, 255);
    border: 3px solid rgba(170, 255, 255, 155);
    border-bottom-color: rgb(170, 255, 255); /* same as the pane color */
    border-top-left-radius: 10px; /* 设置左上角圆角 */
    border-top-right-radius: 10px; /* 设置右上角圆角 */
    min-width: 10ex;
    padding: 8px;
}

QTabBar::tab:selected, QTabBar::tab:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 rgb(0, 255, 255), stop: 0.4 rgb(85, 255, 255),
                                stop: 0.5 rgb(0, 255, 255), stop: 1.0 rgb(0, 255, 255));
}

QTabBar::tab:selected {
    border-color: rgb(85, 255, 255);
    border-bottom-color: rgb(225, 255, 255); /* same as pane color */
}

QTabWidget::pane {
    background-color: rgba(255, 255, 255, 155);  /* 白色背景，55透明度 */
    border: 0px solid rgba(170, 255, 255, 120);
    top: -1px; /* this shifts the pane up to close the gap with the tab bar */
    border-bottom-right-radius: 20px;
}
"""

TAB_BAR_DARK = """
QTabBar::tab {
    background: rgb(49, 61, 79);  /* 深灰蓝色背景 */
    border: 3px solid rgba(74, 85, 104, 155); /* 深灰蓝色边框 */
    border-bottom-color: rgb(49, 61, 79); /* 与标签栏背景色相同 */
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 10ex;
    padding: 8px;
    color: rgb(240, 248, 255); /* 浅色文字 */
}

QTabBar::tab:selected, QTabBar::tab:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 rgb(90, 103, 122), stop: 0.4 rgb(74, 85, 104),
                                stop: 0.5 rgb(90, 103, 122), stop: 1.0 rgb(90, 103, 122)); /* 较亮的深灰蓝色渐变 */

}

QTabBar::tab:selected {
    border-color: rgb(90, 103, 122); /* 选中时边框颜色 */
    border-bottom-color: rgb(61,69,89); /* 选中时下边框颜色，与pane颜色相近，用于视觉上的融合 */
}

QTabWidget::pane {
    background-color: rgba(61, 69, 89, 155);  /* 深灰蓝色背景，55透明度 */
    border: 0px solid rgba(74, 85, 104, 120);
    top: -1px;
    border-bottom-right-radius: 20px;
}
"""


OUTPUT_LOG_LIGHT = """
QTextEdit {
    background-color: rgba(255, 255, 255, 50);
    border-color: rgba(255, 255, 255, 0);
    border-bottom-left-radius: 20px;
    border-bottom-right-radius: 20px;
}

QScrollBar:vertical {
    border: 1px solid rgba(170, 255, 255, 0);
    background: rgba(170, 255, 255, 45);
    width: 15px;
}

QScrollBar::handle:vertical {
    background: rgb(0, 255, 255);
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
    background: none;
    border: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

OUTPUT_LOG_DARK = """
QTextEdit {
    background-color: rgba(0, 0, 0, 50);       /* 黑色背景，透明度大约为 20% */
    border-color: rgba(0, 0, 0, 0);           /* 描边完全透明 */
    border-bottom-left-radius: 20px;
    border-bottom-right-radius: 20px;
}

QScrollBar:vertical {
    border: 1px solid rgba(85, 85, 85, 0);   /* 边框颜色与背景融合 */
    background: rgba(85, 85, 85, 45);       /* 深灰色背景，半透明 */
    width: 15px;
}

QScrollBar::handle:vertical {
    background: rgb(100, 100, 100);          /* 较亮的深灰色滑块 */
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
    background: none;
    border: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

PUSH_BUTTON_LIGHT = """
QPushButton {
    background-color: rgb(170, 255, 255);
    border-radius: 20px;
}
"""

PUSH_BUTTON_DARK = """
QPushButton {
    background-color: #3C3C3C;
    border-radius: 20px;
}
"""