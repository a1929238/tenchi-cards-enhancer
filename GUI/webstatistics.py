import json
import os
import numpy as np
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QSizePolicy, QLayout
from pandas import read_csv, Series, concat, errors

from module.globals import GLOBALS
from module.log.TenchiLogger import logger
from module.statistic.AsyncProduceStatistic import produce_recorder
from module.utils import resource_path

gold_cost_mapping = {
    "香料": {
        "0": 398,
        "1": 398,
        "2": 398,
        "3": 398,
        "4": 698,
        "5": 998,
        "6": 1298,
        "7": 1598,
        "8": 1998
    },
    "主卡等级": {
        "0": 298,
        "1": 298,
        "2": 298,
        "3": 298,
        "4": 298,
        "5": 398,
        "6": 398,
        "7": 698,
        "8": 698,
        "9": 1298,
        "10": 3298,
        "11": 6298,
        "12": 12298,
        "13": 24298,
        "14": 48298,
        "15": 96598
    }
}
REQUIRED_COLUMNS = [
    'timestamp', 'main_star', 'main_name', 'main_bind',
    'sub_star1', 'sub_name1', 'sub_bind1', 'sub_star2',
    'sub_name2', 'sub_bind2', 'sub_star3', 'sub_name3',
    'sub_bind3', 'clover_name', 'clover_bind',
    'original_success_rate', 'extra_success_rate', 'result'
]

