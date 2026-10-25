import http from 'k6/http';

// C组风暴探针: ramping到STORM_VUS(10K/100K), 单Pod尽力而为(8Gi)
export const options = {
  scenarios: {
    storm: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: Number(__ENV.STORM_VUS || 10000) },
        { duration: '45s', target: Number(__ENV.STORM_VUS || 10000) },
        { duration: '15s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  discardResponseBodies: true,
  systemTags: ['status', 'error'],
};

const BASE = __ENV.BASE || 'http://svc-portal:8080';
export default function () {
  http.post(`${BASE}/graphql`,
    JSON.stringify({ query: '{stores{id,name}}' }),
    { headers: { 'Content-Type': 'application/json' } });
}
