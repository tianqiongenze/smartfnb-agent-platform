-- 004_views.sql : 理论用量/实际用量/差异视图(执行于数据加载+索引之后)
USE fnb;

CREATE OR REPLACE VIEW v_theoretical AS
SELECT sl.order_date AS d, sl.store_id, b.ing_id,
       ROUND(SUM(sl.qty * b.grams_per_serving)) AS theo_gram
FROM sales_line sl
JOIN bom b ON sl.dish_id = b.dish_id
GROUP BY sl.order_date, sl.store_id, b.ing_id;

CREATE OR REPLACE VIEW v_actual AS
SELECT movement_date AS d, store_id, ing_id,
       SUM(qty_base_gram) AS actual_gram
FROM stock_movement
WHERE movement_type = 'consume'
GROUP BY movement_date, store_id, ing_id;

CREATE OR REPLACE VIEW v_diff AS
SELECT COALESCE(t.d, a.d)      AS d,
       COALESCE(t.store_id, a.store_id) AS store_id,
       COALESCE(t.ing_id,  a.ing_id)    AS ing_id,
       COALESCE(t.theo_gram, 0) AS theo_gram,
       COALESCE(a.actual_gram, 0) AS actual_gram,
       ROUND((COALESCE(a.actual_gram,0) - COALESCE(t.theo_gram,0))
             / NULLIF(t.theo_gram,0) * 100, 1) AS diff_pct
FROM v_theoretical t
LEFT JOIN v_actual a
  ON t.d = a.d AND t.store_id = a.store_id AND t.ing_id = a.ing_id;
