package com.smartfnb.inventory;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Repository
public class Repo {

    private final JdbcTemplate read, write;
    private final EventPublisher events;

    public Repo(@Qualifier("readJdbc") JdbcTemplate read, @Qualifier("writeJdbc") JdbcTemplate write,
                EventPublisher events) {
        this.read = read; this.write = write; this.events = events;
    }

    public Map<String, Object> unit(String code) {
        return read.queryForMap("SELECT unit_code, ratio_to_gram FROM unit_dict WHERE unit_code=?", code);
    }

    public void insertMovement(Model.MovementCmd cmd, double gram, String refNo) {
        // mov_id 应用侧生成(时间戳<<10 | 随机10bit): DDL无自增, 双副本防碰撞
        long movId = (System.currentTimeMillis() << 10)
                | java.util.concurrent.ThreadLocalRandom.current().nextLong(1024);
        write.update("""
                INSERT INTO stock_movement (mov_id, store_id, ing_id, movement_date, movement_type,
                qty_base_gram, ref_no, created_at) VALUES (?,?,?,?,?,?,?,?)""",
                movId, cmd.storeId(), cmd.ingId(), LocalDate.now(), cmd.movementType(),
                (long) gram, refNo, new Timestamp(System.currentTimeMillis()));
        events.publishMovementCreated(cmd.storeId(), cmd.ingId(), LocalDate.now().toString(), gram);
    }

    private static final String ORPHAN_SQL = """
            INSERT INTO alert (diff_date, store_id, ing_id, theo_gram, actual_gram, diff_pct, level)
            SELECT ?, sm.store_id, sm.ing_id, 0, sm.act, 999.9, 'HIGH'
            FROM (SELECT store_id, ing_id, SUM(qty_base_gram) act
                  FROM stock_movement
                  WHERE movement_date = ? AND store_id = ? AND movement_type='consume'
                  GROUP BY store_id, ing_id) sm
            LEFT JOIN (SELECT sl.store_id, b.ing_id,
                              ROUND(SUM(sl.qty*b.grams_per_serving)) theo
                       FROM sales_line sl JOIN bom b ON sl.dish_id=b.dish_id
                       WHERE sl.order_date = ? AND sl.store_id = ?
                       GROUP BY sl.store_id, b.ing_id) t
              ON t.store_id=sm.store_id AND t.ing_id=sm.ing_id
            WHERE sm.act > 0 AND (t.theo IS NULL OR t.theo = 0)
            ON DUPLICATE KEY UPDATE theo_gram=0, actual_gram=VALUES(actual_gram),
                                    diff_pct=999.9, level='HIGH'""";

    /** 账外领用检查(R2): 有消耗无理论 → HIGH 999.9(BDD: 无销售但记录了消耗) */
    public int computeOrphanAlerts(LocalDate date, int storeId) {
        Integer n = write.execute((java.sql.Connection con) -> {
            try (var ps = con.prepareStatement(ORPHAN_SQL)) {
                java.sql.Date d = java.sql.Date.valueOf(date);
                ps.setDate(1, d); ps.setDate(2, d); ps.setInt(3, storeId);
                ps.setDate(4, d); ps.setInt(5, storeId);
                return ps.executeUpdate();
            }
        });
        return n == null ? 0 : n;
    }

    /** 单店日预警计算(R2事件驱动入口, 复用ALERT_ONE_STORE, 幂等) */
    public int computeAlertsForStore(LocalDate date, int storeId) {
        Integer n = write.execute((java.sql.Connection con) -> {
            try (var ps = con.prepareStatement(ALERT_ONE_STORE)) {
                java.sql.Date d = java.sql.Date.valueOf(date);
                ps.setDate(1, d); ps.setInt(2, storeId);
                ps.setDate(3, d); ps.setInt(4, storeId);
                ps.setDate(5, d);
                return ps.executeUpdate();
            }
        });
        return n == null ? 0 : n;
    }

