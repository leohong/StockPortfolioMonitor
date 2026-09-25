"""Compare ten evenly distributed DuckDB rows with archived official responses."""
from src.config import load_config
from src.data.phase2_normalizer import normalize_institutional, normalize_margin
from src.database.db import connect, read_institutional, read_margin
from src.data.providers.twse_phase2 import fetch_daily


def main():
    settings, _, _ = load_config()
    with connect(settings.database) as db:
        institutional = read_institutional(db, "3702")
        margin = read_margin(db, "3702")
    dates = [row.market_date for row in institutional]
    chosen = [dates[round(index * (len(dates) - 1) / 9)] for index in range(10)]
    inst_db = {row.market_date: row for row in institutional}
    margin_db = {row.market_date: row for row in margin}
    print("date,foreign,trust,dealer,total,margin_buy,margin_sell,margin_repay,margin_balance,short_sell,short_cover,short_repay,short_balance")
    for market_date in chosen:
        raw_inst = normalize_institutional("3702", market_date, fetch_daily("institutional", market_date, settings.cache_dir))
        raw_margin = normalize_margin("3702", market_date, fetch_daily("margin", market_date, settings.cache_dir))
        assert raw_inst == inst_db[market_date]
        assert raw_margin == margin_db[market_date]
        print(",".join(map(str, [market_date, raw_inst.foreign_net, raw_inst.investment_trust_net,
            raw_inst.dealer_net, raw_inst.institutional_total_net, raw_margin.margin_buy,
            raw_margin.margin_sell, raw_margin.margin_cash_repayment, raw_margin.margin_balance,
            raw_margin.short_sell, raw_margin.short_cover, raw_margin.short_stock_repayment,
            raw_margin.short_balance])))


if __name__ == "__main__":
    main()
