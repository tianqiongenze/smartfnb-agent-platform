package com.smartfnb.inventory;

import java.util.List;
import java.util.Map;

/** 领域模型 */
public final class Model {
    private Model() {}

    public record MovementCmd(Integer storeId, Integer ingId, String movementType,
                              double qty, String unitCode, String refNo) {}

    /** 值对象: 克为基准的数量(反P7: 所有入库数据强制过单位字典) */
    public record Gram(double value) {
        public Gram {
            if (value < 0) throw new IllegalArgumentException("克数不能为负: " + value);
        }
    }

    public record DiffLine(Integer ingId, String ingCode, String ingName, String category,
                           double theoGram, double actualGram, Double diffPct, String level) {}

    public record Alert(String id, String diffDate, Integer storeId, Integer ingId,
                        String ingName, Double theoGram, Double actualGram, Double diffPct,
                        String level, String status) {}
}
