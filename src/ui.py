import streamlit as st
import json
from src.i18n import STATUS, RANGE_LABELS, FIELDS, message, display_value

from src.config import load_config
from src.charts.stock_chart import stock_chart, RANGES
from src.services.stock_service import load_stock, refresh, refresh_phase2, refresh_phase3, refresh_phase4, refresh_phase5, refresh_phase6
from src.database.db import (connect, read_institutional, read_margin, read_pivots, read_levels, read_structure,
                             read_evidence, read_market_stage, read_snapshots, read_change_events)
from src.services.portfolio_service import load_portfolio, filter_portfolio

STRUCTURE_STATES = {"UPTREND_STRUCTURE": "上升結構", "DOWNTREND_STRUCTURE": "下降結構",
                    "POSSIBLE_BASE": "可能築底", "POSSIBLE_TOP": "可能築頂",
                    "RANGE": "區間整理", "UNCONFIRMED": "尚未確認"}
FACTOR_LABELS = {"price_structure":"價格結構", "rsi":"相對強弱指標", "moving_averages":"移動平均線",
                 "volume":"成交量", "institutional":"三大法人", "margin":"融資",
                 "support_resistance":"支撐／壓力"}
EVIDENCE_STATUS = {"BULLISH":"偏多", "NEUTRAL":"中性", "BEARISH":"偏空", "WARNING":"警示", "INSUFFICIENT_DATA":"資料不足"}
SEVERITY_LABELS = {"INFO":"資訊", "WATCH":"注意", "IMPORTANT":"重要", "CRITICAL":"關鍵"}
STAGE_LABELS = {"A_DOWNTREND":"A｜下降趨勢", "B_EARLY_BASE":"B｜初步築底", "C_BASE_CONFIRMATION":"C｜底部確認",
                "D_UPTREND":"D｜上升趨勢", "E_OVERHEATED":"E｜過熱", "F_HIGH_LEVEL_CORRECTION":"F｜高檔修正",
                "G_STRUCTURE_WEAKENING":"G｜結構轉弱", "TRANSITION":"過渡期", "UNCLASSIFIED":"無法分類"}


def stock_detail():
    settings, holdings, _ = load_config()
    with connect(settings.database):
        pass
    if st.button("← 返回投資組合雷達"):
        st.session_state.view = "portfolio"
        st.rerun()
    st.title("台股技術分析儀表板")
    st.caption("第六階段 · 每日快照、昨日與今日、變化偵測")
    selected_ticker = st.session_state.get("selected_ticker")
    selected_index = next((i for i,item in enumerate(holdings) if item.ticker == selected_ticker), 0)
    holding = st.selectbox("股票", holdings, index=selected_index, format_func=lambda h: f"{h.ticker} {h.name}")
    if st.button("更新市場資料", type="primary"):
        try:
            with st.spinner("取得官方資料、驗證並儲存…"):
                refresh(settings, holding.ticker)
                refresh_phase2(settings, holding.ticker)
                refresh_phase3(settings, holding.ticker)
                refresh_phase4(settings, holding.ticker)
                refresh_phase5(settings, holding.ticker)
                refresh_phase6(settings, holding.ticker)
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
        evidence = read_evidence(db, holding.ticker)
        market_stage = read_market_stage(db, holding.ticker)
        recent_snapshots = read_snapshots(db, holding.ticker, 2)
        latest_events = read_change_events(db, holding.ticker, recent_snapshots[0].market_date) if recent_snapshots else []
    if institutional_count < 250 or margin_count < 250:
        st.warning(f"第二階段資料尚未完成：法人 {institutional_count}/250 日、融資融券 {margin_count}/250 日。請按「更新市場資料」。")
        return
    a, b, c = st.columns(3)
    a.metric(f"{holding.ticker} {holding.name}", f"{latest.close:.2f} 元")
    b.metric("最新交易日", str(latest.market_date))
    c.metric("資料品質", STATUS[quality.status])
    st.caption(f"行情 {len(data)} 日 · 法人 {institutional_count} 日 · 融資融券 {margin_count} 日 · 成交量／法人：股 · 融資融券：交易單位")
    meaningful_events = [item for item in latest_events if item.severity in {"WATCH","IMPORTANT","CRITICAL"}]
    changed_only = st.toggle("只顯示今日有重要變化的持股")
    if changed_only and not meaningful_events:
        st.info("此持股在最新交易日沒有需要注意的重要變化。")
        return
    if len(recent_snapshots) == 2:
        current, previous = recent_snapshots
        st.subheader("昨日與今日")
        st.dataframe({"指標":["市場階段","收盤價","RSI14","成交量比","外資 5 日","投信 5 日","融資 20 日增幅","第一支撐","第一壓力"],
            str(previous.market_date):[STAGE_LABELS[previous.market_stage],previous.close,previous.rsi14,previous.volume_ratio_20,previous.foreign_5d,previous.trust_5d,previous.margin_change_pct_20d,previous.support_1,previous.resistance_1],
            str(current.market_date):[STAGE_LABELS[current.market_stage],current.close,current.rsi14,current.volume_ratio_20,current.foreign_5d,current.trust_5d,current.margin_change_pct_20d,current.support_1,current.resistance_1]}, hide_index=True)
        st.subheader("最新變化")
        if latest_events:
            for item in latest_events:
                st.write(f"**{SEVERITY_LABELS[item.severity]}｜{item.change_type}**　{item.explanation}（{item.previous_value} → {item.current_value}）")
        else:
            st.caption("最新交易日沒有偵測到變化事件。")
    if market_stage:
        st.subheader("市場階段")
        st.markdown(f"### {STAGE_LABELS[market_stage.stage]}")
        for reason in market_stage.reasons:
            st.write(f"• {reason}")
        st.caption("判定依固定規則與優先序產生；市場階段是證據摘要，不是買賣建議。")
    if structure:
        st.subheader("價格結構")
        st.write(f"狀態：**{STRUCTURE_STATES[structure.state]}**　高點證據：{structure.high_label or '—'} {structure.high_pivot_date or '—'} / {structure.high_price or '—'} 元　低點證據：{structure.low_label or '—'} {structure.low_pivot_date or '—'} / {structure.low_price or '—'} 元")
        st.caption(f"Pivot 敏感度：左 {settings.pivot_left_bars} 日／右 {settings.pivot_right_bars} 日；圖上標註轉折日，訊號僅自確認日起可用。")
    if evidence:
        st.subheader("七因素證據矩陣")
        st.caption("各因素獨立呈現，不計算單一買賣分數。")
        order = {name:i for i,name in enumerate(FACTOR_LABELS)}
        evidence = sorted(evidence, key=lambda x: order[x.factor])
        for start in (0, 4):
            columns = st.columns(min(4, len(evidence) - start))
            for column, item in zip(columns, evidence[start:start+4]):
                with column:
                    st.markdown(f"**{FACTOR_LABELS[item.factor]}**　`{EVIDENCE_STATUS[item.status]}`")
                    st.metric(item.headline, item.current_value)
                    st.caption(item.reasoning)
                    with st.expander("檢視證據"):
                        for observation in item.observations:
                            st.json(observation)
                        st.write("來源日期：", "、".join(map(str, item.source_dates)) or "尚無")
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


