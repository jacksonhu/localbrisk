import marimo


__generated_with = "0.9.7"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    mo.md(r"""
    # 牧原股份（SZ002714）近20个交易日成交量分析

    本 notebook 使用 `stock-data` skill 从腾讯自选股接口获取牧原股份（sz002714）最近20个交易日的日K数据，并对成交量进行基础统计分析和可视化。

    > 说明：本文件中已将一次查询得到的最近20日K线数据（包括成交量）以静态方式写入，方便在无外部网络/无 skill 环境下复现分析过程。
    """)


@app.cell
def _():
    # 原始K线数据（来自 stock-data kline sz002714 day 20 返回的 data.nodes）
    kline_nodes = [
        {"open": 46.84, "last": 46.73, "high": 47.49, "low": 46.40, "volume": 41535900.00, "amount": 1951278349.00, "date": "2026-02-05"},
        {"open": 46.09, "last": 46.41, "high": 47.05, "low": 46.05, "volume": 35902000.00, "amount": 1666070820.00, "date": "2026-02-06"},
        {"open": 46.16, "last": 46.65, "high": 47.29, "low": 46.08, "volume": 33472000.00, "amount": 1561810510.00, "date": "2026-02-09"},
        {"open": 46.46, "last": 45.92, "high": 46.94, "low": 45.83, "volume": 29733800.00, "amount": 1369389167.00, "date": "2026-02-10"},
        {"open": 45.88, "last": 46.03, "high": 46.17, "low": 45.35, "volume": 28609900.00, "amount": 1308787202.00, "date": "2026-02-11"},
        {"open": 45.81, "last": 45.24, "high": 46.08, "low": 45.17, "volume": 27639100.00, "amount": 1254800556.00, "date": "2026-02-12"},
        {"open": 45.24, "last": 45.35, "high": 46.08, "low": 45.02, "volume": 29893400.00, "amount": 1361870914.00, "date": "2026-02-13"},
        {"open": 45.51, "last": 44.56, "high": 45.86, "low": 44.40, "volume": 39137600.00, "amount": 1752206261.00, "date": "2026-02-24"},
        {"open": 44.51, "last": 44.79, "high": 45.09, "low": 44.41, "volume": 28359200.00, "amount": 1270976854.00, "date": "2026-02-25"},
        {"open": 45.03, "last": 45.13, "high": 45.98, "low": 44.91, "volume": 38872500.00, "amount": 1767240333.00, "date": "2026-02-26"},
        {"open": 45.15, "last": 46.90, "high": 47.06, "low": 45.15, "volume": 71847000.00, "amount": 3345129696.00, "date": "2026-02-27"},
        {"open": 46.50, "last": 46.81, "high": 48.14, "low": 46.42, "volume": 51336900.00, "amount": 2419022911.00, "date": "2026-03-02"},
        {"open": 46.70, "last": 46.53, "high": 47.50, "low": 46.46, "volume": 44967800.00, "amount": 2109667382.00, "date": "2026-03-03"},
        {"open": 46.69, "last": 47.13, "high": 47.23, "low": 46.26, "volume": 54724700.00, "amount": 2558352928.00, "date": "2026-03-04"},
        {"open": 47.13, "last": 46.80, "high": 47.18, "low": 46.18, "volume": 32351300.00, "amount": 1509164200.00, "date": "2026-03-05"},
        {"open": 46.67, "last": 49.34, "high": 49.53, "low": 46.55, "volume": 90999700.00, "amount": 4424914816.00, "date": "2026-03-06"},
        {"open": 49.60, "last": 49.41, "high": 50.76, "low": 49.21, "volume": 83824300.00, "amount": 4184045761.00, "date": "2026-03-09"},
        {"open": 48.88, "last": 48.33, "high": 49.55, "low": 48.19, "volume": 49295000.00, "amount": 2399023649.00, "date": "2026-03-10"},
        {"open": 48.34, "last": 49.31, "high": 49.78, "low": 48.22, "volume": 47550200.00, "amount": 2332330031.00, "date": "2026-03-11"},
        {"open": 49.50, "last": 50.54, "high": 50.68, "low": 49.00, "volume": 34338200.00, "amount": 1714509024.00, "date": "2026-03-12"},
    ]

    kline_nodes


@app.cell
def _():
    import pandas as pd

    df = pd.DataFrame(kline_nodes)
    # 成交量单位：股，这里转换为“万股”方便阅读
    df["volume_wan"] = df["volume"] / 10000
    df


@app.cell
def _():
    import numpy as np

    volume_stats = {
        "样本交易日数": len(df),
        "成交量均值(万股)": df["volume_wan"].mean(),
        "成交量中位数(万股)": df["volume_wan"].median(),
        "成交量最大值(万股)": df["volume_wan"].max(),
        "成交量最小值(万股)": df["volume_wan"].min(),
        "成交量标准差(万股)": df["volume_wan"].std(ddof=1),
    }

    volume_stats


@app.cell
def _(mo):
    mo.md(r"""
    ## 成交量统计结果解读

    - **样本范围**：最近20个交易日（日K）
    - **指标说明**：
      - 均值、中位数反映整体成交量水平
      - 最大值、最小值帮助识别放量/缩量极端交易日
      - 标准差衡量成交量波动程度

    下一个单元格将结合具体数值给出文字分析结论。
    """)


@app.cell
def _():
    # 生成简要文字分析
    mean_v = volume_stats["成交量均值(万股)"]
    median_v = volume_stats["成交量中位数(万股)"]
    max_v = volume_stats["成交量最大值(万股)"]
    min_v = volume_stats["成交量最小值(万股)"]

    analysis_text = f"""
    近20个交易日中：
    - 日均成交量约为 {mean_v:.2f} 万股，中位数为 {median_v:.2f} 万股，均值与中位数接近，说明整体成交量分布相对均衡，未出现极端失衡情况；
    - 最大单日成交量约为 {max_v:.2f} 万股，最小单日成交量约为 {min_v:.2f} 万股，最大/最小比值约为 {max_v/min_v:.2f} 倍，表明期间存在一定程度的放量与缩量，但波动仍在合理区间；
    - 结合标准差可进一步判断：若标准差接近均值的一半以上，则说明成交量波动较为明显，可能对应阶段性情绪或事件驱动。
    """

    print(analysis_text)


@app.cell
def _():
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 4))
    plt.bar(df["date"], df["volume_wan"], color="steelblue")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("成交量（万股）")
    plt.title("牧原股份（sz002714）近20个交易日成交量")
    plt.tight_layout()
    plt.show()


@app.cell
def _(mo):
    mo.md(r"""
    ## 小结

    - 使用 `stock-data kline sz002714 day 20` 获取了牧原股份最近20个交易日的日K数据；
    - 提取成交量字段并换算为“万股”进行统计分析；
    - 通过均值、中位数、极值和标准差刻画了成交量的整体水平与波动特征；
    - 使用柱状图展示了近20日成交量在时间维度上的变化，有助于识别明显放量/缩量的交易日。

    如需进一步分析，可以在此基础上：
    - 叠加价格涨跌幅，观察“价量配合”关系；
    - 计算5日、10日成交量均线，判断量能趋势；
    - 与行业指数或大盘成交量对比，评估相对活跃度。
    """)


if __name__ == "__main__":
    app.run()
