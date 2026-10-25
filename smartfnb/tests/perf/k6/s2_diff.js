import http from 'k6/http';
import { check, sleep } from 'k6';

// S2 差异报表(重聚合查询, 读源)
export const options = {
  scenarios: {
    s2: {
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
    http_req_duration: ['p(95)<1000'],
  },
};

const BASE = __ENV.BASE || 'http://svc-portal:8080';
const DATE = __ENV.QDATE || '2026-10-23';
const STORES = [7, 18, 3, 27, 12];

export default function () {
  const s = STORES[Math.floor(Math.random() * STORES.length)];
  const r = http.post(`${BASE}/graphql`,
    JSON.stringify({ query: `query($s:Int,$d:String!){diffReport(storeId:$s,date:$d,limit:60){alertCount lines{ingName diffPct level}}}`,
                     variables: { s, d: DATE } }),
    { headers: { 'Content-Type': 'application/json' } });
  check(r, { 'status 200': (s2) => s2.status === 200 });
  sleep(0.5);
}
