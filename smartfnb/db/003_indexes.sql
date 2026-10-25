-- 003_indexes.sql : 数据加载完成后补建索引并ANALYZE(生成器全部完成前不执行)
USE fnb;

ALTER TABLE sales_line ADD INDEX idx_sl_date_store (order_date, store_id, dish_id);
ALTER TABLE sales_order ADD INDEX idx_so_date (order_date, store_id);
ALTER TABLE stock_movement ADD INDEX idx_sm_date_store (movement_date, store_id, movement_type, ing_id);
ALTER TABLE waste_record ADD INDEX idx_wr_date (waste_date, store_id);
ALTER TABLE purchase_order ADD INDEX idx_po_date (order_date, store_id);
ALTER TABLE purchase_item ADD INDEX idx_pi_po (po_id);
ALTER TABLE member ADD INDEX idx_member_level (level);

ANALYZE TABLE sales_line, sales_order, stock_movement, waste_record, purchase_order, purchase_item, member, bom;
