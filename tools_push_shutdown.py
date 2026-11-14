# -*- coding: utf-8 -*-
"""tools_push_shutdown.py — 清退收尾推送(Contents API): docs/10-停机腾退与恢复手册.md + README.md
仿 tools_push_v3.py：token 经 git credential fill 获取且绝不打印；PUT 时带已有文件的 sha。
本机 GCM 存有多个 github 账号：credential fill 必须显式带 username=tianqiongenze，
否则 GCM 弹 "Select an account" 交互窗导致无人值守时永久挂起。
"""
import base64, json, subprocess, urllib.request, os, sys
from urllib.parse import quote

def token():
    env = dict(os.environ)
    env['GCM_INTERACTIVE'] = 'never'
    env['GIT_TERMINAL_PROMPT'] = '0'
    r = subprocess.run(['git', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\nusername=tianqiongenze\n\n',
                       capture_output=True, text=True, env=env)
    for line in r.stdout.splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
T = token()

def api(method, path, body=None, timeout=30):
    req = urllib.request.Request(
        f'https://api.github.com/repos/tianqiongenze/smartfnb-agent-platform{path}',
        data=json.dumps(body).encode() if body else None, method=method)
    req.add_header('Authorization', f'token {T}')
    req.add_header('Accept', 'application/vnd.github+json')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())
    except Exception as e:
        return {'message': str(e)}

FILES = [
    ('docs/10-停机腾退与恢复手册.md', r'D:\projects\连锁餐饮智能体\docs\10-停机腾退与恢复手册.md'),
    ('README.md', r'D:\projects\连锁餐饮智能体\README.md'),
]
failed = False
for path, local in FILES:
    ok = False
    for attempt in range(3):
        try:
            with open(local, 'rb') as f:
                content = base64.b64encode(f.read()).decode()
            old = api('GET', f'/contents/{quote(path)}')
            body = {'message': f'chore: 清退收尾 — 新增停机腾退与恢复手册V5 + README索引补10条目 ({os.path.basename(local)})',
                    'content': content, 'branch': 'main'}
            if 'sha' in old:
                body['sha'] = old['sha']
            r = api('PUT', f'/contents/{quote(path)}', body, timeout=60)
            if 'commit' in r:
                print(path.split('/')[-1], 'OK commit', r['commit']['sha'][:10])
                ok = True
                break
            print(path.split('/')[-1], 'retry', attempt, r.get('message'))
        except Exception as e:
            print(path.split('/')[-1], 'err', str(e)[:80])
    if not ok:
        print('FAILED:', local)
        failed = True
sys.exit(1 if failed else 0)
