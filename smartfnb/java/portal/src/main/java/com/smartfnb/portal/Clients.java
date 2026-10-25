package com.smartfnb.portal;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;

/** 下游客户端装配: recipe/inventory(REST) + agent(SSE) */
@Configuration
public class Clients {

    @Bean
    public RestClient recipeClient(@Value("${app.recipe-url}") String base) {
        return RestClient.builder().baseUrl(base).build();
    }

    @Bean
    public RestClient inventoryClient(@Value("${app.inventory-url}") String base) {
        return RestClient.builder().baseUrl(base).build();
    }

    @Bean
    public WebClient agentWebClient(@Value("${app.agent-url}") String base) {
        return WebClient.builder().baseUrl(base).build();
    }
}
