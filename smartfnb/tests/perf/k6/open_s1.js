import http from 'k6/http';
import { check } from 'k6';

// 开放模型: constant-arrival-rate, RATE由env注入(验证§1.4口径5-10K QPS)
export const options = {
  scenarios: {
    open: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 3000),
      timeUnit: '1s',
      duration: __ENV.DUR || '60s',
      preAllocatedVUs: Number(__ENV.PRE || 2000),
      maxVUs: Number(__ENV.MAX || 30000),
    },
  },
  discardResponseBodies: true,
  thresholds: __ENV.NO_THRESH ? {} : {
    http_req_failed: ['rate<0.05'],
  },
};

const BASE = __ENV.BASE || 'http://svc-portal:8080';
export default function () {
  const r = http.post(`${BASE}/graphql`,
    JSON.stringify({ query: '{stores{id,name}}' }),
    { headers: { 'Content-Type': 'application/json' } });
  check(r, { '200': (s) => s.status === 200 });
}
