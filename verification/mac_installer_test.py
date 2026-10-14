from pathlib import Path
import subprocess,os,uuid,plistlib,io,json,shutil
from PIL import Image
import argparse,sys
parser=argparse.ArgumentParser();parser.add_argument('package',type=Path);parser.add_argument('--work',type=Path,required=True)
args=parser.parse_args();package=args.package.resolve();h=args.work.resolve();h.mkdir(parents=True,exist_ok=True)
t=h/('mac-tests-'+uuid.uuid4().hex[:6]);t.mkdir();b=t/'bin';b.mkdir();app=t/'Mousecape.app/Contents/MacOS';app.mkdir(parents=True)
res=package/'PRTS Install.app/Contents/Resources'
bash=os.environ.get('PRTS_BASH') or shutil.which('bash') or ('D:/Git/bin/bash.exe' if os.name=='nt' else '/bin/bash')
def pos(p):
 p=p.resolve();return ('/'+p.drive[0].lower()+p.as_posix()[2:]) if os.name=='nt' else str(p)
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8',newline='\n')
 if s.startswith('#!'):p.chmod(0o755)
put(b/'mktemp',r'''#!/bin/sh
for arg do template=$arg; done
case "$template" in *XXXXXX) exec /usr/bin/mktemp "$@";; *) echo 'mktemp: template must end in XXXXXX' >&2; exit 1;; esac
''')
put(b/'osascript','#!/bin/sh\ncat >/dev/null\nif [ "$#" = 0 ]; then printf "%s\\n" "$SIM_CHOICE"; else printf "%s\\n" "$*" >> "$SIM_LOG"; fi\n')
put(b/'open','#!/bin/sh\nprintf "%s\\n" "$*" >> "$SIM_LOG"\n')
put(b/'plutil','#!/bin/sh\n[ "${SIM_BAD_PLIST:-0}" != 1 ]\n')
put(b/'sw_vers','#!/bin/sh\necho MOCK_MACOS\n')
put(app/'mousecloak','#!/bin/sh\n[ "${SIM_FAIL:-0}" != 1 ] || exit 1\necho "Applied theme successfully!"\n')
s=(package/'PRTS Install.app/Contents/MacOS/PRTSInstaller').read_text(encoding='utf8')
s=s.replace('RES="$HERE/../Resources"',f'RES="{pos(res)}"').replace('STATE="$HOME/Library/Application Support/PRTS Final"',f'STATE="{pos(t/"state")}"').replace('LIB="$HOME/Library/Application Support/Mousecape/capes"',f'LIB="{pos(t/"capes")}"')
s=s.replace('for candidate in /Applications/Mousecape.app "$HOME/Applications/Mousecape.app";',f'for candidate in "{pos(t/"Mousecape.app")}";')
for cmd in ['osascript','open','plutil','sw_vers','uname','file','cmp','grep']:s=s.replace('/usr/bin/'+cmd,cmd)
s=s.replace('/bin/cp','cp');put(t/'test.sh',s)
def run(choice,flags=None,args='',script=None):
 env=os.environ.copy();env.update(SIM_CHOICE=choice,SIM_LOG=pos(t/'messages'));env.update(flags or {})
 return subprocess.run([bash,'-c',f'export HOME="{pos(t)}" PATH="{pos(b)}:$PATH"; bash "{pos(script or t/"test.sh")}" {args}'],env=env,capture_output=True,timeout=20)
put(t/'old-mktemp.sh',s.replace('installer.XXXXXX','installer-XXXXXX.log'))
r=run('安装完整静态主题（兼容优先）',script=t/'old-mktemp.sh');assert r.returncode!=0 and not (t/'capes').exists()
for choice,flags in [('安装完整静态主题（兼容优先）',{}),('安装循环动画主题（可选）',{}),('安装循环动画主题（可选）',{'SIM_FAIL':'1'}),('恢复系统默认',{}),('恢复系统默认',{'SIM_FAIL':'1'}),('Cancel',{}),('打开 Mousecape 管理／还原',{})]:
 r=run(choice,flags);assert r.returncode==0,(choice,r.stdout,r.stderr)
old=(t/'capes/local.prts.final.Static.cape').read_bytes()
r=run('安装完整静态主题（兼容优先）',{'SIM_BAD_PLIST':'1'});assert r.returncode!=0 and (t/'capes/local.prts.final.Static.cape').read_bytes()==old
put(b/'cp','#!/bin/sh\nprintf partial > "$2"\nexit 1\n');r=run('安装完整静态主题（兼容优先）');assert r.returncode!=0 and (t/'capes/local.prts.final.Static.cape').read_bytes()==old;(b/'cp').unlink()
assert not (t/'state/lock').exists() and not list((t/'capes').glob('.prts-cape.*'))
(app/'mousecloak').rename(app/'disabled');assert run('安装完整静态主题（兼容优先）').returncode==0;(app/'disabled').rename(app/'mousecloak')
assert run('',args='--diagnose').returncode==0
put(t/'missing.sh',s.replace(pos(t/'Mousecape.app'),pos(t/'NoApp')))
(t/'messages').write_text('')
assert run('Cancel',script=t/'missing.sh').returncode==0
messages=(t/'messages').read_text(encoding='utf8');assert 'Mousecape/releases' in messages and '操作未完成' not in messages
for cape in res.glob('*.cape'):
 assert len(plistlib.loads(cape.read_bytes())['Cursors'])==40
 c=plistlib.loads(cape.read_bytes())
 for v in c['Cursors'].values():
  for data in v['Representations']:
   im=Image.open(io.BytesIO(data));im.load();assert im.height==im.width*v['FrameCount']
report='PASS macOS strict trailing-X mktemp regression (old version fails, fixed version passes); updated 40-role capes, full PNG decode; simulated install/static/animated/reset/cancel/no-helper/missing-dependency-guidance/diagnose/invalid-plist/copy-failure/logging/lock cleanup. Native AppleScript, Mousecape, macOS security and CPU architecture NOT tested.'
(h/'mac-test-results.txt').write_text(report,encoding='utf8');print(report)
