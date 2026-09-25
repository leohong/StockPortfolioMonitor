import streamlit as st
import json
from src.i18n import STATUS, RANGE_LABELS, FIELDS, message, display_value

from src.config import load_config
from src.charts.stock_chart import stock_chart, RANGES
from src.services.stock_service import load_stock, refresh, refresh_phase2, refresh_phase3
from src.database.db import connect, read_institutional, read_margin, read_pivots, read_levels, read_structure

STRUCTURE_STATES = {"UPTREND_STRUCTURE": "上升結構", "DOWNTREND_STRUCTURE": "下降結構",
                    "POSSIBLE_BASE": "可能築底", "POSSIBLE_TOP": "可能築頂",
                    "RANGE": "區間整理", "UNCONFIRMED": "尚未確認"}


def stock_detail():
    settings, holdings, _ = load_config()
    with connect(settings.database):
        pass
    st.title("台股技術分析儀表板")
    st.caption("第三階段 · 證交所官方資料、價格結構與支撐壓力 · 五層互動圖")
    holding = st.selectbox("股票", holdings, format_func=lambda h: f"{h.ticker} {h.name}")
    if st.button("更新市場資料", type="primary"):
        try:
            with st.spinner("取得官方資料、驗證並儲存…"):
                refresh(settings, holding.ticker)
                refresh_phase2(settings, holding.ticker)
                refresh_phase3(settings, holding.ticker)
            st.success("資料更新完成")
        except Exception as exc:
            st.error("更新失敗，已保留原有資料。請確認網路連線與官方來源是否可用。")
            with st.expander("錯誤詳細資訊"):
                st.code(str(exc))
    data, quality = load_stock(settings, holding.ticker)
    if quality.status == "FAIL":
        st.warning("尚無可分析資料或驗證失敗。請按「更新市場資料」。")
        for error in quality.errors:
            st.write(message(error))
        return
    latest = data.iloc[-1]
    with connect(settings.database) as db:
        institutional_count = len(read_institutional(db, holding.ticker))
        margin_count = len(read_margin(db, holding.ticker))
        pivots, levels, structure = read_pivots(db, holding.ticker), read_levels(db, holding.ticker), read_structure(db, holding.ticker)
    if institutional_count < 250 or margin_count < 250:
        st.warning(f"第二階段資料尚未完成：法人 {institutional_count}/250 日、融資融券 {margin_count}/250 日。請按「更新市場資料」。")
        return
    a, b, c = st.columns(3)
    a.metric(f"{holding.ticker} {holding.name}", f"{latest.close:.2f} 元")
    b.metric("最新交易日", str(latest.market_date))
    c.metric("資料品質", STATUS[quality.status])
    st.caption(f"行情 {len(data)} 日 · 法人 {institutional_count} 日 · 融資融券 {margin_count} 日 · 成交量／法人：股 · 融資融券：交易單位")
    if structure:
        st.subheader("價格結構")
        st.write(f"狀態：**{STRUCTURE_STATES[structure.state]}**　高點證據：{structure.high_label or '—'} {structure.high_pivot_date or '—'} / {structure.high_price or '—'} 元　低點證據：{structure.low_label or '—'} {structure.low_pivot_date or '—'} / {structure.low_price or '—'} 元")
        st.caption(f"Pivot 敏感度：左 {settings.pivot_left_bars} 日／右 {settings.pivot_right_bars} 日；圖上標註轉折日，訊號僅自確認日起可用。")
    st.link_button("證交所官方來源", latest.source)
    with st.expander("資料品質與限制", expanded=True):
        for warning in quality.warnings:
            st.warning(message(warning))
        with connect(settings.database) as db:
            audit = db.execute("SELECT checked_at,status,details_json FROM data_quality_events WHERE ticker=? ORDER BY checked_at DESC LIMIT 5", [holding.ticker]).fetchdf()
        for row in audit.itertuples():
            with st.expander(f"檢查紀錄：{row.checked_at} · {STATUS.get(row.status, row.status)}"):
                details = json.loads(row.details_json)
                for item in details.get("errors", []) + details.get("warnings", []):
                    st.write(message(item))
    selected = st.radio("顯示區間", list(RANGES), format_func=RANGE_LABELS.get, index=2, horizontal=True)
    st.plotly_chart(stock_chart(data, selected, pivots, levels), width="stretch", config={"displaylogo": False, "scrollZoom": True})
    st.caption("五層依序為價格、成交量、三大法人、融資、RSI；共同日期軸與統一游標。指標先以完整歷史計算，再套用顯示區間。")
    with st.expander("逐日精確資料與來源"):
        day = st.selectbox("日期", list(reversed(data.market_date.tolist())))
        record = data[data.market_date == day].iloc[0]
        st.json({FIELDS.get(k, k): display_value(record[k]) for k in data.columns})
        display = data.copy()
        for column in ("source_type", "is_official", "volume_unit", "turnover_unit"):
            display[column] = display[column].map(display_value)
        st.dataframe(display.rename(columns=FIELDS), hide_index=True)
