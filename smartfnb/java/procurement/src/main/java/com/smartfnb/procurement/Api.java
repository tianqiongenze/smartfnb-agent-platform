package com.smartfnb.procurement;

import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** 采购域API(Phase2): 比价 / 建议单(人在环: DRAFT→APPROVED/REJECTED) */
@RestController
@RequestMapping("/api")
public class Api {

    private final Repo repo;

    public Api(Repo repo) { this.repo = repo; }

    @GetMapping("/suppliers")
    public List<Map<String, Object>> suppliers() { return repo.suppliers(); }

    @GetMapping("/price-compare")
    public List<Map<String, Object>> priceCompare(@RequestParam int ingId,
                                                  @RequestParam(defaultValue = "90") int days) {
        return repo.priceCompare(ingId, Math.min(days, 365));
    }

    /** 生成建议单: 由采购建议Agent或人工调用, 默认DRAFT等待审批(人在环, 防AI越权) */
    @PostMapping("/suggestions")
    public Map<String, Object> create(@RequestBody Map<String, Object> body) {
        int storeId = ((Number) body.get("storeId")).intValue();
        int ingId = ((Number) body.get("ingId")).intValue();
        double qty = ((Number) body.get("qty")).doubleValue();
        String unitCode = String.valueOf(body.getOrDefault("unitCode", "kg"));
        Long supId = body.get("supId") == null ? null : ((Number) body.get("supId")).longValue();
        Double estPrice = body.get("estPrice") == null ? null : ((Number) body.get("estPrice")).doubleValue();
        String reason = String.valueOf(body.getOrDefault("reason", ""));
        return repo.createSuggestion(storeId, ingId, qty, unitCode, supId, estPrice, reason);
    }

    @GetMapping("/suggestions")
    public List<Map<String, Object>> suggestions(@RequestParam(defaultValue = "DRAFT") String status,
                                                 @RequestParam(required = false) Integer storeId) {
        return repo.suggestions(status, storeId);
    }

    @PostMapping("/suggestions/{id}/approve")
    public Map<String, Object> approve(@PathVariable long id,
                                       @RequestParam(defaultValue = "buyer") String by) {
        int n = repo.decide(id, "APPROVED", by);
        if (n == 0) throw new IllegalArgumentException("建议单不存在或已处理: " + id);
        return Map.of("ok", true, "id", id, "status", "APPROVED");
    }

    @PostMapping("/suggestions/{id}/reject")
    public Map<String, Object> reject(@PathVariable long id,
                                      @RequestParam(defaultValue = "buyer") String by) {
        int n = repo.decide(id, "REJECTED", by);
        if (n == 0) throw new IllegalArgumentException("建议单不存在或已处理: " + id);
        return Map.of("ok", true, "id", id, "status", "REJECTED");
    }
}
