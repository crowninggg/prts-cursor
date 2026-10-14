from pathlib import Path
import subprocess,os,json,uuid,shutil,hashlib
import argparse,sys
parser=argparse.ArgumentParser()
parser.add_argument('package',type=Path)
parser.add_argument('--work',type=Path,required=True)
args=parser.parse_args();package=args.package.resolve();h=args.work.resolve();h.mkdir(parents=True,exist_ok=True)
t=h/('linux-tests-'+uuid.uuid4().hex[:6]);t.mkdir();b=t/'bin';b.mkdir()
bash=os.environ.get('PRTS_BASH') or shutil.which('bash') or ('D:/Git/bin/bash.exe' if os.name=='nt' else '/bin/bash');checks=[]
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8',newline='\n')
 if s.startswith('#!'):p.chmod(0o755)
def pos(p):
 p=p.resolve();return ('/'+p.drive[0].lower()+p.as_posix()[2:]) if os.name=='nt' else str(p)

# BSD/BusyBox require trailing Xs; Git Bash's GNU mktemp alone masked this defect.
put(b/'mktemp',r'''#!/bin/sh
for arg do template=$arg; done
case "$template" in *XXXXXX) exec /usr/bin/mktemp "$@";; *) echo 'mktemp: template must end in XXXXXX' >&2; exit 1;; esac
''')
put(b/'gsettings',r'''#!/bin/sh
printf '%s\n' "$*" >> "$SIM_LOG"
case "$1" in
 list-schemas) printf '%s\n' org.gnome.desktop.interface org.cinnamon.desktop.interface org.mate.peripherals-mouse;;
 writable) if [ "${SIM_READONLY:-0}" = 1 ]; then echo false; else echo true; fi;;
 get) case "$3" in *size) echo 48;; *) if [ -f "$SIM_THEME" ]; then cat "$SIM_THEME"; else echo "'Before Theme'"; fi;; esac;;
 set) [ "${SIM_FAIL:-0}" != 1 ] || exit 1; [ "${SIM_NOOP:-0}" != 1 ] || exit 0; printf '%s\n' "$4" > "$SIM_THEME";;
esac
''')
put(b/'kreadconfig6',r'''#!/bin/sh
case "$*" in *cursorSize*) echo 48;; *) if [ -f "$SIM_THEME" ]; then cat "$SIM_THEME"; else echo breeze_cursors; fi;; esac
''')
put(b/'kwriteconfig6',r'''#!/bin/sh
printf '%s\n' "$*" >> "$SIM_LOG"
for arg do value=$arg; done
printf '%s\n' "$value" > "$SIM_THEME"
''')
put(b/'plasma-apply-cursortheme',r'''#!/bin/sh
printf '%s\n' "plasma $*" >> "$SIM_LOG"
[ "$1" = --size ] && [ "$2" = 48 ] || exit 7
[ "${SIM_FAIL:-0}" != 1 ] || exit 1
printf '%s\n' "$3" > "$SIM_THEME"
[ "${SIM_REFRESH_FAIL:-0}" != 1 ] || exit 1
''')
put(b/'xfconf-query',r'''#!/bin/sh
case "$*" in *CursorThemeSize*) echo 48;; *" -s "*) printf '%s\n' "$*" >> "$SIM_LOG"; printf '%s\n' "$6" > "$SIM_THEME";; *) if [ -f "$SIM_THEME" ]; then cat "$SIM_THEME"; else echo OldXFCE; fi;; esac
''')
# Small fixtures exercise all actual install code without repeated 70 MB disk copies.
fixture=t/'包';fixture.mkdir();shutil.copy2(package/'INSTALL.sh',fixture/'INSTALL.sh')
for theme in ['PRTS-Final','PRTS-Final-Static']:
 for n in ['index.theme','cursors/left_ptr','cursors/pointer','cursors/text','cursors_scalable/default/metadata.json']:put(fixture/'files'/theme/n,'fixture')
 folder=fixture/'files'/theme
 put(folder/'checksums.sha256','\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(folder).as_posix() for p in sorted(folder.rglob('*')) if p.is_file())+'\n')
base=os.environ.copy();base.pop('DISPLAY',None);base.pop('WAYLAND_DISPLAY',None);base.pop('SUDO_USER',None)
def run(desk,action,root=None,extra=None,session='wayland',input_text=None):
 root=root or t/('用户 '+desk.replace(':','_'));root.mkdir(exist_ok=True)
 e=base.copy();e.update(SIM_LOG=pos(root/'commands'),SIM_THEME=pos(root/'theme'));e.update(extra or {})
 cmd=f'export HOME="{pos(root)}" PATH="{pos(b)}:$PATH" XDG_DATA_HOME="{pos(root/"data")}" XDG_STATE_HOME="{pos(root/"state")}" XDG_CURRENT_DESKTOP="{desk}" XDG_SESSION_TYPE="{session}"; sh "{pos(fixture/"INSTALL.sh")}" {action}'
 r=subprocess.run([bash,'-c',cmd],env=e,capture_output=True,input=input_text,timeout=25);return r,root
fixed=(fixture/'INSTALL.sh').read_text(encoding='utf8')
put(fixture/'INSTALL.sh',fixed.replace('operation.XXXXXX','operation-XXXXXX.log'))
r,_=run('GNOME','static',t/'old-mktemp');assert r.returncode==1 and b'XXXXXX' in r.stderr
put(fixture/'INSTALL.sh',fixed)
for desk,backend in [('ubuntu:GNOME','gnome'),('ubuntu:KDE','plasma'),('KDE','plasma'),('X-Cinnamon','cinnamon'),('MATE','mate'),('XFCE','xfce'),('Budgie:GNOME','gnome'),('LXQt','manual'),('sway','manual'),('Hyprland','manual')]:
 for act in ['static','install']:
  r,root=run(desk,act);assert r.returncode==0,(desk,act,r.stdout.decode(),r.stderr.decode())
 assert (root/'data/icons/PRTS-Final/cursors/left_ptr').exists()
 if backend!='manual':
  saved=(root/'state/prts-cursors/desktops'/backend/'theme').read_bytes()
  r,_=run(desk,'restore');assert r.returncode==0 and (root/'theme').read_bytes()==saved,(desk,r.stdout)
 else:assert not (root/'theme').exists()
 checks.append('PASS '+desk+' install/static/'+('restore' if backend!='manual' else 'safe manual fallback'))
# Independent desktop backups on same account, now permits switching instead of refusing it.
root=t/'shared';r,_=run('GNOME','static',root);assert r.returncode==0
(root/'theme').write_text('breeze_cursors\n');r,_=run('ubuntu:KDE','install',root);assert r.returncode==0
assert (root/'state/prts-cursors/desktops/gnome/theme').read_text().strip()=="'Before Theme'"
assert (root/'state/prts-cursors/desktops/plasma/theme').read_text().strip()=='breeze_cursors'
# read-only/no-op/failure must not say apply succeeded.
for mode in ['SIM_READONLY','SIM_NOOP','SIM_FAIL']:
 r,root=run('GNOME','static',t/mode,{mode:'1'})
 if mode=='SIM_READONLY':assert r.returncode==0 and not (root/'theme').exists()
 else:assert r.returncode==1
 assert not (root/'state/prts-cursors/lock').exists()
 assert '已安装 PRTS-Final-Static，且桌面设置已读回' not in r.stdout.decode()
# KDE can save theme but report failed live refresh: report relogin without undoing valid setting.
r,root=run('KDE','static',t/'kde-refresh',{'SIM_REFRESH_FAIL':'1'});assert r.returncode==0 and '注销' in r.stdout.decode()
# No helper -> config-only route; retain user's size.
(b/'plasma-apply-cursortheme').rename(b/'plasma-disabled');r,root=run('KDE','static',t/'kde-config');assert r.returncode==0 and '即时应用' in r.stdout.decode();(b/'plasma-disabled').rename(b/'plasma-apply-cursortheme')
# Migration of older backup, no overwriting first pre-install choice.
root=t/'migration';put(root/'state/prts-cursors/before-kind','gsettings');put(root/'state/prts-cursors/before-schema','org.gnome.desktop.interface');put(root/'state/prts-cursors/before-theme',"'Original Saved'\n")
r,_=run('GNOME','static',root);assert r.returncode==0
assert (root/'state/prts-cursors/desktops/gnome/theme').read_text().strip()=="'Original Saved'"
# Keep conflict directory intact; diagnose is read-only for themes.
root=t/'conflict';put(root/'.icons/PRTS-Final-Static/sentinel','keep');r,_=run('GNOME','static',root);assert r.returncode==0 and (root/'.icons/PRTS-Final-Static/sentinel').read_text()=='keep'
r,root=run('GNOME','diagnose',t/'diagnose');assert r.returncode==0 and not (root/'data').exists() and not (root/'theme').exists()
r,root=run('GNOME','static',t/'sudo',{'SUDO_USER':'somebody'});assert r.returncode==2 and not (root/'data').exists()
# Both session types use actual desktop APIs, not assumptions based on distro.
r,root=run('GNOME','static',t/'x11',session='x11');assert r.returncode==0
checks.append('PASS per-desktop backups, previous-backup migration, read-only settings, no-op detection, failure rollback path, KDE preserve size/config-only/relogin, legacy conflict, diagnose no theme writes, sudo rejected, X11/Wayland branches')
# Mixed installed Plasma helpers: newest reader + older writer still works.
(b/'plasma-apply-cursortheme').rename(b/'plasma-disabled')
(b/'kwriteconfig6').rename(b/'kwriteconfig5')
r,root=run('KDE','static',t/'mixed-kde-tools');assert r.returncode==0 and '即时应用' in r.stdout.decode()
(b/'kwriteconfig5').rename(b/'kwriteconfig6')
(b/'plasma-disabled').rename(b/'plasma-apply-cursortheme')
# An incomplete extraction must not replace an already installed theme.
broken=fixture/'files/PRTS-Final/cursors/text';saved=broken.read_bytes();broken.unlink()
root=t/'incomplete';put(root/'data/icons/PRTS-Final/sentinel','keep')
r,_=run('GNOME','install',root);assert r.returncode==1 and (root/'data/icons/PRTS-Final/sentinel').read_text()=='keep'
broken.write_bytes(saved)
# Concurrent install lock must never be stolen.
root=t/'locked';(root/'state/prts-cursors/lock').mkdir(parents=True)
r,_=run('GNOME','static',root);assert r.returncode==1 and (root/'state/prts-cursors/lock').is_dir()
assert not (root/'data/icons/PRTS-Final-Static').exists()
checks.append('PASS mixed Plasma 5/6 helpers, incomplete package preserves installed theme, existing lock preserved')
put(b/'zenity',r'''#!/bin/sh
if [ "${SIM_CANCEL:-0}" = 1 ]; then exit 1; fi
echo 'GTK display unavailable' >&2; exit 1
''')
put(b/'kdialog','#!/bin/sh\necho Qt-failed >&2\nexit 2\n')
r,root=run('GNOME','menu',t/'gui-fallback',{'DISPLAY':':99'},input_text=b'1\n')
assert r.returncode==0 and (root/'theme').read_text().strip()=="'PRTS-Final-Static'"
r,root=run('GNOME','menu',t/'gui-cancel',{'DISPLAY':':99','SIM_CANCEL':'1'},input_text=b'1\n')
assert r.returncode==0 and not (root/'data').exists()
r,root=run('KDE','static',t/'kde-helper-fails',{'SIM_FAIL':'1'})
assert r.returncode==0 and (root/'theme').read_text().strip()=='PRTS-Final-Static' and '注销' in r.stdout.decode()
source=fixture/'files/PRTS-Final/cursors/left_ptr';old=source.read_bytes();source.write_text('corrupted')
root=t/'checksum-fail';put(root/'data/icons/PRTS-Final/sentinel','keep')
r,_=run('GNOME','install',root);assert r.returncode==1 and (root/'data/icons/PRTS-Final/sentinel').read_text()=='keep'
assert '校验失败' in r.stdout.decode();source.write_bytes(old)
checks.append('PASS strict trailing-X mktemp regression, GUI failure -> terminal menu, Cancel stays canceled, KDE helper failure -> verified config, corrupt resources rejected before replacing theme')
(h/'linux-test-results.txt').write_text('\n'.join(checks),encoding='utf8');(h/'last-test-dir.txt').write_text(str(t));print('\n'.join(checks))
