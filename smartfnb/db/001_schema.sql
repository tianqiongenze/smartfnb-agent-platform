-- ============================================================
-- SmartF&B fnb schema (TiDB v8.5.8, MySQL compatible)
-- 001_schema.sql : DDL only (indexes added post-load for speed)
-- ============================================================
CREATE DATABASE IF NOT EXISTS fnb DEFAULT CHARSET utf8mb4;
USE fnb;

-- ---------- 主数据 ----------
CREATE TABLE IF NOT EXISTS store (
  store_id    INT NOT NULL PRIMARY KEY,
  name        VARCHAR(64) NOT NULL,
  city        VARCHAR(32) NOT NULL,
  area_m2     INT,
  opened_at   DATE
) COMMENT '门店主数据(32)';

CREATE TABLE IF NOT EXISTS unit_dict (
  unit_code   VARCHAR(8) NOT NULL PRIMARY KEY,
  unit_name   VARCHAR(16) NOT NULL,
  ratio_to_gram DECIMAL(12,4) NOT NULL COMMENT '换算为克的系数'
) COMMENT '计量单位字典(反P7:单位强制过字典)';

CREATE TABLE IF NOT EXISTS ingredient (
  ing_id    INT NOT NULL PRIMARY KEY,
  ing_code  VARCHAR(16) NOT NULL UNIQUE COMMENT '一品一码',
  name_std  VARCHAR(64) NOT NULL COMMENT '标准名',
  category  VARCHAR(16) NOT NULL COMMENT '肉类/海鲜/蔬菜/调料/粮油/干货',
  base_unit VARCHAR(8) NOT NULL DEFAULT 'g',
  box_ratio DECIMAL(12,4) DEFAULT NULL COMMENT '按箱采购时每箱克数',
  aliases   JSON COMMENT '历史别名(鸡翅膀/翅中/鸡翅（中）)',
  ref_price DECIMAL(10,2) COMMENT '参考价 元/kg'
) COMMENT '食材主数据(500)';

CREATE TABLE IF NOT EXISTS supplier (
  sup_id   INT NOT NULL PRIMARY KEY,
  name     VARCHAR(64) NOT NULL,
  category VARCHAR(16),
  rating   DECIMAL(3,1)
) COMMENT '供应商(200)';

CREATE TABLE IF NOT EXISTS dish (
  dish_id  INT NOT NULL PRIMARY KEY,
  name     VARCHAR(64) NOT NULL,
  category VARCHAR(16),
  price    DECIMAL(8,2)
) COMMENT '菜品(800)';

CREATE TABLE IF NOT EXISTS bom (
  id BIGINT NOT NULL PRIMARY KEY AUTO_RANDOM(4),
  dish_id INT NOT NULL,
  ing_id  INT NOT NULL,
  grams_per_serving DECIMAL(10,2) NOT NULL,
  KEY idx_bom_dish (dish_id)
) COMMENT '菜品配方BOM';

CREATE TABLE IF NOT EXISTS store_menu (
  store_id INT NOT NULL,
  dish_id  INT NOT NULL,
  PRIMARY KEY (store_id, dish_id)
) COMMENT '门店菜单';

CREATE TABLE IF NOT EXISTS member (
  member_id BIGINT NOT NULL PRIMARY KEY,
  name_mask VARCHAR(16),
  phone_hash CHAR(64) COMMENT '脱敏(GB/T 35273)',
  level     TINYINT,
  registered_at DATE
) COMMENT '会员(100万,对应百万用户口径D1)';

CREATE TABLE IF NOT EXISTS hot_member (
  hot_id  INT NOT NULL PRIMARY KEY,
  member_id BIGINT NOT NULL,
  order_cnt INT
) COMMENT '热点会员Top10万(Redis warmup数据源)';

-- ---------- 事实表(先无二级索引,003补建) ----------
CREATE TABLE IF NOT EXISTS sales_order (
  order_id  BIGINT NOT NULL PRIMARY KEY,
  store_id  INT NOT NULL,
  member_id BIGINT,
  order_date DATE NOT NULL,
  order_time DATETIME NOT NULL,
  channel   TINYINT COMMENT '1堂食2外卖3团建预订',
  amount    DECIMAL(12,2)
) COMMENT '销售订单头(1500万)';

