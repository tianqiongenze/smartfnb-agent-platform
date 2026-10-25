package com.smartfnb.inventory;

import org.springframework.web.bind.annotation.*;

import java.sql.Date;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api")
public class Api {

    private final Repo repo;

    public Api(Repo repo) { this.repo = repo; }

    /** 领料/收货/废弃登记(PDA扫码入口): 单位强制过字典换算为克 */
    @PostMapping("/stock-movements")
    public Map<String, Object> ingest(@RequestBody Model.MovementCmd cmd) {
        if (!List.of("receive", "consume", "waste", "transfer_out").contains(cmd.movementType())) {
            throw new IllegalArgumentException("非法movementType: " + cmd.movementType());
        }
        Map<String, Object> unit = repo.unit(cmd.unitCode());
        double ratio = ((Number) unit.get("ratio_to_gram")).doubleValue();
        if (ratio <= 0) throw new IllegalArgumentException("箱装单位必须映射到具体食材箱规");
        double gram = new Model.Gram(cmd.qty() * ratio).value();
        String refNo = cmd.refNo() == null ? UUID.randomUUID().toString().substring(0, 8) : cmd.refNo();
        repo.insertMovement(cmd, gram, refNo);
        return Map.of("ok", true, "qtyBaseGram", gram, "refNo", refNo);
    }

    /** 差异报表(T+1): 理论 vs 实际, 按|差异|降序 */
    @GetMapping("/diff")
    public List<Map<String, Object>> diff(@RequestParam String date,
                                          @RequestParam(required = false) Integer storeId,
                                          @RequestParam(defaultValue = "100") int limit) {
        return repo.diff(LocalDate.parse(date), storeId, Math.min(limit, 500));
    }

    /** 计算当日预警(幂等), 由 CronJob 每日 07:30 调用 */
    @PostMapping("/alerts/compute")
    public Map<String, Object> compute(@RequestParam String date) {
        int n = repo.computeAlerts(LocalDate.parse(date));
        return Map.of("date", date, "upserted", n);
    }

    /** 账外领用检查(R2): 有消耗无理论→HIGH */
    @PostMapping("/alerts/orphan-check")
    public Map<String, Object> orphan(@RequestParam String date, @RequestParam int storeId) {
        int n = repo.computeOrphanAlerts(LocalDate.parse(date), storeId);
        return Map.of("date", date, "storeId", storeId, "orphans", n);
    }

    /** 单店日预警计算(R2: 事件消费者调用, 秒级) */
    @PostMapping("/alerts/compute-store")
    public Map<String, Object> computeStore(@RequestParam String date, @RequestParam int storeId) {
        int n = repo.computeAlertsForStore(LocalDate.parse(date), storeId);
        return Map.of("date", date, "storeId", storeId, "upserted", n);
    }

    @GetMapping("/alerts")
    public List<Map<String, Object>> alerts(@RequestParam String date,
                                            @RequestParam(required = false) Integer storeId) {
        return repo.alerts(LocalDate.parse(date), storeId);
    }

    @PostMapping("/alerts/{id}/ack")
    public Map<String, Object> ack(@PathVariable long id) {
        repo.ack(id);
        return Map.of("ok", true, "id", id);
    }
}
