package com.smartfnb.recipe;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/** MDM数据质量门禁报表(Phase1): 读取 quality_check 工具落库的质量报告 */
@RestController
@RequestMapping("/api/quality")
public class QualityApi {

    private final JdbcTemplate jdbc;

    public QualityApi(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @GetMapping("/latest")
    public Map<String, Object> latest() {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT run_id AS runId, checked_at AS checkedAt, rule_name AS ruleName,
                   status, metric, detail
            FROM quality_report
            WHERE run_id = (SELECT run_id FROM quality_report ORDER BY checked_at DESC LIMIT 1)
            ORDER BY rule_name""");
        String verdict = rows.stream().allMatch(r -> "PASS".equals(r.get("status"))) ? "PASS" : "FAIL";
        return Map.of("verdict", verdict, "rules", rows);
    }

    @GetMapping("/history")
    public List<Map<String, Object>> history(@RequestParam(defaultValue = "10") int limit) {
        return jdbc.queryForList("""
            SELECT run_id AS runId, checked_at AS checkedAt,
                   SUM(status='FAIL') AS failCnt, COUNT(*) AS total
            FROM quality_report GROUP BY run_id, checked_at
            ORDER BY checked_at DESC LIMIT ?""", Math.min(limit, 50));
    }
}
