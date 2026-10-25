import http from 'k6/http';
import { check, sleep } from 'k6';

// S1 菜单浏览(主数据读, L1缓存路径)
export const options = {
  scenarios: {
    s1: {
      executor: __ENV.EXECUTOR || 'ramping-vus',
      startVUs: Number(__ENV.START_VUS || 1),
      stages: __ENV.STAGES
        ? JSON.parse(__ENV.STAGES)
        : [{ duration: '30s', target: Number(__ENV.VUS || 50) },
           { duration: __ENV.DUR || '2m', target: Number(__ENV.VUS || 50) },
           { duration: '20s', target: 0 }],
      gracefulRampDown: '10s',
    },
  },
  thresholds: __ENV.NO_THRESH ? {} : {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300'],
  },
  discardResponseBodies: true,
};

const BASE = __ENV.BASE || 'http://svc-portal:8080';

export default function () {
  const r = http.post(`${BASE}/graphql`,
    JSON.stringify({ query: '{stores{id,name} ingredients{id,name,category}}' }),
    { headers: { 'Content-Type': 'application/json' } });
  check(r, { 'status 200': (s) => s.status === 200 });
  sleep(0.1);
}
