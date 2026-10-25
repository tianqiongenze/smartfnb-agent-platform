package com.smartfnb.procurement;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;

/** TiDB 读写分离双数据源(与svc-inventory同款装配) */
@Configuration
public class DsCfg {

    @Bean(destroyMethod = "close")
    public DataSource writeDs(@Value("${app.db.write}") String url,
                              @Value("${app.db.user:root}") String user,
                              @Value("${app.db.pass:}") String pass) {
        return hikari(url, user, pass, 10);
    }

    @Bean(destroyMethod = "close")
    public DataSource readDs(@Value("${app.db.read}") String url,
                             @Value("${app.db.user:root}") String user,
                             @Value("${app.db.pass:}") String pass) {
        return hikari(url, user, pass, 20);
    }

    @Bean
    public JdbcTemplate writeJdbc(@Qualifier("writeDs") DataSource ds) { return new JdbcTemplate(ds); }

    @Bean
    public JdbcTemplate readJdbc(@Qualifier("readDs") DataSource ds) { return new JdbcTemplate(ds); }

    private HikariDataSource hikari(String url, String user, String pass, int pool) {
        HikariConfig c = new HikariConfig();
        c.setJdbcUrl(url); c.setUsername(user); c.setPassword(pass);
        c.setMaximumPoolSize(pool);
        c.setConnectionTestQuery("SELECT 1");
        c.setInitializationFailTimeout(60_000);
        return new HikariDataSource(c);
    }
}
