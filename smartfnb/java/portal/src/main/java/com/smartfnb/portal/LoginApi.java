package com.smartfnb.portal;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;

/** MVP登录: 固定账号+HS256 JWT(等保强化在Phase 1接入IAM) */
@RestController
@RequestMapping("/api")
public class LoginApi {

    @Value("${app.jwt-secret:smartfnb-dev-secret}")
    private String secret;

    private static final Map<String, String> USERS = Map.of(
            "admin", "admin123",       // 总部运营
            "buyer", "buyer123",       // 采购主管
            "store7", "store123"       // 7号店店长(演示)
    );

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody Map<String, String> body) {
        String user = body.getOrDefault("username", "");
        String pass = body.getOrDefault("password", "");
        if (!pass.equals(USERS.get(user))) {
            throw new IllegalArgumentException("用户名或密码错误");
        }
        return Map.of("token", jwt(user), "user", user, "role", user.equals("admin") ? "ADMIN" : "USER");
    }

    private String jwt(String sub) {
        try {
            String header = Base64.getUrlEncoder().withoutPadding()
                    .encodeToString("{\"alg\":\"HS256\"}".getBytes(StandardCharsets.UTF_8));
            long exp = Instant.now().plusSeconds(8 * 3600).getEpochSecond();
            String payload = Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(("{\"sub\":\"" + sub + "\",\"exp\":" + exp + "}")
                            .getBytes(StandardCharsets.UTF_8));
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            String sig = Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(mac.doFinal((header + "." + payload).getBytes(StandardCharsets.UTF_8)));
            return header + "." + payload + "." + sig;
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
