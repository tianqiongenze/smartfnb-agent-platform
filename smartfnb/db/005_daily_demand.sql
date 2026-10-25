-- 005_daily_demand.sql : 预计算每店每食材每日理论需求(克) — 预测服务的数据基座
USE fnb;

CREATE TABLE IF NOT EXISTS daily_demand (
  store_id  INT NOT NULL,
  ing_id    INT NOT NULL,
  stat_date DATE NOT NULL,
  demand_gram BIGINT NOT NULL,
  PRIMARY KEY (store_id, ing_id, stat_date)
);

INSERT INTO daily_demand (store_id, ing_id, stat_date, demand_gram)
SELECT sl.store_id, b.ing_id, sl.order_date, CAST(ROUND(SUM(sl.qty * b.grams_per_serving)) AS SIGNED)
FROM sales_line sl
JOIN bom b ON sl.dish_id = b.dish_id
GROUP BY sl.store_id, b.ing_id, sl.order_date;
