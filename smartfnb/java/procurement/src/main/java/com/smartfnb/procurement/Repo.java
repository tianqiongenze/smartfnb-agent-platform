package com.smartfnb.procurement;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Repository
public class Repo {

    private final JdbcTemplate read, write;

    public Repo(@Qualifier("readJdbc") JdbcTemplate read, @Qualifier("writeJdbc") JdbcTemplate write) {
        this.read = read; this.write = write;
    }

    public List<Map<String, Object>> suppliers() {
        return read.queryForList("""
            SELECT sup_id AS supId, name, category, rating FROM supplier ORDER BY rating DESC""");
    }

    /** 近N天各供应商对某食材的实际成交均价与次数(采购历史比价, SQL可溯源) */
    public List<Map<String, Object>> priceCompare(int ingId, int days) {
        return read.queryForList("""
            SELECT po.sup_id AS supId, s.name AS supName, s.rating,
                   ROUND(AVG(pi.unit_price),2) AS avgPrice, COUNT(*) AS dealCnt
            FROM purchase_item pi
            JOIN purchase_order po ON po.po_id = pi.po_id
            JOIN supplier s ON s.sup_id = po.sup_id
            WHERE pi.ing_id = ? AND po.order_date >= ?
            GROUP BY po.sup_id, s.name, s.rating
            ORDER BY avgPrice ASC""", ingId, LocalDate.now().minusDays(days));
    }

    /** 生成采购建议单(DRAFT, 人在环) — 双副本防碰撞的应用侧ID */
    public Map<String, Object> createSuggestion(int storeId, int ingId, double qty, String unitCode,
                                                Long supId, Double estPrice, String reason) {
        long id = (System.currentTimeMillis() << 10)
                | java.util.concurrent.ThreadLocalRandom.current().nextLong(1024);
        write.update("""
            INSERT INTO po_suggestion (id, store_id, ing_id, sug_date, suggest_qty, unit_code,
                                       sup_id, est_price, reason, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,'DRAFT',?)""",
                id, storeId, ingId, LocalDate.now(), qty, unitCode,
                supId, estPrice, reason, new Timestamp(System.currentTimeMillis()));
        return Map.of("id", String.valueOf(id), "status", "DRAFT");
    }

    public List<Map<String, Object>> suggestions(String status, Integer storeId) {
        String base = """
            SELECT g.id, g.store_id AS storeId, g.ing_id AS ingId, i.name_std AS ingName,
                   g.sug_date AS sugDate, g.suggest_qty AS suggestQty, g.unit_code AS unitCode,
                   g.sup_id AS supId, s.name AS supName, g.est_price AS estPrice,
                   g.reason, g.status, g.created_at AS createdAt, g.decided_at AS decidedAt
            FROM po_suggestion g
            JOIN ingredient i ON i.ing_id = g.ing_id
            LEFT JOIN supplier s ON s.sup_id = g.sup_id
            WHERE g.status = ? %s ORDER BY g.created_at DESC LIMIT 100"""
                .formatted(storeId == null ? "" : "AND g.store_id = ?");
        return storeId == null
                ? read.queryForList(base, status)
                : read.queryForList(base, status, storeId);
    }

    public int decide(long id, String status, String by) {
        return write.update(
                "UPDATE po_suggestion SET status=?, decided_by=?, decided_at=NOW() WHERE id=? AND status='DRAFT'",
                status, by, id);
    }
}
