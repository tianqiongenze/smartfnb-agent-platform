package com.smartfnb.inventory;

import org.springframework.web.bind.annotation.*;

import java.time.YearMonth;
import java.util.List;
import java.util.Map;

/** 浪费月报(Phase2): 废弃量 vs 理论用量, 按门店/品类汇总 — Go标准: 浪费率相对基线下降≥10% */
@RestController
@RequestMapping("/api/reports")
public class ReportApi {

    private final Repo repo;

    public ReportApi(Repo repo) { this.repo = repo; }

    /** 月度浪费报告: month=YYYY-MM; 基线=上月。返回按门店的浪费公斤与浪费率(废弃/理论) */
    @GetMapping("/waste-monthly")
    public Map<String, Object> wasteMonthly(@RequestParam String month) {
        YearMonth cur = YearMonth.parse(month);
        YearMonth prev = cur.minusMonths(1);
        List<Map<String, Object>> rows = repo.monthlyWaste(cur.atDay(1), cur.atEndOfMonth());
        List<Map<String, Object>> base = repo.monthlyWaste(prev.atDay(1), prev.atEndOfMonth());
        double curRate = rate(rows), baseRate = rate(base);
        double drop = baseRate == 0 ? 0 : round1((baseRate - curRate) / baseRate * 100);
        return Map.of(
                "month", month,
                "baselineMonth", prev.toString(),
                "currentWasteRatePct", curRate,
                "baselineWasteRatePct", baseRate,
                "improvementPct", drop,
                "targetPct", 10.0,
                "goStandardMet", drop >= 10.0,
                "byStore", rows);
    }

    private double rate(List<Map<String, Object>> rows) {
        double waste = 0, theo = 0;
        for (Map<String, Object> r : rows) {
            waste += ((Number) r.getOrDefault("wasteKg", 0)).doubleValue();
            theo += ((Number) r.getOrDefault("theoKg", 0)).doubleValue();
        }
        return theo == 0 ? 0 : round1(waste / theo * 100);
    }

    private double round1(double v) { return Math.round(v * 10.0) / 10.0; }
}
