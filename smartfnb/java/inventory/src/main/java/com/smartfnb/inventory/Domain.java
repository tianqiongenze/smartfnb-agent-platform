package com.smartfnb.inventory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** 纯领域逻辑(无框架依赖): 理论用量计算 + 差异预警规则 —— TDD/BDD 评审重点 */
public final class Domain {
    private Domain() {}

    public static final double ALERT_THRESHOLD_PCT = 15.0;

    /** 理论用量 = Σ 销售数量 × BOM标准克重 */
    public static Map<Integer, Double> theoretical(List<Model.DiffLine> ignore, Map<Integer, List<int[]>> bomByDish,
                                                   Map<Integer, Double> salesQtyByDish) {
        Map<Integer, Double> out = new HashMap<>();
        salesQtyByDish.forEach((dishId, qty) -> {
            List<int[]> bom = bomByDish.get(dishId);
            if (bom == null) return;                    // 无BOM菜品不计入(进数据质量看板)
            for (int[] ing : bom) out.merge(ing[0], qty * ing[1], Double::sum);
        });
        return out;
    }

    /** 差异率 = (实际-理论)/理论 × 100, 理论为0时有消耗视为异常 */
    public static Double diffPct(double theo, double actual) {
        if (theo <= 0) return actual > 0 ? Double.POSITIVE_INFINITY : null;
        return round1((actual - theo) / theo * 100.0);
    }

    /** 预警规则: |差异|>15% 告警; >=30% 为HIGH (BDD: 高价值食材用量差异预警) */
    public static String level(Double diffPct) {
        if (diffPct == null) return null;
        double d = Math.abs(diffPct);
        if (d <= ALERT_THRESHOLD_PCT) return null;
        return d >= 30.0 ? "HIGH" : "MEDIUM";
    }

    private static double round1(double v) { return Math.round(v * 10.0) / 10.0; }
}
