package com.smartfnb.recipe;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** TDD: 单位换算领域规则(反P7: 克/斤/箱混乱教训的领域级防线) */
class UnitConverterTest {

    @Test
    @DisplayName("1斤=500克, 1千克=1000克")
    void basicConversion() {
        assertEquals(500.0, new Model.Quantity(1, "jin").toBaseGram(500), 0.001);
        assertEquals(1000.0, new Model.Quantity(1, "kg").toBaseGram(1000), 0.001);
        assertEquals(50.0, new Model.Quantity(1, "liang").toBaseGram(50), 0.001);
    }

    @Test
    @DisplayName("2.5斤=1250克")
    void fractionalJin() {
        assertEquals(1250.0, new Model.Quantity(2.5, "jin").toBaseGram(500), 0.001);
    }

    @Test
    @DisplayName("箱装按一品一码的箱规换算")
    void boxByIngredientRule() {
        assertEquals(15000.0, new Model.Quantity(1, "box").toBaseGram(15000), 0.001);
    }

    @Test
    @DisplayName("非法单位系数必须抛异常(禁止静默错算)")
    void illegalRatioThrows() {
        assertThrows(IllegalArgumentException.class,
                () -> new Model.Quantity(3, "box").toBaseGram(0));
        assertThrows(IllegalArgumentException.class,
                () -> new Model.Quantity(3, "box").toBaseGram(-1));
    }
}
