package com.smartfnb.recipe;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/** 仓储: 只读主数据访问 + L1 Caffeine 缓存(30min, TTL策略见方案§7.2) */
@Repository
public class Repo {

    private final JdbcTemplate jdbc;
    private final Cache<String, List<Map<String, Object>>> l1 =
            Caffeine.newBuilder().expireAfterWrite(Duration.ofMinutes(30)).maximumSize(512).build();

    public Repo(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public List<Map<String, Object>> stores() {
        return l1.get("stores", k -> jdbc.queryForList(
                "SELECT store_id AS id, name, city, area_m2 AS areaM2 FROM store ORDER BY store_id"));
    }

    public List<Map<String, Object>> units() {
        return l1.get("units", k -> jdbc.queryForList(
                "SELECT unit_code AS code, unit_name AS name, ratio_to_gram AS ratioToGram FROM unit_dict"));
    }

    public Map<String, Object> unit(String code) {
        return jdbc.queryForMap("SELECT unit_code, unit_name, ratio_to_gram FROM unit_dict WHERE unit_code=?", code);
    }

    public List<Map<String, Object>> ingredients() {
        return l1.get("ingredients", k -> jdbc.queryForList(
                "SELECT ing_id AS id, ing_code AS code, name_std AS name, category, ref_price AS refPrice FROM ingredient ORDER BY ing_id"));
    }

    public Map<String, Object> ingredient(int id) {
        return jdbc.queryForMap("SELECT ing_id, ing_code, name_std, category, base_unit, box_ratio, aliases, ref_price FROM ingredient WHERE ing_id=?", id);
    }

    public List<Map<String, Object>> dishes(int storeId) {
        return jdbc.queryForList("""
            SELECT d.dish_id, d.name, d.category, d.price FROM store_menu m
            JOIN dish d ON d.dish_id = m.dish_id WHERE m.store_id=? ORDER BY d.dish_id""", storeId);
    }

    public List<Map<String, Object>> bom(int dishId) {
        return jdbc.queryForList("""
            SELECT b.dish_id, b.ing_id, b.grams_per_serving, i.name_std, i.ing_code, i.category
            FROM bom b JOIN ingredient i ON i.ing_id = b.ing_id WHERE b.dish_id=?""", dishId);
    }

    /** L1缓存包装(用于热点读) */
    public List<Map<String, Object>> dishesCached(int storeId) {
        return l1.get("dishes:" + storeId, k -> dishes(storeId));
    }
}
