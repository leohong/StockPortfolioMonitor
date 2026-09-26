from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re
import shutil
from threading import Lock
from uuid import uuid4

import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont


_KALEIDO_LOCK = Lock()


class _WorkspaceTmpDirectory:
    """Kaleido temp directory that avoids Windows TemporaryDirectory ACL issues."""

    root: Path

    def __init__(self, path=None, *, sneak=False):
        del sneak
        base = Path(path) if path else self.root
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / f"kaleido-{uuid4().hex}"
        self.path.mkdir()
        self.exists = True

    def clean(self):
        shutil.rmtree(self.path, ignore_errors=True)
        self.exists = self.path.exists()


def _font(size):
    for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/mingliu.ttc")):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _plain(value):
    return re.sub(r"<[^>]+>", "", str(value).replace("<br>", "\n"))


def _pillow_png(figure):
    """Render the same Plotly trace values when Chrome cannot run locally."""
    width, height = 3200, 2200
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    layout = figure.layout

    # Export annotations contain the snapshot, Evidence Cards, events and source.
    for ann in layout.annotations or ():
        if ann.xref != "paper" or ann.yref != "paper":
            continue
        x = int(100 + float(ann.x if ann.x is not None else 0) * 3000)
        y = int(610 - (float(ann.y if ann.y is not None else 1) - 1) * 1450)
        draw.multiline_text((x, max(20, y)), _plain(ann.text), fill="#222222", font=_font(22), spacing=5)

    grouped = {}
    for trace in figure.data:
        axis = getattr(trace, "yaxis", None) or "y"
        grouped.setdefault(axis, []).append(trace)
    panel_height = 1450 / max(1, len(grouped))
    palette = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e")
    for panel_index, (axis, traces) in enumerate(grouped.items()):
        left, right = 130, 3070
        top = int(650 + panel_index * panel_height)
        bottom = int(650 + (panel_index + 1) * panel_height - 25)
        draw.rectangle((left, top, right, bottom), outline="#c7ccd1", width=2)
        values = []
        points = []
        for trace_index, trace in enumerate(traces):
            raw_y = getattr(trace, "y", None)
            if raw_y is None:
                raw_y = getattr(trace, "close", None)
            ys = list(raw_y) if raw_y is not None else []
            numeric = [float(v) for v in ys if v is not None]
            values.extend(numeric)
            points.append((trace, numeric, palette[trace_index % len(palette)]))
        if not values:
            continue
        low, high = min(values), max(values)
        span = high - low or 1
        for trace, ys, color in points:
            if not ys:
                continue
            coords = [(left + i * (right-left) / max(1, len(ys)-1), bottom - (v-low) / span * (bottom-top)) for i,v in enumerate(ys)]
            if trace.type == "bar":
                bar_width = max(2, int((right-left) / max(1, len(ys)) * .6))
                for x,y in coords:
                    draw.rectangle((x-bar_width/2, y, x+bar_width/2, bottom), fill=color)
            else:
                draw.line(coords, fill=color, width=4)
        draw.text((left + 8, top + 5), axis, fill="#555555", font=_font(18))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def snapshot_csv(snapshot, evidence, events, source_url):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["section","field","value","source_dates","source"])
    for field,value in snapshot.model_dump().items():
        writer.writerow(["snapshot",field,value,snapshot.market_date,source_url])
    for item in evidence:
        writer.writerow(["evidence",item.factor,json.dumps({"status":item.status,"headline":item.headline,
            "current_value":item.current_value,"observations":item.observations,"reasoning":item.reasoning},ensure_ascii=False,default=str),
            "|".join(map(str,item.source_dates)),source_url])
    for item in events:
        writer.writerow(["event",item.change_type,json.dumps({"severity":item.severity,"previous":item.previous_value,
            "current":item.current_value,"explanation":item.explanation},ensure_ascii=False),item.market_date,source_url])
    return output.getvalue().encode("utf-8-sig")