    /**
     * 差异查询(显式谓词下推SQL, 不走视图: TiDB v8.5 对两级聚合视图的外层过滤不下推,
     * 会全表聚合49M行导致实例内存超限8176)。单店日聚合走 (date,store) 索引, 毫秒级。
     */
    public List<Map<String, Object>> diff(LocalDate date, Integer storeId, int limit) {
        String sql;
        Object[] args;
        if (storeId == null) {
            sql = """
                SELECT t.d AS diffDate, t.store_id AS storeId, t.ing_id AS ingId, i.ing_code AS ingCode,
                       i.name_std AS ingName, i.category,
                       CASE WHEN ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) >= 30 THEN 'HIGH' WHEN ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) > 15 THEN 'MEDIUM' END AS level,
                       t.theo_gram AS theoGram, COALESCE(a.actual_gram,0) AS actualGram,
                       ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1) AS diffPct
                FROM (
                  SELECT sl.order_date d, sl.store_id, b.ing_id,
                         ROUND(SUM(sl.qty*b.grams_per_serving)) theo_gram
                  FROM sales_line sl JOIN bom b ON sl.dish_id=b.dish_id
                  WHERE sl.order_date = ?
                  GROUP BY sl.order_date, sl.store_id, b.ing_id
                ) t
                LEFT JOIN (
                  SELECT movement_date d, store_id, ing_id, SUM(qty_base_gram) actual_gram
                  FROM stock_movement
                  WHERE movement_type='consume' AND movement_date = ?
                  GROUP BY movement_date, store_id, ing_id
                ) a ON t.d=a.d AND t.store_id=a.store_id AND t.ing_id=a.ing_id
                JOIN ingredient i ON i.ing_id=t.ing_id
                ORDER BY ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) DESC
                LIMIT ?""";
            args = new Object[]{java.sql.Date.valueOf(date), java.sql.Date.valueOf(date), limit};
        } else {
            sql = """
                SELECT t.d AS diffDate, t.store_id AS storeId, t.ing_id AS ingId, i.ing_code AS ingCode,
                       i.name_std AS ingName, i.category,
                       CASE WHEN ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) >= 30 THEN 'HIGH' WHEN ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) > 15 THEN 'MEDIUM' END AS level,
                       t.theo_gram AS theoGram, COALESCE(a.actual_gram,0) AS actualGram,
                       ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1) AS diffPct
                FROM (
                  SELECT sl.order_date d, sl.store_id, b.ing_id,
                         ROUND(SUM(sl.qty*b.grams_per_serving)) theo_gram
                  FROM sales_line sl JOIN bom b ON sl.dish_id=b.dish_id
                  WHERE sl.order_date = ? AND sl.store_id = ?
                  GROUP BY sl.order_date, sl.store_id, b.ing_id
                ) t
                LEFT JOIN (
                  SELECT movement_date d, store_id, ing_id, SUM(qty_base_gram) actual_gram
                  FROM stock_movement
                  WHERE movement_type='consume' AND movement_date = ? AND stock_movement.store_id = ?
                  GROUP BY movement_date, store_id, ing_id
                ) a ON t.d=a.d AND t.store_id=a.store_id AND t.ing_id=a.ing_id
                JOIN ingredient i ON i.ing_id=t.ing_id
                ORDER BY ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) DESC
                LIMIT ?""";
            args = new Object[]{java.sql.Date.valueOf(date), storeId,
                                java.sql.Date.valueOf(date), storeId, limit};
        }
        return read.queryForList(sql, args);
    }

    public List<Map<String, Object>> alerts(LocalDate date, Integer storeId) {
        String base = """
            SELECT a.id, a.diff_date AS diffDate, a.store_id AS storeId, a.ing_id AS ingId,
                   i.name_std AS ingName, a.theo_gram AS theoGram, a.actual_gram AS actualGram,
                   a.diff_pct AS diffPct, a.level, a.status
            FROM alert a JOIN ingredient i ON i.ing_id = a.ing_id
            WHERE a.diff_date = ? %s ORDER BY ABS(a.diff_pct) DESC LIMIT 300""".formatted(storeId == null ? "" : "AND a.store_id = ?");
        return storeId == null
                ? read.queryForList(base, java.sql.Date.valueOf(date))
                : read.queryForList(base, java.sql.Date.valueOf(date), storeId);
    }

