from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView


# 使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
class QWidgetWebExpectation(QWidget):
    """
    使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示, 显示为单独的窗口
    """

    def __init__(self, cost_total, net_profit, gold_cost, time_spend) -> None:
        super().__init__()
        self.cost_total = cost_total
        self.net_profit = net_profit
        self.net_profit_per = f"{net_profit / cost_total * 100:.1f}%"
        self.gold_cost = gold_cost
        self.time_spend = time_spend
        self.src = "https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"  # 没办法，暂时使用公共cdn
        self.web_view = QWebEngineView()
        self.cus_layout = QVBoxLayout()
        # 将html设置到QWebEngineView中
        self.web_view.setHtml(self.create_html())
        self.cus_layout.addWidget(self.web_view)
        self.setWindowTitle("强化收益")
        self.setLayout(self.cus_layout)



    def create_html(self):
        """
        创建统计数据的html，不包含切换按钮
        """
        # 创建html
        html = f"""
        <!DOCTYPE html>
        <html>
        
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ECharts</title>
            <!-- Import ECharts -->
            <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
            <title>Layout</title>
            <style>
                .container {{
                    display: flex;
                    justify-content: space-between;
                }}
        
                .left-column,
                .right-column {{
                    width: 45%;
                    flex: 1;
                }}
        
                .rect1 {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100%;
                }}
        
                .rect1 p {{
                    display: flex;
                    width: 100%;
                    justify-content: center;
                    margin: 0; /* 去除默认的段落间距 */
                }}
        
                .rect1 p > span {{
                    display: inline-block;
                }}
        
                .label {{
                    width: 40%;
                    text-align: right;
                    margin-right: 5px;
                }}
        
                .value {{
                    width: 60%;
                    text-align: left;
                }}
            </style>
        </head>
        
        <body>
            <div id="main_chart" style="width: 100%;height: 400px;"></div>
            <div class="container">
                <div class="left-column">
                    <div class="rect1">
                        <p><span class="label">利润   </span><span class="value">{self.net_profit:.0f}</span></p>
                    </div>
                    <div class="rect1">
                        <p><span class="label">成本   </span><span class="value">{self.cost_total:.0f}</span></p>
                    </div>
                    <div class="rect1">
                        <p><span class="label">利润率   </span><span class="value">{self.net_profit_per}</span></p>
                    </div>
                </div>
                <div class="right-column">
                    <div class="rect1">
                        <p><span class="label">耗时   </span><span class="value">{self.time_spend}</span></p>
                    </div>
                    <div class="rect1">
                        <p><span class="label">金币   </span><span class="value">{self.gold_cost:.0f}</span></p>
                    </div>
                </div>
            </div>
            <script type="text/javascript">
                var myChart = echarts.init(document.getElementById('main_chart'));
                var option = {{
                    tooltip: {{
                        trigger: 'item'
                    }},
                    legend: {{
                        top: '5%',
                        left: 'center'
                    }},
                    series: [
                        {{
                            name: 'Access From',
                            type: 'pie',
                            radius: ['40%', '70%'],
                            avoidLabelOverlap: false,
                            padAngle: 5,
                            itemStyle: {{
                                borderRadius: 10
                            }},
                            label: {{
                                show: false,
                                position: 'center'
                            }},
                            emphasis: {{
                                label: {{
                                    show: true,
                                    fontSize: 40,
                                    fontWeight: 'bold'
                                }}
                            }},
                            labelLine: {{
                                show: false
                            }},
                            data: [
                                {{ value: {self.cost_total}, name: '成本' }},
                                {{ value: {self.net_profit}, name: '利润' }}
                            ]
                        }}
                    ]
                }};
                myChart.setOption(option)
            </script>
        </body>
        
        </html>
        """
        return html