CREATE TABLE IF NOT EXISTS sales_line (
  line_id  BIGINT NOT NULL PRIMARY KEY,
  order_id BIGINT NOT NULL,
  store_id INT NOT NULL,
  order_date DATE NOT NULL,
  dish_id  INT NOT NULL,
  qty      INT NOT NULL,
  line_amount DECIMAL(12,2)
) COMMENT '销售明细(6000万)';

CREATE TABLE IF NOT EXISTS stock_movement (
  mov_id BIGINT NOT NULL PRIMARY KEY,
  store_id INT NOT NULL,
  ing_id  INT NOT NULL,
  movement_date DATE NOT NULL,
  movement_type ENUM('receive','consume','waste','transfer_out') NOT NULL,
  qty_base_gram BIGINT NOT NULL COMMENT '统一克(反P7)',
  ref_no   VARCHAR(32),
  created_at DATETIME
) COMMENT '出入库流水(3000万)';

CREATE TABLE IF NOT EXISTS waste_record (
  waste_id BIGINT NOT NULL PRIMARY KEY,
  store_id INT NOT NULL,
  ing_id  INT NOT NULL,
  waste_date DATE NOT NULL,
  qty_base_gram BIGINT NOT NULL,
  reason TINYINT COMMENT '1过期2工艺损耗3破损4其他',
  note VARCHAR(128)
) COMMENT '废弃记录(500万)';

CREATE TABLE IF NOT EXISTS purchase_order (
  po_id BIGINT NOT NULL PRIMARY KEY,
  store_id INT NOT NULL,
  sup_id  INT NOT NULL,
  order_date DATE NOT NULL,
  status TINYINT,
  total_amount DECIMAL(14,2)
) COMMENT '采购单(400万)';

CREATE TABLE IF NOT EXISTS purchase_item (
  pi_id BIGINT NOT NULL PRIMARY KEY,
  po_id BIGINT NOT NULL,
  ing_id INT NOT NULL,
  qty    DECIMAL(12,2),
  unit_code VARCHAR(8),
  unit_price DECIMAL(10,2)
) COMMENT '采购明细(1000万)';

-- ---------- 告警(svc-inventory写入) ----------
CREATE TABLE IF NOT EXISTS alert (
  id BIGINT NOT NULL PRIMARY KEY AUTO_RANDOM(5),
  diff_date DATE NOT NULL,
  store_id INT NOT NULL,
  ing_id  INT NOT NULL,
  theo_gram BIGINT,
  actual_gram BIGINT,
  diff_pct DECIMAL(6,1),
  level ENUM('HIGH','MEDIUM') NOT NULL,
  status ENUM('OPEN','ACK') NOT NULL DEFAULT 'OPEN',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  acked_at DATETIME NULL,
  UNIQUE KEY uk_alert (diff_date, store_id, ing_id)
) COMMENT '用量差异预警(反P6:数字可溯源)';

-- ---------- Phase2 采购建议(人在环) ----------
CREATE TABLE IF NOT EXISTS po_suggestion (
  id BIGINT NOT NULL PRIMARY KEY,
  store_id INT NOT NULL,
  ing_id  INT NOT NULL,
  sug_date DATE NOT NULL,
  suggest_qty DECIMAL(12,2) NOT NULL,
  unit_code VARCHAR(8) NOT NULL,
  sup_id INT,
  est_price DECIMAL(10,2),
  reason VARCHAR(300),
  status ENUM('DRAFT','APPROVED','REJECTED') NOT NULL DEFAULT 'DRAFT',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  decided_at DATETIME NULL,
  decided_by VARCHAR(32) NULL,
  KEY idx_sug_status (status, store_id)
) COMMENT '采购建议单(AI生成, 人在环审批)';

-- ---------- Phase3 会员域 ----------
CREATE TABLE IF NOT EXISTS member_points (
  member_id BIGINT NOT NULL PRIMARY KEY,
  points INT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT '会员积分';
CREATE TABLE IF NOT EXISTS member_coupons (
  id BIGINT NOT NULL PRIMARY KEY,
  member_id BIGINT NOT NULL,
  title VARCHAR(64) NOT NULL,
  amount DECIMAL(8,2) NOT NULL,
  status ENUM('VALID','USED') NOT NULL DEFAULT 'VALID',
  issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  used_at DATETIME NULL,
  KEY idx_mc_member (member_id, status)
) COMMENT '会员券';
