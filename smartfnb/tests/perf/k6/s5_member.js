import http from 'k6/http';
import { check, sleep } from 'k6';

// S5 会员积分/券(C端百万口径主路径)
export const options = {
  scenarios: {
    s5: {
      executor: __ENV.EXECUTOR || 'ramping-vus',
      startVUs: 1,
      stages: __ENV.STAGES
        ? JSON.parse(__ENV.STAGES)
        : [{ duration: '30s', target: Number(__ENV.VUS || 50) },
           { duration: __ENV.DUR || '2m', target: Number(__ENV.VUS || 50) },
           { duration: '20s', target: 0 }],
    },
  },
  thresholds: __ENV.NO_THRESH ? {} : {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300'],
  },
};

const BASE = __ENV.BASE || 'http://svc-member:8080';

export default function () {
  // 模拟百万会员随机分布: 100000..1099999
  const id = 100000 + Math.floor(Math.random() * 1000000);
  const r1 = http.get(`${BASE}/api/members/${id}`);
  check(r1, { 'profile 200': (s) => s.status === 200 });
  if (Math.random() < 0.2) {
    const r2 = http.post(`${BASE}/api/members/${id}/points?delta=${10 + Math.floor(Math.random() * 90)}`);
    check(r2, { 'earn 200': (s) => s.status === 200 });
  }
  sleep(0.2);
}
