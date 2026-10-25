package com.smartfnb.inventory;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** TDD: 差异计算与预警规则 —— 对应 contracts/features/usage-diff.feature */
class DiffCalculatorTest {

    @Test
    @DisplayName("理论用量 = Σ 销售数量×BOM克重 (58份黑椒牛柳×150克=8700克)")
    void theoreticalFromSalesAndBom() {
        Map<Integer, Double> sales = Map.of(101, 58.0);          // dish 101 卖58份
        Map<Integer, List<int[]>> bom = Map.of(101, List.of(new int[]{1, 150})); // 牛肉150g/份
        Map<Integer, Double> theo = Domain.theoretical(null, bom, sales);
        assertEquals(8700.0, theo.get(1), 0.001);
    }

    @Test
    @DisplayName("领料12.8公斤 vs 理论8.7公斤 → 差异+47.1%, 触发HIGH预警")
    void highDiffTriggersAlert() {
        Double pct = Domain.diffPct(8700, 12800);
        assertEquals(47.1, pct, 0.1);
        assertEquals("HIGH", Domain.level(pct));
    }

    @Test
    @DisplayName("实际8.0公斤 vs 理论8.7公斤 → 差异-8.0%, 不触发预警")
    void smallDiffNoAlert() {
        Double pct = Domain.diffPct(8700, 8000);
        assertEquals(-8.0, pct, 0.1);
        assertNull(Domain.level(pct));
    }

    @Test
    @DisplayName("无销售但记录了消耗 → 差异无穷大, 判HIGH(疑似账外领用)")
    void consumptionWithoutSales() {
        Double pct = Domain.diffPct(0, 5000);
        assertEquals(Double.POSITIVE_INFINITY, pct);
        assertEquals("HIGH", Domain.level(pct));
    }

    @Test
    @DisplayName("边界: 恰好15.0%不告警, 15.1%告警MEDIUM")
    void thresholdBoundary() {
        assertNull(Domain.level(15.0));
        assertNull(Domain.level(-15.0));
        assertEquals("MEDIUM", Domain.level(15.1));
        assertEquals("MEDIUM", Domain.level(-15.1));
    }

    @Test
    @DisplayName("负克数的数量对象必须抛异常(值对象不变式)")
    void negativeGramRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Model.Gram(-1));
    }
}
