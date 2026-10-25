package com.smartfnb.recipe;

import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class Api {

    private final Repo repo;

    public Api(Repo repo) { this.repo = repo; }

    @GetMapping("/stores")
    public List<Map<String, Object>> stores() { return repo.stores(); }

    @GetMapping("/units")
    public List<Map<String, Object>> units() { return repo.units(); }

    @GetMapping("/ingredients")
    public List<Map<String, Object>> ingredients() { return repo.ingredients(); }

    @GetMapping("/ingredients/{id}")
    public Map<String, Object> ingredient(@PathVariable int id) { return repo.ingredient(id); }

    @GetMapping("/dishes")
    public List<Map<String, Object>> dishes(@RequestParam int storeId) { return repo.dishesCached(storeId); }

    @GetMapping("/bom/{dishId}")
    public List<Map<String, Object>> bom(@PathVariable int dishId) { return repo.bom(dishId); }
}
