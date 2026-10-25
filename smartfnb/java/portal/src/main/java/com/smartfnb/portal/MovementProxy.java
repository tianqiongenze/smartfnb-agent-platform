package com.smartfnb.portal;

import org.springframework.web.client.RestClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** H5/PDA 领料扫码代理(Phase1): 转发到 svc-inventory 登记接口 */
@RestController
@RequestMapping("/api/movements")
public class MovementProxy {

    private final RestClient inventory;

    public MovementProxy(RestClient inventoryClient) { this.inventory = inventoryClient; }

    @PostMapping
    public Map<String, Object> ingest(@RequestBody Map<String, Object> body) {
        return inventory.post().uri("/api/stock-movements")
                .body(body)
                .retrieve().body(Map.class);
    }

    /** R8: 运营页代理 — 采购/World Model/预测 REST */
    @GetMapping("/proc/**")
    public Object procGet(jakarta.servlet.http.HttpServletRequest req) {
        String path = req.getRequestURI().replaceFirst("^.*?/api/proc", "/api");
        String q = req.getQueryString();
        return inventory.get().uri(path + (q == null ? "" : "?" + q)).retrieve().body(Object.class);
    }

    @PostMapping("/proc/**")
    public Object procPost(jakarta.servlet.http.HttpServletRequest req,
                           @RequestBody(required = false) Map<String, Object> body) {
        String path = req.getRequestURI().replaceFirst("^.*?/api/proc", "/api");
        String q = req.getQueryString();
        var spec = inventory.post().uri(path + (q == null ? "" : "?" + q));
        if (body != null) spec = spec.body(body);
        return spec.retrieve().body(Object.class);
    }
}
