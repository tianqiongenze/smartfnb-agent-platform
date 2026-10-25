package com.smartfnb.member;

import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 会员域API(Phase3, C端百万用户入口): 资料/积分/券 */
@RestController
@RequestMapping("/api/members")
public class Api {

    private final Repo repo;

    public Api(Repo repo) { this.repo = repo; }

    @GetMapping("/{id}")
    public Map<String, Object> profile(@PathVariable long id) { return repo.profile(id); }

    /** 消费得积分: delta=消费金额(元取整) */
    @PostMapping("/{id}/points")
    public Map<String, Object> earn(@PathVariable long id, @RequestParam int delta) {
        int total = repo.earnPoints(id, Math.max(delta, 0));
        return Map.of("memberId", id, "earned", Math.max(delta, 0), "total", total);
    }

    @GetMapping("/{id}/coupons")
    public List<Map<String, Object>> coupons(@PathVariable long id) { return repo.coupons(id); }

    @PostMapping("/{id}/coupons")
    public Map<String, Object> issue(@PathVariable long id,
                                     @RequestParam(defaultValue = "会员专享券") String title,
                                     @RequestParam(defaultValue = "20") double amount) {
        return repo.issueCoupon(id, title, amount);
    }

    @PostMapping("/{id}/coupons/{couponId}/use")
    public Map<String, Object> use(@PathVariable long id, @PathVariable long couponId) {
        int n = repo.useCoupon(couponId, id);
        if (n == 0) throw new IllegalArgumentException("券不存在或已使用");
        return Map.of("ok", true);
    }
}
