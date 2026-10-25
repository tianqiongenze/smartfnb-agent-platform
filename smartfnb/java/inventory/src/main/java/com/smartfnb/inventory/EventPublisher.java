package com.smartfnb.inventory;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/** 领域事件发布器(R2): 经Pulsar REST Producer发布 stock.movement.created
 * fire-and-forget: 事件链路故障不阻塞领料写入(反P4: 失败仅记日志, CronJob兜底) */
@Component
public class EventPublisher {

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3)).build();
    private final String pulsarUrl;

    public EventPublisher() {
        // R2: 经事件枢纽的HTTP生产网关投递(pulsar python客户端生产, 解耦Java与Pulsar版本)
        this.pulsarUrl = System.getenv().getOrDefault("EVENT_HUB_URL",
                "http://event-consumer:8081/publish");
    }

    public void publishMovementCreated(int storeId, int ingId, String date, double gram) {
        try {
            String body = "{\"storeId\":" + storeId + ",\"ingId\":" + ingId
                    + ",\"date\":\"" + date + "\",\"gram\":" + (long) gram + "}";
            HttpRequest req = HttpRequest.newBuilder(URI.create(pulsarUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .timeout(Duration.ofSeconds(5))
                    .build();
            http.sendAsync(req, HttpResponse.BodyHandlers.discarding())
                .exceptionally(e -> { warn(storeId, e); return null; });
        } catch (Exception e) {
            warn(storeId, e);
        }
    }

    private void warn(int storeId, Throwable e) {
        System.out.printf("[EVENT_PUBLISH_FAIL] store=%d %s%n", storeId, e.getMessage());
    }
}
