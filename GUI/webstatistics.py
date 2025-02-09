import json

import numpy as np
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
import pandas as pd

from module.utils import resource_path


# 使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
class WebStatistics:
    """
    使用ECharts为统计数据绘制图表，用内置的谷歌浏览器显示
    """

    def __init__(self, main_window) -> None:
        self.csv_file = {}
        self.data_frame = None
        self.main_window = main_window
        self.statistics = self.main_window.statistics
        self.src = "https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"  # 没办法，暂时使用公共cdn

        # asyncio.create_task(self.load_csv_data()).add_done_callback(lambda _: self.init_tab())

        self.load_csv_to_df(csv_path=resource_path("enhance_stats//card_stats.csv"))

        self.init_tab()

    def load_csv_to_df(self, csv_path):
        # 读取CSV文件
        df = pd.read_csv(csv_path, header=0)

        # 处理缺失值
        df.replace('', np.nan, inplace=True)

        # 将布尔值字段转换为布尔类型
        bool_columns = ['main_bind', 'sub_bind1', 'sub_bind2', 'sub_bind3', 'clover_bind']
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower().map({'1': True, '0': False, 'true': True, 'false': False})

        # 将result字段转换为布尔类型
        df['result'] = df['result'].astype(str).str.lower().map({'true': True, 'false': False})

        self.data_frame = df

    def init_tab(self):
        """
        初始化标签页
        """
        self.web_view = QWebEngineView()
        self.stats_tab_widget = QTabWidget(self.main_window.tab_3)

        # 创建使用四叶草标签页
        self.stats_tab_widget.addTab(self.create_empty_tab("使用四叶草"), "使用四叶草")
        self.stats_tab_widget.addTab(self.create_empty_tab("制卡结果"), "制卡结果")
        self.stats_tab_widget.addTab(self.create_empty_tab("强化结果"), "强化结果")
        self.stats_tab_widget.addTab(self.create_empty_tab("强卡成功率"), "强卡成功率")

        # 连接 tab change 信号
        self.stats_tab_widget.currentChanged.connect(
            lambda index: self.load_tab_content(self.stats_tab_widget, index))

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

        if type == "强化结果":
            html = self.create_bar_for_upgrade()
        elif type == "使用四叶草":
            html = self.create_html_for_clover()
        elif type == "制卡结果":
            html = self.create_html_for_made_card()
        elif type == "强卡成功率":
            html = self.create_html_for_success_rate()

        self.web_view.setHtml(html)

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
            </head>
            <body>
                <!-- Container for ECharts -->
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
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

    """制卡结果"""

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
                    "text": '卡片 - 绑定制造量',
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
                        "name": '制造量',
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
                    "text": '卡片 - 不绑制造量',
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
                        "name": '制造量',
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
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
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

        df = self.data_frame

        card_order = list(range(9))
        bind_data = [0] * len(card_order)
        unbind_data = [0] * len(card_order)

        # 处理主卡的绑定和非绑定情况
        bind_main_counts = df[df['main_bind']]['main_star'].value_counts().sort_index()
        unbind_main_counts = df[~df['main_bind']]['main_star'].value_counts().sort_index()

        # 处理副卡的绑定和非绑定情况
        bind_sub_stars = pd.Series(dtype='int64')
        unbind_sub_stars = pd.Series(dtype='int64')

        for i in range(1, 4):
            sub_star = df[f'sub_star{i}']
            sub_bind = df[f'sub_bind{i}']

            # 绑定副卡
            mask_bind = (sub_bind == True) & (sub_star.notna())
            bind_sub = sub_star[mask_bind].astype(int)
            bind_sub_stars = pd.concat([bind_sub_stars, bind_sub])

            # 非绑定副卡
            mask_unbind = (sub_bind == False) & (sub_star.notna())
            unbind_sub = sub_star[mask_unbind].astype(int)
            unbind_sub_stars = pd.concat([unbind_sub_stars, unbind_sub])

        bind_sub_counts = bind_sub_stars.value_counts().sort_index()
        unbind_sub_counts = unbind_sub_stars.value_counts().sort_index()

        # 处理成功和失败的次数，区分绑定和非绑定
        # 绑定情况
        bind_success_mask = (df['main_bind']) & (df['result'] == 'success')
        bind_success_counts = df[bind_success_mask]['main_star'].value_counts().sort_index()

        bind_failure_mask = (df['main_bind']) & (df['result'] == 'failure')
        bind_failure_counts = df[bind_failure_mask]['main_star'].value_counts().sort_index()

        # 非绑定情况
        unbind_success_mask = (~df['main_bind']) & (df['result'] == 'success')
        unbind_success_counts = df[unbind_success_mask]['main_star'].value_counts().sort_index()

        unbind_failure_mask = (~df['main_bind']) & (df['result'] == 'failure')
        unbind_failure_counts = df[unbind_failure_mask]['main_star'].value_counts().sort_index()

        # 计算每个星级的制造量
        for s in card_order:
            # 绑定数据计算
            bind_main = bind_main_counts.get(s, 0)
            bind_sub = bind_sub_counts.get(s, 0)
            bind_succ = bind_success_counts.get(s - 1, 0)
            bind_fail = bind_failure_counts.get(s + 1, 0)
            bind_total = bind_main + bind_sub - bind_succ - bind_fail
            bind_data[s] = max(bind_total, 0)  # 确保非负

            # 非绑定数据计算
            unbind_main = unbind_main_counts.get(s, 0)
            unbind_sub = unbind_sub_counts.get(s, 0)
            unbind_succ = unbind_success_counts.get(s - 1, 0)
            unbind_fail = unbind_failure_counts.get(s + 1, 0)
            unbind_total = unbind_main + unbind_sub - unbind_succ - unbind_fail
            unbind_data[s] = max(unbind_total, 0)  # 确保非负

        # 转为 int 而不是 int64
        bind_data = [int(x) for x in bind_data]
        unbind_data = [int(x) for x in unbind_data]

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
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
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
                    "left": 20,
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
                        "name": '成功率 - (直接加算)',
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
                        "name": '失败率',
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
            </head>
            <body>
                <div id="main" style="width: 475px;height:375px;"></div>
                <div class="button-container" style="margin-left: 170px;">
                    <button onclick="showChart1()">显示绑定</button>
                    <button onclick="showChart2()">显示不绑</button>
                </div>
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

        bind_data, unbind_data = df_transform()

        bind_opt = create_option(bind_data, "绑定主卡 - 强化成功率")
        unbind_opt = create_option(unbind_data, "不绑主卡 - 强化成功率")

        html = create_html(option1=bind_opt, option2=unbind_opt)

        return html


    #
    # """强卡 理论成功率(加算) - 堆叠柱状图 归一化"""
    #
    # """强卡 理论成功率(乘算) - 堆叠柱状图 归一化"""
