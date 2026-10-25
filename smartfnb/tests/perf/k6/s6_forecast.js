import http from 'k6/http';
import { check, sleep } from 'k6';

// S6 需求预测(统计模型路径)
export const options = {
  scenarios: {
    s6: {
      executor: __ENV.EXECUTOR || 'ramping-vus',
      startVUs: 1,
      stages: __ENV.STAGES
        ? JSON.parse(__ENV.STAGES)
        : [{ duration: '30s', target: Number(__ENV.VUS || 10) },
           { duration: __ENV.DUR || '2m', target: Number(__ENV.VUS || 10) },
           { duration: '20s', target: 0 }],
    },
  },
  thresholds: __ENV.NO_THRESH ? {} : {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
  },
};

const BASE = __ENV.BASE || 'http://svc-forecast:8000';
const INGS = ['鲈鱼', '五花肉', '土豆', '基围虾', '牛腩'];

export default function () {
  const ing = INGS[Math.floor(Math.random() * INGS.length)];
  const store = 1 + Math.floor(Math.random() * 32);
  const r = http.get(
    `${BASE}/api/forecast?storeId=${store}&ingName=${encodeURIComponent(ing)}&days=7`);
  check(r, { 'status 200': (s) => s.status === 200 });
  sleep(0.5);
}
