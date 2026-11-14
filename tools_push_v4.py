# -*- coding: utf-8 -*-
"""push_v4.py — V4审查报告与README推送主仓库(Contents API, 带重试)"""
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
    ('docs/11-V4%E5%AE%A1%E6%9F%A5%E4%B8%8E%E4%BC%98%E5%8C%96%E9%87%8D%E6%9E%84%E6%96%B9%E6%A1%88(%E8%81%94%E7%BD%91%E5%AF%B9%E6%A0%87).md', r'D:\projects\连锁餐饮智能体\docs\11-V4审查与优化重构方案(联网对标).md'),
    ('README.md', r'D:\projects\连锁餐饮智能体\README.md'),
]
for path, local in FILES:
    ok = False
    for attempt in range(3):
        try:
            with open(local,'rb') as f: content = base64.b64encode(f.read()).decode()
            old = api('GET', f'/contents/{path}?ref=main')
            body = {'message': f'V4: 审查报告入库+README索引更新 ({os.path.basename(local)})', 'content': content, 'branch':'main'}
            if 'sha' in old: body['sha'] = old['sha']
            r = api('PUT', f'/contents/{path}', body)
            if 'commit' in r:
                print(os.path.basename(local), 'OK'); ok = True; break
            print(os.path.basename(local), 'retry', attempt, r.get('message'))
        except Exception as e:
            print(os.path.basename(local), 'err', str(e)[:100])
    if not ok: print('FAILED:', local)