def portfolio_radar():
    settings, holdings, _ = load_config()
    data = load_portfolio(settings, holdings)
    st.title("投資組合雷達")
    st.caption("第七階段 · 從最新資料庫快照快速找出需要注意的持股；不進行最佳到最差排名。")
    valid = data[data.market_date.notna()]
    latest_date = valid.market_date.max() if not valid.empty else None
    if latest_date is not None and hasattr(latest_date, "date"):
        latest_date = latest_date.date()
    top = st.columns(5)
    top[0].metric("持股數", len(holdings))
    top[1].metric("今日階段變化", int(data.stage_changed.sum()))
    top[2].metric("重要警示", int(data.important_count.sum()))
    top[3].metric("資料品質警告", int((data.quality != "PASS").sum()))
    top[4].metric("最新資料日", str(latest_date) if latest_date else "尚無")
    if valid.empty:
        st.warning("尚無完整分析快照。請先進入個股詳情更新市場資料。")
    a,b,c,d = st.columns([2,2,2,1])
    search = a.text_input("搜尋股票代號或名稱")
    available_stages = sorted(x for x in data.stage.dropna().unique())
    stage_filter = b.multiselect("市場階段", available_stages, format_func=lambda x: STAGE_LABELS.get(x,x))
    alert_filter = c.selectbox("警示篩選", ["全部","有重要警示","有任何變化","資料品質警告"])
    changed_only = d.toggle("只看有變化")
    filtered = filter_portfolio(data, search, stage_filter, alert_filter, changed_only)
    display = filtered.copy()
    display["stock"] = display.ticker + " " + display["name"]
    display["stage_label"] = display.stage.map(lambda x: STAGE_LABELS.get(x,"尚無"))
    display["structure"] = display.structure.map(lambda x: STRUCTURE_STATES.get(x,"尚無"))
    display["changed_label"] = display.changed.map({True:"是",False:"否"})
    columns = {"stock":"股票", "price":"價格", "cost":"成本", "profit_pct":"損益（%）", "stage_label":"市場階段",
        "rsi":"RSI", "structure":"價格結構", "ma":"均線", "foreign_5d":"外資 5 日", "trust_5d":"投信 5 日",
        "margin_20d_pct":"融資 20 日（%）", "key_risk":"主要風險／事件", "changed_label":"有變化"}
    event = st.dataframe(display[list(columns)].rename(columns=columns), hide_index=True, width="stretch",
        on_select="rerun", selection_mode="single-row", key="portfolio_table")
    if event.selection.rows:
        selected = filtered.iloc[event.selection.rows[0]]
        st.session_state.selected_ticker = selected.ticker
        st.session_state.view = "detail"
        st.rerun()
    st.caption(f"顯示 {len(filtered)}／{len(data)} 檔；可點選任一列開啟個股詳情。表格欄位可直接排序。")


def application():
    if "view" not in st.session_state:
        st.session_state.view = "portfolio"
    portfolio_radar() if st.session_state.view == "portfolio" else stock_detail()
