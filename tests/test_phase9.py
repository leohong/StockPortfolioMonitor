import csv
import io
from datetime import date,datetime,timezone

from PIL import Image
import plotly.graph_objects as go

from src.models import AnalysisSnapshot,Evidence,ChangeEvent
from src.services.export_service import snapshot_csv,snapshot_png,export_figure


def objects():
    snapshot=AnalysisSnapshot(ticker="3702",market_date=date(2026,9,24),close=117.5,market_stage="TRANSITION",
        structure_state="DOWNTREND_STRUCTURE",support_1=114,resistance_1=119.5,bullish_evidence_count=1,
        bearish_evidence_count=1,warning_count=1,data_quality_status="PASS",created_at=datetime(2026,9,25,tzinfo=timezone.utc))
    evidence=[Evidence(ticker="3702",market_date=date(2026,9,24),factor="rsi",status="BULLISH",headline="RSI 強勢",
        current_value="64.07",observations=[{"metric":"rsi14","value":64.07}],reasoning="Wilder RSI14",
        source_dates=[date(2026,9,24)],updated_at=datetime(2026,9,25,tzinfo=timezone.utc))]
    events=[ChangeEvent(ticker="3702",market_date=date(2026,9,24),change_type="RESISTANCE_BROKEN",severity="IMPORTANT",
        previous_value="114",current_value="117.5",explanation="突破壓力")]
    return snapshot,evidence,events


def test_csv_uses_exact_snapshot_evidence_events_and_source():
    snapshot,evidence,events=objects(); source="https://www.twse.com.tw/source"
    rows=list(csv.DictReader(io.StringIO(snapshot_csv(snapshot,evidence,events,source).decode("utf-8-sig"))))
    assert next(x for x in rows if x["field"]=="close")["value"]=="117.5"
    assert next(x for x in rows if x["section"]=="evidence")["source_dates"]=="2026-09-24"
    assert next(x for x in rows if x["section"]=="event")["field"]=="RESISTANCE_BROKEN"
    assert all(x["source"]==source for x in rows)


def test_export_figure_preserves_chart_values_and_adds_metadata():
    snapshot,evidence,events=objects(); original=go.Figure(go.Scatter(x=[1,2],y=[3.25,4.5],name="real"))
    exported=export_figure(original,snapshot,evidence,events,"https://www.twse.com.tw/source")
    assert list(exported.data[0].y)==[3.25,4.5]
    assert exported.layout.width==3200 and exported.layout.height==2200
    texts="\n".join(item.text for item in exported.layout.annotations)
    assert "2026-09-24" in texts
    assert "www.twse.com.tw" in texts
    assert len(exported.layout.annotations)==len(evidence)+2


def test_png_is_high_resolution_and_not_fabricated():
    snapshot,evidence,events=objects(); figure=go.Figure(go.Scatter(x=[1,2],y=[3.25,4.5]))
    image=Image.open(io.BytesIO(snapshot_png(figure,snapshot,evidence,events,"https://www.twse.com.tw/source")))
    assert image.size==(3200,2200)
