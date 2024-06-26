import sys
import json
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MainWindow(QMainWindow):
    def __init__(self, option, src):
        super().__init__()
        self.setWindowTitle("ECharts in PyQt6")
        self.setGeometry(100, 100, 800, 600)

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        self.load_chart(option, src)

    def load_chart(self, option, src):
        # Convert Python dictionary to JSON string
        option_str = json.dumps(option)

        # HTML template to embed ECharts
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>ECharts</title>
            <!-- Import ECharts -->
            <script src="{src}"></script>
        </head>
        <body>
            <!-- Container for ECharts -->
            <div id="main" style="width: 600px;height:400px;"></div>
            <script type="text/javascript">
                // Initialize ECharts
                var myChart = echarts.init(document.getElementById('main'));
                // Specify chart configuration
                var option = {option_str};
                // Display the chart using the configuration items and data just specified.
                myChart.setOption(option);
            </script>
        </body>
        </html>
        """
        self.browser.setHtml(html)

if __name__ == "__main__":
    # Define the option dictionary and the src URL for ECharts
    option = {
            "title":[
                {
                "subtext": '绑定',
                "left": '16.67%',
                "top": '75%',
                "textAlign": 'center'
                },
                {
                "subtext": '不绑',
                "left": '83.33%',
                "top": '75%',
                "textAlign": 'center'
                }
            ],
            "tooltip": {
                "trigger": 'item'
            },
            "legend": {
            },
            "series": [
                {
                    "name": '绑定',
                    "type": 'pie',
                    "radius": '50%',
                    "center": ['25%', '75%'],
                    "data": [
        { "value": 1048, 'name': 'Search Engine' },
        { 'value': 735, 'name': 'Direct' },
        { 'value': 580, 'name': 'Email' },
        { 'value': 484, 'name': 'Union Ads' },
        { 'value': 300, 'name': 'Video Ads' }
      ],
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                },
                {
                    "name": '不绑',
                    "type": 'pie',
                    "radius": '50%',
                    "center": ['75%', '75%'],
                    "data": [
        { "value": 1048, 'name': 'Search Engine' },
        { 'value': 735, 'name': 'Direct' },
        { 'value': 580, 'name': 'Email' },
        { 'value': 484, 'name': 'Union Ads' },
        { 'value': 300, 'name': 'Video Ads' }
      ],
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
    src = "https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"

    app = QApplication(sys.argv)
    window = MainWindow(option, src)
    window.show()
    sys.exit(app.exec())
