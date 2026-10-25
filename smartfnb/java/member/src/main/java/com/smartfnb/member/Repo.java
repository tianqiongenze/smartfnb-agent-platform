package com.smartfnb.member;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Repository
public class Repo {

    private final JdbcTemplate read, write;

    public Repo(@Qualifier("readJdbc") JdbcTemplate read, @Qualifier("writeJdbc") JdbcTemplate write) {
        this.read = read; this.write = write;
    }

    public Map<String, Object> profile(long memberId) {
        return read.queryForMap("""
            SELECT m.member_id AS memberId, m.name_mask AS nameMask, m.level,
                   COALESCE(p.points, 0) AS points
            FROM member m LEFT JOIN member_points p ON p.member_id = m.member_id
            WHERE m.member_id = ?""", memberId);
    }

    /** 消费得积分(1元=1分): upsert幂等 */
    public int earnPoints(long memberId, int delta) {
        write.update("""
                INSERT INTO member_points (member_id, points) VALUES (?,?)
                ON DUPLICATE KEY UPDATE points = points + VALUES(points)""", memberId, delta);
        return read.queryForObject("SELECT points FROM member_points WHERE member_id=?", Integer.class, memberId);
    }

    public List<Map<String, Object>> coupons(long memberId) {
        return read.queryForList("""
            SELECT id, title, amount, status, issued_at AS issuedAt
            FROM member_coupons WHERE member_id=? ORDER BY issued_at DESC LIMIT 20""", memberId);
    }

    public Map<String, Object> issueCoupon(long memberId, String title, double amount) {
        long id = (System.currentTimeMillis() << 10)
                | java.util.concurrent.ThreadLocalRandom.current().nextLong(1024);
        write.update("INSERT INTO member_coupons (id, member_id, title, amount) VALUES (?,?,?,?)",
                id, memberId, title, amount);
        return Map.of("id", String.valueOf(id), "title", title, "amount", amount, "status", "VALID");
    }

    public int useCoupon(long id, long memberId) {
        return write.update(
                "UPDATE member_coupons SET status='USED', used_at=NOW() WHERE id=? AND member_id=? AND status='VALID'",
                id, memberId);
    }
}
