# -*- coding: utf-8 -*-
"""push_opt.py — V4-OPT 重构成果推送主仓库(Contents API, 带重试)"""
import base64, json, subprocess, urllib.request, os

def token():
    r = subprocess.run(['git','credential','fill'], input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('password='): return line.split('=',1)[1]
T = token()

def api(method, path, body=None, timeout=60):
    req = urllib.request.Request(f'https://api.github.com/repos/tianqiongenze/smartfnb-agent-platform{path}',
        data=json.dumps(body).encode() if body else None, method=method)
    req.add_header('Authorization', f'token {T}'); req.add_header('Accept','application/vnd.github+json')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return json.loads(e.read().decode())
    except Exception as e: return {'message': str(e)}

FILES = [
    ('smartfnb/agent-runtime/app/guards.py', r'D:\projects\连锁餐饮智能体\smartfnb\agent-runtime\app\guards.py'),
    ('smartfnb/agent-runtime/app/main.py', r'D:\projects\连锁餐饮智能体\smartfnb\agent-runtime\app\main.py'),
    ('smartfnb/agent-runtime/app/graph.py', r'D:\projects\连锁餐饮智能体\smartfnb\agent-runtime\app\graph.py'),
    ('smartfnb/agent-runtime/app/harness/budget.py', r'D:\projects\连锁餐饮智能体\smartfnb\agent-runtime\app\harness\budget.py'),
    ('smartfnb/agent-runtime/app/harness/loop.py', r'D:\projects\连锁餐饮智能体\smartfnb\agent-runtime\app\harness\loop.py'),
    ('smartfnb/agent-runtime/tests/test_store_date_extract.py', r'D:\projects\连锁餐饮智能体\smartfnb\agent-runtime\tests\test_store_date_extract.py'),
    ('smartfnb/mcp-fnb-tools/server.py', r'D:\projects\连锁餐饮智能体\smartfnb\mcp-fnb-tools\server.py'),
    ('smartfnb/tools/event-consumer/consumer.py', r'D:\projects\连锁餐饮智能体\smartfnb\tools\event-consumer\consumer.py'),
    ('smartfnb/tools/redis-warmup/warmup.py', r'D:\projects\连锁餐饮智能体\smartfnb\tools\redis-warmup\warmup.py'),
    ('smartfnb/tools/quality/seed_check.py', r'D:\projects\连锁餐饮智能体\smartfnb\tools\quality\seed_check.py'),
    ('docs/03-%E4%B8%8A%E7%BA%BF%E6%8A%A5%E5%91%8A.md', r'D:\projects\连锁餐饮智能体\docs\03-上线报告.md'),
]
for path, local in FILES:
    ok = False
    for attempt in range(3):
        try:
            with open(local,'rb') as f: content = base64.b64encode(f.read()).decode()
            old = api('GET', f'/contents/{path}?ref=main')
            body = {'message': f'V4-OPT: 用户确认选项1离线重构 ({os.path.basename(local)})', 'content': content, 'branch':'main'}
            if 'sha' in old: body['sha'] = old['sha']
            r = api('PUT', f'/contents/{path}', body)
            if 'commit' in r:
                print(os.path.basename(local), 'OK'); ok = True; break
            print(os.path.basename(local), 'retry', attempt, r.get('message'))
        except Exception as e:
            print(os.path.basename(local), 'err', str(e)[:100])
    if not ok: print('FAILED:', local)
