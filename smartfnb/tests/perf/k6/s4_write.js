import http from 'k6/http';
import { check } from 'k6';

// S4 领料写入(事件链路含Pulsar发布, fire-and-forget)
export const options = {
  scenarios: {
    s4: {
      executor: __ENV.EXECUTOR || 'ramping-vus',
      startVUs: 1,
      stages: __ENV.STAGES
        ? JSON.parse(__ENV.STAGES)
        : [{ duration: '30s', target: Number(__ENV.VUS || 30) },
           { duration: __ENV.DUR || '2m', target: Number(__ENV.VUS || 30) },
           { duration: '20s', target: 0 }],
    },
  },
  thresholds: __ENV.NO_THRESH ? {} : {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

const BASE = __ENV.BASE || 'http://svc-inventory:8080';

export default function () {
  const store = 1 + Math.floor(Math.random() * 32);
  const ing = 1 + Math.floor(Math.random() * 500);
  const r = http.post(`${BASE}/api/stock-movements`,
    JSON.stringify({ storeId: store, ingId: ing, movementType: 'receive',
                     qty: 1 + Math.random() * 5, unitCode: 'kg' }),
    { headers: { 'Content-Type': 'application/json' } });
  check(r, { 'status 200': (s) => s.status === 200 });
}
