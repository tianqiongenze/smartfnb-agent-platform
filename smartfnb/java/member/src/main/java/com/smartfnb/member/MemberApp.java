package com.smartfnb.member;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;

@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)
public class MemberApp {
    public static void main(String[] args) {
        SpringApplication.run(MemberApp.class, args);
    }
}
