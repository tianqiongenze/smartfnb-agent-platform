package com.smartfnb.portal;

import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.MutationMapping;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.stereotype.Controller;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/** GraphQL BFF: 聚合 recipe/inventory, 一次请求取全(方案§6.3) */
@Controller
public class GraphqlApi {

    private final RestClient recipe, inventory;

    public GraphqlApi(RestClient recipeClient, RestClient inventoryClient) {
        this.recipe = recipeClient; this.inventory = inventoryClient;
    }

    @QueryMapping
    public List<Map<String, Object>> stores() {
        return recipe.get().uri("/api/stores").retrieve().body(List.class);
    }

    @QueryMapping
    public List<Map<String, Object>> units() {
        return recipe.get().uri("/api/units").retrieve().body(List.class);
    }

    @QueryMapping
    public List<Map<String, Object>> ingredients() {
        return recipe.get().uri("/api/ingredients").retrieve().body(List.class);
    }

    @SuppressWarnings("unchecked")
    @QueryMapping
    public Map<String, Object> diffReport(@Argument Integer storeId, @Argument String date,
                                          @Argument Integer limit) {
        String uri = storeId == null
                ? "/api/diff?date=" + date + "&limit=" + (limit == null ? 100 : limit)
                : "/api/diff?date=" + date + "&storeId=" + storeId + "&limit=" + (limit == null ? 100 : limit);
        List<Map<String, Object>> lines = inventory.get().uri(uri).retrieve().body(List.class);
        List<Map<String, Object>> alerts = inventory.get()
                .uri("/api/alerts?date=" + date + (storeId == null ? "" : "&storeId=" + storeId))
                .retrieve().body(List.class);
        return Map.of("date", date, "storeId", storeId == null ? 0 : storeId,
                "lines", lines == null ? List.of() : lines,
                "alertCount", alerts == null ? 0 : alerts.size());
    }

    @QueryMapping
    public List<Map<String, Object>> alerts(@Argument String date, @Argument Integer storeId) {
        String uri = "/api/alerts?date=" + date + (storeId == null ? "" : "&storeId=" + storeId);
        return inventory.get().uri(uri).retrieve().body(List.class);
    }

    @QueryMapping
    public List<Map<String, Object>> quality() {
        Map<String, Object> resp = recipe.get().uri("/api/quality/latest").retrieve().body(Map.class);
        Object rules = resp == null ? List.of() : resp.get("rules");
        return rules instanceof List ? (List<Map<String, Object>>) rules : List.of();
    }

    @MutationMapping
    public boolean ackAlert(@Argument String id) {
        inventory.post().uri("/api/alerts/" + id + "/ack").retrieve().toBodilessEntity();
        return true;
    }

    @MutationMapping
    public String ingestMovement(@Argument Integer storeId, @Argument Integer ingId,
                                 @Argument String movementType, @Argument Double qty, @Argument String unitCode) {
        Map<String, Object> resp = inventory.post().uri("/api/stock-movements")
                .body(Map.of("storeId", storeId, "ingId", ingId, "movementType", movementType,
                        "qty", qty, "unitCode", unitCode))
                .retrieve().body(Map.class);
        return String.valueOf(resp == null ? "" : resp.get("refNo"));
    }
}
