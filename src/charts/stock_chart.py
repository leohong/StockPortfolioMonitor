import plotly.graph_objects as go
from plotly.subplots import make_subplots

RANGES = {"20D": 20, "60D": 60, "120D": 120, "1Y": None}


def stock_chart(data, selected="120D"):
    if selected not in RANGES:
        raise ValueError("Unknown date range")
    visible = data.copy()
    if selected == "1Y":
        import pandas as pd
        cutoff = pd.Timestamp(data.market_date.iloc[-1]) - pd.DateOffset(years=1)
        visible = data[pd.to_datetime(data.market_date) > cutoff]
    else:
        visible = data.tail(RANGES[selected])
    phase2_columns = {"foreign_net", "investment_trust_net", "dealer_net", "margin_balance", "margin_change_1d"}
    if not phase2_columns.issubset(data.columns):
        raise ValueError("第二階段資料尚未完成，無法繪製五層圖表")
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.022,
                        row_heights=[0.40, 0.16, 0.16, 0.14, 0.14], specs=[[{}], [{}], [{}], [{"secondary_y": True}], [{}]])
    dates = visible.market_date
    # Explicit strings preserve source precision, including BIGINT volume/turnover.
    raw_hover = [f"{r.market_date}<br>開盤價 {r.open:.2f}<br>最高價 {r.high:.2f}<br>最低價 {r.low:.2f}<br>收盤價 {r.close:.2f}<br>成交量 {r.volume:,} 股<br>成交金額 {r.turnover:,} 元" for r in visible.itertuples()]
    fig.add_trace(go.Candlestick(x=dates, open=visible.open, high=visible.high, low=visible.low, close=visible.close,
                                name="開高低收（新臺幣）", text=raw_hover, hoverinfo="text"), row=1, col=1)
    for window, color in [(5, "#e5ac28"), (20, "#2982c2"), (60, "#aa69bd")]:
        fig.add_trace(go.Scatter(x=dates, y=visible[f"ma{window}"], name=f"{window} 日均線", line=dict(color=color), hovertemplate="%{y:.4f} 元<extra>%{fullData.name}</extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=dates, y=visible.volume, name="成交量（股）", text=raw_hover, textposition="none", hovertemplate="%{text}<extra></extra>", marker_color="#6f9ab8"), row=2, col=1)
    fig.add_trace(go.Scatter(x=dates, y=visible.volume_ma20, name="20 日均量", customdata=visible[["volume_ratio_20"]], hovertemplate="MA20 %{y:,.2f} 股<br>量比 %{customdata[0]:.4f} 倍<extra></extra>"), row=2, col=1)
    participants = [("foreign_net", "外資及陸資", "#4c78a8"),
                    ("investment_trust_net", "投信", "#f58518"),
                    ("dealer_net", "自營商", "#54a24b")]
    for column, label, color in participants:
        fig.add_trace(go.Bar(x=dates, y=visible[column], name=f"{label}買賣超（股）",
            marker_color=color, hovertemplate=f"{label}買賣超 %{{y:,.0f}} 股<extra></extra>"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dates, y=visible.margin_balance, name="融資餘額（交易單位）",
        line=dict(color="#b279a2"), hovertemplate="融資餘額 %{y:,.0f} 交易單位<extra></extra>"), row=4, col=1, secondary_y=False)
    fig.add_trace(go.Bar(x=dates, y=visible.margin_change_1d, name="融資日增減（交易單位）",
        marker_color="#e45756", opacity=0.35, hovertemplate="融資日增減 %{y:+,.0f} 交易單位<extra></extra>"), row=4, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=dates, y=visible.rsi14, name="相對強弱指標 RSI14", hovertemplate="%{y:.4f}<extra>RSI14</extra>"), row=5, col=1)
    for value in (30, 50, 70):
        fig.add_hline(y=value, line_dash="dot", line_color="#888", row=5, col=1)
    fig.update_yaxes(title_text="新臺幣", row=1, col=1)
    fig.update_yaxes(title_text="股", row=2, col=1)
    fig.update_yaxes(title_text="法人買賣超（股）", row=3, col=1)
    fig.update_yaxes(title_text="融資餘額", row=4, col=1, secondary_y=False)
    fig.update_yaxes(title_text="日增減", showgrid=False, row=4, col=1, secondary_y=True)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=5, col=1)
    fig.update_xaxes(type="date", rangeslider_visible=False, showspikes=True, spikemode="across", matches=None)
    # hoversubplots follows a shared axis ID; matched but distinct x IDs are insufficient.
    fig.update_traces(xaxis="x")
    from datetime import timedelta
    fig.update_yaxes(anchor="x")
    fig.update_shapes(xref="paper")
    for axis in ("xaxis2", "xaxis3", "xaxis4", "xaxis5"):
        setattr(fig.layout, axis, None)
    fig.update_layout(xaxis=dict(anchor="y5", showticklabels=True, tickformat="%Y/%m/%d", hoverformat="%Y/%m/%d",
        range=[str(dates.iloc[0] - timedelta(days=1)), str(dates.iloc[-1] + timedelta(days=1))]))
    fig.update_layout(height=1100, hovermode="x unified", hoversubplots="axis",
                      margin=dict(l=40, r=55, t=40, b=30), legend=dict(orientation="h"), barmode="relative")
    return fig