    private static final String ALERT_ONE_STORE = """
            INSERT INTO alert (diff_date, store_id, ing_id, theo_gram, actual_gram, diff_pct, level)
            WITH t AS (
              SELECT sl.store_id, b.ing_id,
                     ROUND(SUM(sl.qty*b.grams_per_serving)) theo_gram
              FROM sales_line sl JOIN bom b ON sl.dish_id=b.dish_id
              WHERE sl.order_date = ? AND sl.store_id = ?
              GROUP BY sl.store_id, b.ing_id
            ), a AS (
              SELECT store_id, ing_id, SUM(qty_base_gram) actual_gram
              FROM stock_movement
              WHERE movement_date = ? AND store_id = ? AND movement_type='consume'
              GROUP BY store_id, ing_id
            )
            SELECT ?, t.store_id, t.ing_id, t.theo_gram, COALESCE(a.actual_gram,0),
                   ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1),
                   CASE WHEN ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) >= 30
                        THEN 'HIGH' ELSE 'MEDIUM' END
            FROM t LEFT JOIN a ON t.store_id=a.store_id AND t.ing_id=a.ing_id
            WHERE ABS(ROUND((COALESCE(a.actual_gram,0)-t.theo_gram)/NULLIF(t.theo_gram,0)*100,1)) > 15
            ON DUPLICATE KEY UPDATE theo_gram = VALUES(theo_gram), actual_gram = VALUES(actual_gram),
                                    diff_pct = VALUES(diff_pct), level = VALUES(level)""";

    /** 从理论vs实际生成预警(幂等: UNIQUE d+store+ing)。按门店循环, 显式谓词下推SQL(不走视图) */
    public int computeAlerts(LocalDate date) {
        List<Integer> stores = read.queryForList("SELECT store_id FROM store ORDER BY store_id", Integer.class);
        int total = 0;
        for (Integer sid : stores) {
            Integer n = write.execute((java.sql.Connection con) -> {
                try (var ps = con.prepareStatement(ALERT_ONE_STORE)) {
                    java.sql.Date d = java.sql.Date.valueOf(date);
                    ps.setDate(1, d); ps.setInt(2, sid);
                    ps.setDate(3, d); ps.setInt(4, sid);
                    ps.setDate(5, d);
                    return ps.executeUpdate();
                }
            });
            total += (n == null ? 0 : n);
        }
        return total;
    }

    public void ack(long alertId) {
        write.update("UPDATE alert SET status='ACK', acked_at=NOW() WHERE id=?", alertId);
    }

    /** 月度浪费汇总(按门店, 谓词下推, 单月范围走索引): 浪费kg vs 理论kg */
    public List<Map<String, Object>> monthlyWaste(LocalDate from, LocalDate to) {
        return read.queryForList("""
            SELECT s.store_id AS storeId, s.name AS storeName,
                   ROUND(COALESCE(w.wasteKg,0),1) AS wasteKg,
                   ROUND(COALESCE(t.theoKg,0),1) AS theoKg
            FROM store s
            LEFT JOIN (
              SELECT store_id, SUM(qty_base_gram)/1000 wasteKg
              FROM waste_record
              WHERE waste_date >= ? AND waste_date <= ?
              GROUP BY store_id
            ) w ON w.store_id = s.store_id
            LEFT JOIN (
              SELECT sl.store_id, ROUND(SUM(sl.qty*b.grams_per_serving)/1000,1) theoKg
              FROM sales_line sl JOIN bom b ON sl.dish_id=b.dish_id
              WHERE sl.order_date >= ? AND sl.order_date <= ?
              GROUP BY sl.store_id
            ) t ON t.store_id = s.store_id
            ORDER BY wasteKg DESC""", java.sql.Date.valueOf(from), java.sql.Date.valueOf(to),
            java.sql.Date.valueOf(from), java.sql.Date.valueOf(to));
    }
}