# 使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
class WebStatistics:
    """
    使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
    """

    def __init__(self, main_window) -> None:
        self.csv_file = {}
        self.data_frame = None
        self.main_window = main_window
        self.src = "https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"  # 没办法，暂时使用公共cdn
        self.theme = GLOBALS.THEME
        self.background_color = '#100C2A' if self.theme == "dark" else '#FFFFFF'
        self.produce_stats = produce_recorder.produce_statistics
        self.web_view = QWebEngineView()
        # 设置 QWebEngineView 的 sizePolicy
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.html_cache = {}  # HTML 缓存

        self.refresh_data()
        if self.data_frame is not None:
            self.init_tab()

    def load_csv_to_df(self, csv_path):
        # 检查文件是否存在
        if not os.path.exists(csv_path):
            print(f"文件不存在: {csv_path}")
            self.data_frame = None
            return

        try:
            # 读取CSV文件
            df = read_csv(csv_path, header=0)

            # 检查列完整性
            if not set(REQUIRED_COLUMNS).issubset(df.columns):
                missing = set(REQUIRED_COLUMNS) - set(df.columns)
                print(f"缺少必要列: {', '.join(missing)}")
                return

            # 处理缺失值
            df.replace('', np.nan, inplace=True)

            # 将布尔值字段转换为布尔类型
            bool_columns = ['main_bind', 'sub_bind1', 'sub_bind2', 'sub_bind3', 'clover_bind']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower().map({'1': True, '0': False, 'true': True, 'false': False})

            # 将result字段转换为布尔类型
            if "result" in df.columns:
                df['result'] = df['result'].astype(str).str.lower().map({'true': True, 'false': False})

            self.data_frame = df

        except errors.EmptyDataError:
            print("文件内容为空")
            self.data_frame = None
            return

    def count_gold_cost(self):
        """统计金币消耗"""
        gold_cost = 0
        # 制卡金币消耗
        for level in range(0, 9):
            level_key = str(level)
            count = self.produce_stats["bind"][level_key] + self.produce_stats["unbind"][level_key]
            gold_cost += gold_cost_mapping["香料"][level_key] * count

        # 强化金币消耗
        main_star_counts = self.data_frame['main_star'].value_counts()
        for level, count in main_star_counts.items():
            level_key = str(level)
            gold_cost += gold_cost_mapping["主卡等级"][level_key] * count

        produce_recorder.save_gold_cost(gold_cost)

    def init_tab(self):
        """
        初始化标签页
        """

        self.stats_tab_widget = QTabWidget(self.main_window.tab_3)

        # 创建标签页
        self.stats_tab_widget.addTab(self.create_empty_tab("使用四叶草"), "使用四叶草")
        self.stats_tab_widget.addTab(self.create_empty_tab("制卡总和"), "制卡总和")
        self.stats_tab_widget.addTab(self.create_empty_tab("强化结果"), "强化结果")
        self.stats_tab_widget.addTab(self.create_empty_tab("强卡成功率"), "强卡成功率")
        self.stats_tab_widget.addTab(self.create_empty_tab("偏移-1"), "偏移-1")
        self.stats_tab_widget.addTab(self.create_empty_tab("偏移-2"), "偏移-2")

        # 连接 tab change 信号
        self.stats_tab_widget.currentChanged.connect(self.load_tab_content)

        # 预加载使用四叶草统计
        self.load_tab_content(0)

    def create_empty_tab(self, type):
        """
        创建一个空的标签页
        """
        tab = QWidget()
        tab.setProperty("type", type)
        layout = QVBoxLayout(tab)
        # 设置布局的 sizeConstraint
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        # 设置边距和间距为 0 (为了完全无缝)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tab.setLayout(layout)
        return tab

    def load_tab_content(self, index):
        """
        加载标签页内容
        """
        tab = self.stats_tab_widget.widget(index)
        layout = tab.layout()

        # 确保 web_view 没有父级，或者从之前的父级移除
        if self.web_view.parent() is not None:
            self.web_view.setParent(None)

        # 将 web_view 添加到当前标签页的布局
        layout.addWidget(self.web_view)

        tab_type = tab.property("type")

        if tab_type in self.html_cache:
            html = self.html_cache[tab_type]
        else:
            if tab_type == "强化结果":
                html = self.create_bar_for_upgrade()
            elif tab_type == "使用四叶草":
                html = self.create_html_for_clover()
            elif tab_type == "制卡总和":
                html = self.create_html_for_made_card()
            elif tab_type == "强卡成功率":
                html = self.create_html_for_success_rate()
            elif tab_type == "偏移-1":
                html = self.create_html_for_success_rate_and_p_by_add()
            elif tab_type == "偏移-2":
                html = self.create_html_for_success_rate_and_p_by_multi()
            self.html_cache[tab_type] = html

        self.web_view.setHtml(html)

    def refresh_data(self):
        """"刷新方法"""
        self.load_csv_to_df(csv_path="enhance_stats/card_stats.csv")
        if self.data_frame is not None:
            self.count_gold_cost()

    def reload(self):
        self.refresh_data()
        if self.data_frame is not None:
            self.html_cache = {}  # 清空缓存
            self.load_tab_content(self.stats_tab_widget.currentIndex())  # 重新加载当前页面

    """使用四叶草"""

    def create_html_for_clover(self):
        """
        创建柱状图 - 统计数据的 HTML
        """

        def create_echart(categories, bind_data, unbind_data):
            """
            使用统计数据来创建柱状图的option，分别为绑定和不绑
            """

            option1 = {
                "title": {
                    "text": '四叶草 - 绑定消耗量',
                    "left": 'center',
                    "top": '5%'
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "grid": {
                    "left": 50,
                    "right": 50,
                    "top": 40,
                    "bottom": 40
                },
                "xAxis": {
                    "type": 'value',
                    "axisLabel": {
                        "formatter": '{value}'
                    }
                },
                "yAxis": {
                    "type": 'category',
                    "data": categories
                },
                "series": [
                    {
                        "name": '使用数',
                        "type": 'bar',
                        "label": {
                            "show": True,
                            "position": 'right'
                        },
                        "data": bind_data
                    }
                ]
            }

            option2 = {
                "title": {
                    "text": '四叶草 - 不绑消耗量',
                    "left": 'center',
                    "top": '5%'
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "grid": {
                    "left": 50,
                    "right": 50,
                    "top": 40,
                    "bottom": 40
                },
                "xAxis": {
                    "type": 'value',
                    "axisLabel": {
                        "formatter": '{value}'
                    }
                },
                "yAxis": {
                    "type": 'category',
                    "data": categories
                },
                "series": [
                    {
                        "name": '使用数',
                        "type": 'bar',
                        "label": {
                            "show": True,
                            "position": 'right'
                        },
                        "data": unbind_data
                    }
                ]
            }

            return option1, option2

        def create_html(option1, option2):
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
                <script src="{self.src}"></script>
                <style>
                body {{
                    background: {self.background_color};
                }}
                }}
                </style>
            </head>
            <body>
                <!-- Container for ECharts -->
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
                <script type="text/javascript">
                    var myChart = echarts.init(document.getElementById('main'), '{self.theme}');
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

        # 使用df作为数据源
        df = self.data_frame

        # 处理四叶草数据
        df['clover_name'] = df['clover_name'].fillna('未使用')

        # 定义预期的四叶草名称顺序
        clover_order = ['未使用', '1级', '2级', '3级', '4级', '5级', '6级', '超能', 'SS', 'SSS', 'SSR']

        # 根据df中 clover_name列中 各个名字 出现次数 进行统计
        # 根据 clover_bind 是否为 True 分类
        # 次数可以为 0
        bind_data = []
        unbind_data = []

        # 统计绑定和未绑定的四叶草出现次数
        for clover in clover_order:
            bind_count = df[(df['clover_name'] == clover) & (df['clover_bind'] == True)].shape[0]
            unbind_count = df[(df['clover_name'] == clover) & (df['clover_bind'] == False)].shape[0]
            bind_data.append(bind_count)
            unbind_data.append(unbind_count)

        # 创建柱状图option
        option1, option2 = create_echart(categories=clover_order, bind_data=bind_data, unbind_data=unbind_data)

        # 创建html
        html = create_html(option1, option2)

        return html

    """制卡总和"""

    def create_html_for_made_card(self):
        """
        创建柱状图 - 统计数据的 HTML
        """

        def create_echart(categories, bind_data, unbind_data):
            """
            使用统计数据来创建柱状图的option，分别为绑定和不绑
            """

            option1 = {
                "title": {
                    "text": '卡片 - 绑定制作量',
                    "left": 'center',
                    "top": '5%'
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "grid": {
                    "left": 50,
                    "right": 50,
                    "top": 40,
                    "bottom": 40
                },
                "xAxis": {
                    "type": 'value',
                    "axisLabel": {
                        "formatter": '{value}'
                    }
                },
                "yAxis": {
                    "type": 'category',
                    "data": categories
                },
                "series": [
                    {
                        "name": '制作量',
                        "type": 'bar',
                        "label": {
                            "show": True,
                            "position": 'right'
                        },
                        "data": bind_data
                    }
                ]
            }

            option2 = {
                "title": {
                    "text": '卡片 - 不绑制作量',
                    "left": 'center',
                    "top": '5%'
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "grid": {
                    "left": 50,
                    "right": 50,
                    "top": 40,
                    "bottom": 40
                },
                "xAxis": {
                    "type": 'value',
                    "axisLabel": {
                        "formatter": '{value}'
                    }
                },
                "yAxis": {
                    "type": 'category',
                    "data": categories
                },
                "series": [
                    {
                        "name": '制作量',
                        "type": 'bar',
                        "label": {
                            "show": True,
                            "position": 'right'
                        },
                        "data": unbind_data
                    }
                ]
            }

            return option1, option2

        def create_html(option1, option2):
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
                <script src="{self.src}"></script>
                <style>
                body {{
                    background: {self.background_color};
                }}
                </style>
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
                <script type="text/javascript">
                    var myChart = echarts.init(document.getElementById('main'), '{self.theme}');
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

        card_order = list(range(9))

        bind_data = []
        unbind_data = []
        for level in card_order:
            bind_data.append(self.produce_stats["bind"][str(level)])
            unbind_data.append(self.produce_stats["unbind"][str(level)])

        # 创建柱状图option
        option1, option2 = create_echart(categories=card_order, bind_data=bind_data, unbind_data=unbind_data)

        # 创建html
        html = create_html(option1, option2)

        return html

    """强卡结果 成功数和失败数 的 堆积柱状图"""

    def create_bar_for_upgrade(self):
        """ 强化总数统计 """

        def df_transform():
            # === 检查数据存在性 ===
            if self.data_frame.empty:
                print("[Error] 数据框为空")
                return None, None

            # === 核心统计 ===
            grouped = self.data_frame.groupby(['main_star', 'main_bind'], observed=True)['result']
            stats = grouped.agg(success='sum', total='count').reset_index()

            # === 失败次数计算 ===
            stats['failure'] = stats['total'] - stats['success']

            # === 数据拆分 ===
            bind_mask = stats['main_bind'] == True
            unbind_mask = ~bind_mask
            bind_stats = stats[bind_mask].set_index('main_star')
            unbind_stats = stats[unbind_mask].set_index('main_star')

            # === 图表数据准备 ===
            def prepare_chart_data(df):
                return {
                    star: {'success': row['success'], 'failure': row['failure']}
                    for star, row in df.iterrows()
                }

            bind_data = prepare_chart_data(bind_stats)
            unbind_data = prepare_chart_data(unbind_stats)

            return bind_data, unbind_data

        def create_option(data, title):
            """ 使用统计数据来创建横向柱状图的option """
            # 创建一个包含从 0 到 15 的所有键的集合
            all_keys = set(range(16))
            # 使用字典推导式来补充缺失的键，并将默认值设置为 {'success': 0, 'failure': 0}
            data = {key: data.get(key, {'success': 0, 'failure': 0}) for key in all_keys}

            # 确保 categories 包含从 0 到 15 的所有键
            categories = sorted(data.keys())
            success_data = [data[k]['success'] for k in categories]
            failure_data = [data[k]['failure'] for k in categories]

            # 将 [0,1,...,15] -> ['0->1', '1->2', ... ,'15->16']
            categories = [f"{k}→{k + 1}" for k in categories]

            option = {
                "title": {
                    "text": title,
                    "left": "center",
                    "top": "0%"
                },
                "legend": {
                    "selectedMode": "false",
                    "top": "10%"
                },
                "grid": {
                    "left": 50,
                    "right": 20,
                    "top": 55,
                    "bottom": 10
                },
                "xAxis": {
                    "type": 'value',
                    "axisLabel": {
                        "formatter": '{value}次'
                    },
                    "show": False
                },
                "yAxis": {
                    "type": 'category',
                    "data": categories
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "series": [
                    {
                        "name": '成功次数',
                        "type": 'bar',
                        "stack": 'total',
                        "barWidth": '60%',
                        "label": {
                            "show": False
                        },
                        "itemStyle": {
                            "color": 'green'
                        },
                        "data": success_data
                    },
                    {
                        "name": '失败次数',
                        "type": 'bar',
                        "stack": 'total',
                        "barWidth": '60%',
                        "label": {
                            "show": False
                        },
                        "itemStyle": {
                            "color": 'red'
                        },
                        "data": failure_data
                    }
                ]
            }
            return option

        def create_html(option1, option2):
            """ 创建统计数据的html，包含切换按钮 """
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
                <script src="{self.src}"></script>
                <style>
                body {{
                    background: {self.background_color};
                }}
                }}
                </style>
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
                <script type="text/javascript">
                    var myChart = echarts.init(document.getElementById('main'), '{self.theme}');
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

        bind_data, unbind_data = df_transform()
        bind_opt = create_option(data=bind_data, title="绑定卡 - 强化总数")
        unbind_opt = create_option(data=unbind_data, title="不绑定卡 - 强化总数")

        # 创建html
        html = create_html(option1=bind_opt, option2=unbind_opt)
        return html

    """强卡 实际 成功率 - 堆叠柱状图 归一化"""

    def create_html_for_success_rate(self):
        """
        创建统计数据的html，包含切换按钮
        """

        def df_transform():
            # === 检查数据存在性 ===

            if self.data_frame.empty:
                print("[Error] 数据框为空")
                return None, None

            # === 核心统计 ===

            grouped = self.data_frame.groupby(['main_star', 'main_bind'], observed=True)['result']
            stats = grouped.agg(success='sum', total='count').reset_index()

            # === 成功率计算 ===

            stats['total'] = stats['total'].replace(0, 1)  # 防止除零
            stats['success_rate'] = (stats['success'] / stats['total'] * 100).round(0)
            stats['failure_rate'] = (100 - stats['success_rate']).round(0)

            # === 数据拆分 ===

            bind_mask = stats['main_bind'] == True
            unbind_mask = ~bind_mask

            bind_stats = stats[bind_mask].set_index('main_star')
            unbind_stats = stats[unbind_mask].set_index('main_star')

            # === 图表数据准备 ===

            def prepare_chart_data(df):
                return {
                    star: {'success': row['success_rate'], 'failure': row['failure_rate']}
                    for star, row in df.iterrows()
                }

            bind_data = prepare_chart_data(bind_stats)
            unbind_data = prepare_chart_data(unbind_stats)

            return bind_data, unbind_data

        def create_option(data, title):
            # 创建一个包含从 0 到 15 的所有键的集合
            all_keys = set(range(16))

            # 使用字典推导式来补充缺失的键，并将默认值设置为 {'success': 0, 'failure': 0}
            data = {key: data.get(key, {'success': 0, 'failure': 0}) for key in all_keys}

            # 确保 categories 包含从 0 到 15 的所有键
            categories = sorted(data.keys())

            success_data = [data[k]['success'] for k in categories]
            failure_data = [data[k]['failure'] for k in categories]

            # 将 [0,1,...,15] -> ['0->1', '1->2', ... ,'15->16']
            categories = [f"{k}→{k + 1}" for k in categories]

            opt = {
                "title": {
                    "text": title,
                    "left": "center",
                    "top": "0%"
                },
                "legend": {
                    "selectedMode": "false",
                    "top": "10%"
                },
                "grid": {
                    "left": 50,
                    "right": 20,
                    "top": 55,
                    "bottom": 10
                },
                "xAxis": {
                    "type": 'value',
                    "axisLabel": {
                        "formatter": '{value}%'
                    },
                    "show": False
                },
                "yAxis": {
                    "type": 'category',
                    "data": categories
                },
                "series": [
                    {
                        "name": '实际成功率',
                        "type": 'bar',
                        "stack": 'total',
                        "barWidth": '60%',
                        "label": {
                            "show": True,
                            "formatter": "{c}"
                        },
                        "itemStyle": {
                            "color": 'green'
                        },
                        "data": success_data
                    },
                    {
                        "name": '实际失败率',
                        "type": 'bar',
                        "stack": 'total',
                        "barWidth": '60%',
                        "label": {
                            "show": True,
                            "formatter": "{c}"
                        },
                        "itemStyle": {
                            "color": 'red'
                        },
                        "data": failure_data
                    }
                ]
            }

            return opt

        def create_html(option1, option2):
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
                <script src="{self.src}"></script>
                <style>
                body {{
                    background: {self.background_color};
                }}
                }}
                </style>
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
                <script type="text/javascript">
                    var myChart = echarts.init(document.getElementById('main'), '{self.theme}');
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

        bind_data, unbind_data = df_transform()

        bind_opt = create_option(bind_data, "绑定主卡 - 强化成功率")
        unbind_opt = create_option(unbind_data, "不绑主卡 - 强化成功率")

        html = create_html(option1=bind_opt, option2=unbind_opt)

        return html

    """强卡 理论成功率(加算) - 堆叠柱状图 归一化"""

    def create_html_for_success_rate_and_p_by_add(self):
        """
        创建统计数据的html，包含切换按钮，比较实际成功率与理论期望
        """

        def df_transform():
            # === 检查数据存在性 ===
            if self.data_frame.empty:
                print("[Error] 数据框为空")
                return None, None

            # === 计算理论成功率 ===
            self.data_frame['theory_success'] = (
                    self.data_frame['original_success_rate'] + self.data_frame['extra_success_rate']).clip(upper=100)

            # === 核心统计 ===
            grouped = self.data_frame.groupby(['main_star', 'main_bind'], observed=True)
            stats = grouped.agg(
                success=('result', 'sum'),
                total=('result', 'count'),
                theory_success_rate=('theory_success', 'mean')
            ).reset_index()

            # === 成功率计算 ===
            stats['total'] = stats['total'].replace(0, 1)
            stats['success_rate'] = (stats['success'] / stats['total'] * 100).round(1)
            stats['theory_success_rate'] = stats['theory_success_rate'].round(1)

            # === 数据拆分 ===
            bind_mask = stats['main_bind'] == True
            unbind_mask = ~bind_mask

            bind_stats = stats[bind_mask].set_index('main_star')
            unbind_stats = stats[unbind_mask].set_index('main_star')

            # === 图表数据准备 ===
            def prepare_chart_data(df):
                return {
                    star: {
                        'actual': row['success_rate'],
                        'theory': row['theory_success_rate']
                    }
                    for star, row in df.iterrows()
                }

            bind_data = prepare_chart_data(bind_stats)
            unbind_data = prepare_chart_data(unbind_stats)

            return bind_data, unbind_data

        def create_option(data, title):

            # 补全0-15星级数据
            all_keys = set(range(16))
            data = {key: data.get(key, {'actual': 0, 'theory': 0}) for key in all_keys}
            categories = sorted(data.keys())

            # 生成系列数据
            base_data = []
            green_data = []
            red_data = []
            for star in categories:
                actual = data[star]['actual']
                theory = data[star]['theory']
                base = round(min(actual, theory), 1)
                green = round(max(actual - theory, 0), 1)
                red = round(max(theory - actual, 0), 1)

                base_data.append(base)
                green_data.append(green)
                red_data.append(red)

            # 将 [0,1,...,15] -> ['0->1', '1->2', ... ,'15->16']
            categories = [f"{k}→{k + 1}" for k in categories]

            option = {
                "title": {
                    "text": title,
                    "left": "center",
                    "top": "0%"
                },
                "legend": {"show": False},
                "grid": {
                    "left": 50,
                    "right": 20,
                    "top": 55,
                    "bottom": 10
                },
                "xAxis": {
                    "type": "value",
                    "min": 0,
                    "max": 100,
                    "axisLabel": {
                        "formatter": "{value}%"
                    },
                    "show": False
                },
                "yAxis": {
                    "type": "category",
                    "data": [str(star) for star in categories],
                    "axisLabel": {
                        "interval": 0
                    }
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "series": [
                    {
                        "name": "填充值",
                        "type": "bar",
                        "stack": "Compare",
                        "itemStyle": {
                            "color": "#CBE5E3",
                            "opacity": 0.5
                        },
                        "data": base_data
                    },
                    {
                        "name": "向上偏移值",
                        "type": "bar",
                        "stack": "Compare",
                        "itemStyle": {
                            "color": "#91cc75"
                        },
                        "data": green_data,
                        "label": {
                            "show": False,
                            "position": "right",
                            "formatter": "{@[1]}%",
                            "color": "#333"
                        }
                    },
                    {
                        "name": "向下偏移值",
                        "type": "bar",
                        "stack": "Compare",
                        "itemStyle": {
                            "color": "#ee6666"
                        },
                        "data": red_data,
                        "label": {
                            "show": False,
                            "position": "left",
                            "formatter": "{@[1]}%",
                            "color": "#333"
                        }
                    }
                ]
            }
            return option

        def create_html(option1, option2):
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
                <script src="{self.src}"></script>
                <style>
                body {{
                    background: {self.background_color};
                }}
                }}
                </style>
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
                <script type="text/javascript">
                    var myChart = echarts.init(document.getElementById('main'), '{self.theme}');
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

        # 执行转换并生成HTML
        bind_data, unbind_data = df_transform()
        bind_opt = create_option(bind_data, "绑定主卡-实际vs理论成功率(加算)")
        unbind_opt = create_option(unbind_data, "不绑主卡-实际vs理论成功率(加算)")
        return create_html(bind_opt, unbind_opt)

    """强卡 理论成功率(乘算) - 堆叠柱状图 归一化"""

    def create_html_for_success_rate_and_p_by_multi(self):
        """
        创建统计数据的html，包含切换按钮，比较实际成功率与理论期望
        """

        def df_transform():
            # === 检查数据存在性 ===
            if self.data_frame.empty:
                print("[Error] 数据框为空")
                return None, None

            # === 计算理论成功率 ===
            self.data_frame['theory_success'] = ((
                                                         self.data_frame['original_success_rate'] / 100 +
                                                         (1 - self.data_frame['original_success_rate'] / 100) *
                                                         self.data_frame['extra_success_rate'] / 100) * 100).clip(
                upper=100)

            # === 核心统计 ===
            grouped = self.data_frame.groupby(['main_star', 'main_bind'], observed=True)
            stats = grouped.agg(
                success=('result', 'sum'),
                total=('result', 'count'),
                theory_success_rate=('theory_success', 'mean')
            ).reset_index()

            # === 成功率计算 ===
            stats['total'] = stats['total'].replace(0, 1)
            stats['success_rate'] = (stats['success'] / stats['total'] * 100).round(1)
            stats['theory_success_rate'] = stats['theory_success_rate'].round(1)

            # === 数据拆分 ===
            bind_mask = stats['main_bind'] == True
            unbind_mask = ~bind_mask

            bind_stats = stats[bind_mask].set_index('main_star')
            unbind_stats = stats[unbind_mask].set_index('main_star')

            # === 图表数据准备 ===
            def prepare_chart_data(df):
                return {
                    star: {
                        'actual': row['success_rate'],
                        'theory': row['theory_success_rate']
                    }
                    for star, row in df.iterrows()
                }

            bind_data = prepare_chart_data(bind_stats)
            unbind_data = prepare_chart_data(unbind_stats)

            return bind_data, unbind_data

        def create_option(data, title):

            # 补全0-15星级数据
            all_keys = set(range(16))
            data = {key: data.get(key, {'actual': 0, 'theory': 0}) for key in all_keys}
            categories = sorted(data.keys())

            # 生成系列数据
            base_data = []
            green_data = []
            red_data = []
            for star in categories:
                actual = data[star]['actual']
                theory = data[star]['theory']
                base = round(min(actual, theory), 1)
                green = round(max(actual - theory, 0), 1)
                red = round(max(theory - actual, 0), 1)

                base_data.append(base)
                green_data.append(green)
                red_data.append(red)

            # 将 [0,1,...,15] -> ['0->1', '1->2', ... ,'15->16']
            categories = [f"{k}→{k + 1}" for k in categories]

            option = {
                "title": {
                    "text": title,
                    "left": "center",
                    "top": "0%"
                },
                "legend": {"show": False},
                "grid": {
                    "left": 50,
                    "right": 20,
                    "top": 55,
                    "bottom": 10
                },
                "xAxis": {
                    "type": "value",
                    "min": 0,
                    "max": 100,
                    "axisLabel": {
                        "formatter": "{value}%"
                    },
                    "show": False
                },
                "yAxis": {
                    "type": "category",
                    "data": [str(star) for star in categories],
                    "axisLabel": {
                        "interval": 0
                    }
                },
                "tooltip": {
                    "trigger": 'axis',
                    "axisPointer": {
                        "type": 'shadow'
                    }
                },
                "series": [
                    {
                        "name": "填充值",
                        "type": "bar",
                        "stack": "Compare",
                        "itemStyle": {
                            "color": "#CBE5E3",
                            "opacity": 0.5
                        },
                        "data": base_data
                    },
                    {
                        "name": "向上偏移值",
                        "type": "bar",
                        "stack": "Compare",
                        "itemStyle": {
                            "color": "#91cc75"
                        },
                        "data": green_data,
                        "label": {
                            "show": False,
                            "position": "right",
                            "formatter": "{@[1]}%",
                            "color": "#333"
                        }
                    },
                    {
                        "name": "向下偏移值",
                        "type": "bar",
                        "stack": "Compare",
                        "itemStyle": {
                            "color": "#ee6666"
                        },
                        "data": red_data,
                        "label": {
                            "show": False,
                            "position": "left",
                            "formatter": "{@[1]}%",
                            "color": "#333"
                        }
                    }
                ]
            }
            return option

        def create_html(option1, option2):
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
                <script src="{self.src}"></script>
                <style>
                body {{
                    background: {self.background_color};
                }}
                }}
                </style>
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
                <script type="text/javascript">
                    var myChart = echarts.init(document.getElementById('main'), '{self.theme}');
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

        # 执行转换并生成HTML
        bind_data, unbind_data = df_transform()
        bind_opt = create_option(bind_data, "绑定主卡-实际vs理论成功率(乘算)")
        unbind_opt = create_option(unbind_data, "不绑主卡-实际vs理论成功率(乘算)")
        return create_html(bind_opt, unbind_opt)
