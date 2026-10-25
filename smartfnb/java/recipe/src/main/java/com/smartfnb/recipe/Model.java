package com.smartfnb.recipe;

/** 领域模型(记录类型, 不可变值对象) */
public final class Model {
    private Model() {}

    public record Store(Integer storeId, String name, String city, Integer areaM2) {}

    public record Unit(String unitCode, String unitName, double ratioToGram) {}

    /** 值对象: 带单位的数量, 单位换算必须在领域层完成(反P7: 单位混乱教训) */
    public record Quantity(double value, String unitCode) {
        public double toBaseGram(double ratio) {
            if (ratio <= 0) throw new IllegalArgumentException("非法单位系数: " + unitCode);
            return value * ratio;
        }
    }

    public record Ingredient(Integer ingId, String ingCode, String nameStd, String category,
                             String baseUnit, Double boxRatio, String aliases, Double refPrice) {}

    public record Dish(Integer dishId, String name, String category, Double price) {}

    public record BomItem(Integer dishId, Integer ingId, double gramsPerServing) {}
}
