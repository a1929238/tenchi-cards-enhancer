from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
import json

# 使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
class WebStatistics():
    """
    使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
    """
    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.statistics = self.main_window.statistics
        self.src = "https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js" # 没办法，暂时使用公共cdn
        self.init_tab()
        
    def init_tab(self):
        """
        初始化标签页
        """
        self.web_view = QWebEngineView()
        self.stats_tab_widget = QTabWidget(self.main_window.tab_3)
        
        # 创建使用四叶草标签页
        self.stats_tab_widget.addTab(self.create_empty_tab("使用四叶草总和"), "使用四叶草")
        self.stats_tab_widget.addTab(self.create_empty_tab("使用香料总和"), "使用香料")
        self.stats_tab_widget.addTab(self.create_empty_tab("使用卡片总和"), "使用卡片")
        self.stats_tab_widget.addTab(self.create_empty_tab("强化出卡片总和"), "强化出卡片")
        self.stats_tab_widget.addTab(self.create_empty_tab("强化次数/成功次数"), "强化次数/成功次数")

        # 连接 tab change 信号
        self.stats_tab_widget.currentChanged.connect(lambda index: self.load_tab_content(self.stats_tab_widget, index))

        # 将四叶草综合页预加载内容
        self.load_tab_content(self.stats_tab_widget, 0)
    
    def create_empty_tab(self, type):
        """
        创建一个空的标签页
        """
        tab = QWidget()
        tab.setProperty("type", type)
        layout = QVBoxLayout(tab)
        tab.setLayout(layout)
        return tab

    def load_tab_content(self, stats_tab_widget, index):
        """
        加载标签页内容
        """
        tab = stats_tab_widget.widget(index)
        layout = tab.layout()

        if layout.count() == 0 or layout.itemAt(0).widget() is not self.web_view:
            # 清除旧的 QWebEngineView
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
            layout.addWidget(self.web_view)

        type = tab.property("type")
        
        if type == "强化次数/成功次数":
            html = self.create_bar_statistics_html()
        else:
            html = self.create_pie_statistics_html(type)
        
        self.web_view.setHtml(html)

    def create_pie_statistics_html(self, type):
        """
        创建饼图统计数据的 HTML
        """
        # 创建饼option
        option1, option2 = self.create_pie_options(type)
        # 创建html
        html = self.create_double_statistics_html(option1, option2)
        return html

    def create_bar_statistics_html(self):
        """
        创建柱状图统计数据的 HTML
        """
        # 创建柱状图option
        option = self.create_bar_option()
        # 创建html
        html = self.create_statistics_html(option)
        return html


    def create_double_statistics_html(self, option1, option2):
        """
        创建统计数据的html，包含切换按钮
        """
        # 将option转换为json字符串
        option1_str = json.dumps(option1)
        option2_str = json.dumps(option2)
        # 创建html
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>ECharts</title>
            <!-- Import ECharts -->
            <script src="{self.src}"></script>
        </head>
        <body>
            <!-- Container for ECharts -->
            <div id="main" style="width: 475px;height:375px;"></div>
            <button onclick="showChart1()">显示绑定</button>
            <button onclick="showChart2()">显示不绑</button>
            <script type="text/javascript">
                var myChart = echarts.init(document.getElementById('main'));
                var option1 = {option1_str};
                var option2 = {option2_str};

                function showChart1() {{
                    myChart.setOption(option1);
                }}

                function showChart2() {{
                    myChart.setOption(option2);
                }}

                // 默认显示第一个图表
                showChart1();
            </script>
        </body>
        </html>
        """
        return html
    
    def create_statistics_html(self, option):
        """
        创建统计数据的html，不包含切换按钮
        """
        # 将option转换为json字符串
        option_str = json.dumps(option)
        # 创建html
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>ECharts</title>
            <!-- Import ECharts -->
            <script src="{self.src}"></script>
        </head>
        <body>
            <!-- Container for ECharts -->
            <div id="main" style="width: 475px;height:400px;"></div>
            <script type="text/javascript">
                var myChart = echarts.init(document.getElementById('main'));
                var option = {option_str};
                myChart.setOption(option)
            </script>
        </body>
        </html>
        """
        return html

    def create_pie_options(self, type:str) -> tuple:
        """
        使用统计数据来创建饼图的option，分别为绑定和不绑
        """
        bind_data = []
        unbind_data = []
        for name, value in self.statistics[type]["绑定"].items():
            if value == 0:
                continue
            bind_data.append({"value": value, "name": name})
        for name, value in self.statistics[type]["不绑"].items():
            if value == 0:
                continue
            unbind_data.append({"value": value, "name": name})

        option1 = {
            "title": {
                "text": '绑定',
                "left": 'center',
                "top": '15%'
            },
            "tooltip": {
                "trigger": 'item'
            },
            "legend": {
                "type": 'scroll'
            },
            "series": [
                {
                    "name": '绑定',
                    "type": 'pie',
                    "radius": '50%',
                    "center": ['50%', '60%'],
                    "data": bind_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }
            ]
        }

        option2 = {
            "title": {
                "text": '不绑',
                "left": 'center',
                "top": '15%'
            },
            "tooltip": {
                "trigger": 'item'
            },
            "legend": {
                "type": 'scroll'
            },
            "series": [
                {
                    "name": '不绑',
                    "type": 'pie',
                    "radius": '50%',
                    "center": ['50%', '60%'],
                    "data": unbind_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }
            ]
        }

        return option1, option2
    
    def create_bar_option(self):
        """
        使用统计数据来创建柱状图的option
        """
        data_set = [['强化类型','强化次数','成功次数']]
        for type, count in self.statistics["强化次数总和"].items():
            if count == 0:
                continue
            success_count = self.statistics["成功次数总和"].get(type, 0)
            data_set.append([type, count, success_count])
        title = f"使用金币总额:{self.statistics['使用金币总额']}"

        option = {
            "title": {
                "text": title,
                "left": 'center'
            },
            "legend": {
                "left": "left"
            },
            "tooltip": {},
            "dataset":{
                "source": data_set
            },
            "xAxis": {
                "type": 'category'
            },
            "yAxis": {},
            "series": [{ 'type': 'bar' }, { 'type': 'bar' }]
        }
        return option