def v3_snapshot_csv(snapshot,events,scenarios):
    output=io.StringIO(); writer=csv.writer(output); writer.writerow(["section","field","value","market_date"])
    day=snapshot["market_date"]
    for field,value in snapshot["payload"].items():
        writer.writerow(["v3_snapshot",field,json.dumps(value,ensure_ascii=False,default=str) if isinstance(value,(dict,list)) else value,day])
    for event in events: writer.writerow(["significant_event",event["dimension"],f"{event['previous_state']} -> {event['current_state']} [{event['significance']}]",day])
    for scenario in scenarios: writer.writerow(["scenario",scenario["scenario_type"],json.dumps(scenario,ensure_ascii=False,default=str),day])
    return output.getvalue().encode("utf-8-sig")


def export_figure(figure, snapshot, evidence, events, source_url):
    result = go.Figure(figure)
    factor_labels={"price_structure":"價格結構","rsi":"RSI","moving_averages":"移動平均","volume":"成交量","institutional":"三大法人","margin":"融資","support_resistance":"支撐／壓力"}
    status_labels={"BULLISH":"偏多","NEUTRAL":"中性","BEARISH":"偏空","WARNING":"警示","INSUFFICIENT_DATA":"資料不足"}
    colors={"BULLISH":"#dff3e4","NEUTRAL":"#eef1f4","BEARISH":"#f8dddd","WARNING":"#fff0c7","INSUFFICIENT_DATA":"#eeeeee"}
    event_text = "；".join(f"{item.severity} {item.change_type}" for item in events) or "無"
    header=(f"<b>{snapshot.ticker}｜{snapshot.market_date}｜市場階段 {snapshot.market_stage}</b>　"
        f"收盤 {snapshot.close:.2f}｜支撐 {snapshot.support_1 or '—'} / {snapshot.support_2 or '—'}｜壓力 {snapshot.resistance_1 or '—'} / {snapshot.resistance_2 or '—'}")
    result.add_annotation(x=0,y=1.38,xref="paper",yref="paper",xanchor="left",yanchor="middle",
        text=header,showarrow=False,align="left",font=dict(size=28,color="#222"))
    for index,item in enumerate(evidence):
        row,col=divmod(index,4); x=(col+.5)/4; y=1.27-row*.13
        text=(f"<b>{factor_labels[item.factor]}｜{status_labels[item.status]}</b><br>{item.headline}<br>"
              f"{item.current_value}｜來源 {'、'.join(map(str,item.source_dates)) or '尚無'}")
        result.add_annotation(x=x,y=y,xref="paper",yref="paper",xanchor="center",yanchor="middle",
            text=text,showarrow=False,align="left",width=650,bgcolor=colors[item.status],bordercolor="#aab2bb",borderwidth=1,borderpad=10,font=dict(size=17,color="#222"))
    footer=f"<b>重要事件：</b>{event_text}<br><b>官方來源：</b>{source_url}｜快照建立：{snapshot.created_at}"
    result.add_annotation(x=0,y=1.01,xref="paper",yref="paper",xanchor="left",yanchor="bottom",text=footer,showarrow=False,align="left",font=dict(size=16,color="#333"))
    result.update_layout(width=3200,height=2200,margin=dict(l=100,r=100,t=620,b=80),paper_bgcolor="white",plot_bgcolor="white")
    return result


def snapshot_png(figure, snapshot, evidence, events, source_url):
    export = export_figure(figure,snapshot,evidence,events,source_url)
    export_temp = Path(__file__).resolve().parents[2] / "data" / "export_tmp"
    export_temp.mkdir(parents=True,exist_ok=True)
    _WorkspaceTmpDirectory.root = export_temp

    # Kaleido and Choreographer import this helper into separate modules. Patch
    # both references for the duration of the synchronous render so Chrome's
    # profile and HTML remain in the project's writable data directory.
    import kaleido.kaleido as kaleido_module
    import choreographer.browsers.chromium as chromium_module

    with _KALEIDO_LOCK:
        original_kaleido_tmp = kaleido_module.TmpDirectory
        original_chromium_tmp = chromium_module.TmpDirectory
        kaleido_module.TmpDirectory = _WorkspaceTmpDirectory
        chromium_module.TmpDirectory = _WorkspaceTmpDirectory
        try:
            try:
                return export.to_image(format="png",width=3200,height=2200,scale=1)
            except Exception:
                return _pillow_png(export)
        finally:
            kaleido_module.TmpDirectory = original_kaleido_tmp
            chromium_module.TmpDirectory = original_chromium_tmp
