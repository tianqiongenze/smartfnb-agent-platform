# -*- coding: utf-8 -*-
"""push_v3.py — V3修复与报告推送(Contents API, 带超时与逐文件重试)"""
import base64, json, subprocess, urllib.request, os, sys

def token():
    r = subprocess.run(['git','credential','fill'], input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('password='): return line.split('=',1)[1]
T = token()

def api(method, path, body=None, repo='smartfnb-agent-platform', timeout=30):
    req = urllib.request.Request(f'https://api.github.com/repos/tianqiongenze/{repo}{path}',
        data=json.dumps(body).encode() if body else None, method=method)
    req.add_header('Authorization', f'token {T}'); req.add_header('Accept','application/vnd.github+json')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return json.loads(e.read().decode())
    except Exception as e: return {'message': str(e)}

FILES = [
    ('docs/08-%E5%8A%9F%E8%83%BD%E4%B8%8E%E6%80%A7%E8%83%BD%E8%9E%8D%E5%90%88%E6%B5%8B%E8%AF%95%E6%8A%A5%E5%91%8AV3.md', r'D:\projects\连锁餐饮智能体\docs\08-功能与性能融合测试报告V3.md'),
    ('docs/09-%E5%B1%80%E5%9F%9F%E7%BD%91%E4%BA%BA%E5%B7%A5%E6%B5%8B%E8%AF%95%E6%93%8D%E4%BD%9C%E6%8C%87%E5%8D%97.md', r'D:\projects\连锁餐饮智能体\docs\09-局域网人工测试操作指南.md'),
    ('docs/07-ADR%E9%9B%86.md', r'D:\projects\连锁餐饮智能体\docs\07-ADR集.md'),
    ('README.md', r'D:\projects\连锁餐饮智能体\README.md'),
    ('smartfnb/java/portal/src/main/java/com/smartfnb/portal/Clients.java', r'D:\projects\连锁餐饮智能体\smartfnb\java\portal\src\main\java\com\smartfnb\portal\Clients.java'),
    ('smartfnb/web-admin/src/api.js', r'D:\projects\连锁餐饮智能体\smartfnb\web-admin\src\api.js'),
    ('smartfnb/web-admin/src/views/AgentChat.vue', r'D:\projects\连锁餐饮智能体\smartfnb\web-admin\src\views\AgentChat.vue'),
]
for path, local in FILES:
    ok = False
    for attempt in range(3):
        try:
            with open(local,'rb') as f: content = base64.b64encode(f.read()).decode()
            old = api('GET', f'/contents/{path}')
            body = {'message': f'V3: browser-regression fixes D-05/06/07 + perf reports + ADR-0016 ({os.path.basename(local)})',
                    'content': content, 'branch':'main'}
            if 'sha' in old: body['sha'] = old['sha']
            r = api('PUT', f'/contents/{path}', body, timeout=60)
            if 'commit' in r:
                print(path.split('/')[-1], 'OK'); ok = True; break
            print(path.split('/')[-1], 'retry', attempt, r.get('message'))
        except Exception as e:
            print(path.split('/')[-1], 'err', str(e)[:80])
    if not ok: print('FAILED:', local)
