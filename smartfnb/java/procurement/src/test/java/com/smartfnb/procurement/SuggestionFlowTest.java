package com.smartfnb.procurement;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** TDD: 人在环审批规则(建议单只能从DRAFT流转, AI不可越过审批) */
class SuggestionFlowTest {

    static final class Suggestion {
        final String status;
        Suggestion(String status) { this.status = status; }
    }

    /** 领域规则: 审批流转白名单(DRAFT→APPROVED/REJECTED), 其他状态一律拒绝 */
    static boolean canDecide(Suggestion s, String target) {
        if (!"APPROVED".equals(target) && !"REJECTED".equals(target)) return false;
        return s != null && "DRAFT".equals(s.status);
    }

    @Test
    @DisplayName("DRAFT可审批为APPROVED")
    void draftToApproved() {
        assertTrue(canDecide(new Suggestion("DRAFT"), "APPROVED"));
    }

    @Test
    @DisplayName("已APPROVED的不可再次流转(防重复审批/越权)")
    void approvedIsTerminal() {
        assertFalse(canDecide(new Suggestion("APPROVED"), "APPROVED"));
        assertFalse(canDecide(new Suggestion("APPROVED"), "REJECTED"));
    }

    @Test
    @DisplayName("非法目标状态拒绝")
    void illegalTarget() {
        assertFalse(canDecide(new Suggestion("DRAFT"), "PAID"));
    }

    @Test
    @DisplayName("null建议单拒绝")
    void nullSuggestion() {
        assertFalse(canDecide(null, "APPROVED"));
    }
}
