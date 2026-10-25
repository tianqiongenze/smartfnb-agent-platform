package com.smartfnb.inventory;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;

/** 排除自动配置: 读写分离双数据源手工装配(DsCfg), TiDB 多Server分源 */
@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)
public class InventoryApp {
    public static void main(String[] args) {
        SpringApplication.run(InventoryApp.class, args);
    }
}
