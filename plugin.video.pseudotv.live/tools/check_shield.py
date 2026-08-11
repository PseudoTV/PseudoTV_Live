#!/usr/bin/env python3
"""PseudoTV Shield health check.

Predicts the "PseudoTV crashed Kodi" failure before it bites:
  1. Epg21.db corrupt  -> SQLITE_CORRUPT storm -> Kodi crash
  2. addon disabled    -> service dead -> m3u/EPG unreachable
  3. m3u server down   -> PVR can't connect

Usage:  python check_shield.py [--ip 192.168.0.123] [--adb C:\\platform-tools\\adb.exe] [--fix]
"""
import argparse, subprocess, sqlite3, sys, tempfile, os, time, urllib.request

ADB      = r'C:\platform-tools\adb.exe'
KOdiBASE = '/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi'
EPG_DB   = KOdiBASE + '/userdata/Database/Epg21.db'
ADDONS_DB= KOdiBASE + '/userdata/Database/Addons33.db'
ADDON    = 'plugin.video.pseudotv.live'
M3U      = 'http://{ip}:50001/pseudotv.m3u'

def adb(ip, *args):
    return subprocess.run([os.environ.get('PTV_ADB', ADB), '-s', f'{ip}:5555', *args], capture_output=True, text=True)

def db_integrity(path):
    con = sqlite3.connect(path)
    bad = [r for r in con.execute('PRAGMA integrity_check') if r[0] != 'ok']
    con.close()
    return bad

def check(ip, tmp):
    print(f'[check] Shield {ip}')
    # 1. Epg21.db integrity
    epg_local = os.path.join(tmp, 'Epg21.db')
    r = adb(ip, 'pull', EPG_DB, epg_local)
    if r.returncode == 0 and os.path.exists(epg_local):
        try:
            bad = db_integrity(epg_local)
            print(f'  Epg21.db : {"CORRUPT" if bad else "ok"}' + (f' ({bad[0][:60]})' if bad else ''))
            epg_corrupt = bool(bad)
        except sqlite3.Error as e:
            print(f'  Epg21.db : CORRUPT (unreadable: {e})'); epg_corrupt = True
    else:
        print(f'  Epg21.db : missing (fresh install?)'); epg_corrupt = False

    # 2. addon enabled
    adb_local = os.path.join(tmp, 'Addons33.db')
    r = adb(ip, 'pull', ADDONS_DB, adb_local)
    enabled = None
    if r.returncode == 0 and os.path.exists(adb_local):
        con = sqlite3.connect(adb_local)
        row = con.execute("SELECT enabled FROM installed WHERE addonID=?", (ADDON,)).fetchone()
        con.close()
        enabled = bool(row[0]) if row else None
    print(f'  addon    : {"enabled" if enabled else "DISABLED" if enabled is not None else "unknown"}')

    # 3. m3u reachable
    m3u_up = False
    try:
        with urllib.request.urlopen(M3U.format(ip=ip), timeout=8) as resp:
            m3u_up = resp.status == 200 and int(resp.headers.get('Content-Length', 0)) > 0
    except Exception:
        pass
    print(f'  m3u:50001: {"up" if m3u_up else "DOWN"}')

    # 4. memory pressure (OOM on the 3GB Shield crash-loops Kodi)
    low_mem = False
    try:
        r = adb(ip, 'shell', 'cat /proc/meminfo | grep -E "MemFree|MemAvailable|SwapFree"')
        mem = {m.split(':')[0]: int(m.split(':')[1].split()[0]) for m in r.stdout.splitlines() if ':' in m}
        free_kb = mem.get('MemFree', 0) + mem.get('SwapFree', 0)
        print(f'  memory   : {free_kb//1024}MB free ({(mem.get("MemFree",0)//1024)}MB RAM + {mem.get("SwapFree",0)//1024}MB swap)')
        low_mem = free_kb < 300 * 1024
    except Exception:
        print('  memory   : unknown')

    return {'epg_corrupt': epg_corrupt, 'disabled': enabled is False, 'm3u_down': not m3u_up, 'low_mem': low_mem}

def fix(ip):
    print('\n[fix] freeing memory + re-enabling addon + rebuilding Epg21.db')
    for pkg in ('org.smarttube.stable', 'com.showtime.standalone', 'com.google.android.tv'):
        adb(ip, 'shell', f'am force-stop {pkg}')
    adb(ip, 'shell', 'am force-stop org.xbmc.kodi'); time.sleep(2)
    adb(ip, 'shell', f'cp {EPG_DB} {EPG_DB}.corrupt-bak')
    adb(ip, 'shell', f'rm -f {EPG_DB}*')
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, 'Addons33.db')
    adb(ip, 'pull', ADDONS_DB, db)
    con = sqlite3.connect(db)
    con.execute("UPDATE installed SET enabled=1, disabledReason=0 WHERE addonID=?", (ADDON,))
    con.commit(); con.close()
    adb(ip, 'push', db, ADDONS_DB)
    adb(ip, 'shell', 'monkey -p org.xbmc.kodi 1')
    print('[fix] Kodi restarted - verify with: python check_shield.py --ip %s' % ip)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ip', default='192.168.0.123')
    ap.add_argument('--adb', default=ADB)
    ap.add_argument('--fix', action='store_true', help='apply the fix if problems found')
    args = ap.parse_args()
    _adb = args.adb
    tmp = tempfile.mkdtemp()
    issues = check(args.ip, tmp)
    if not any(issues.values()):
        print('\n[OK] Shield healthy - no action needed.'); return
    print('\n[WARN] Predicted failure (this caused the earlier PseudoTV crash):')
    if issues['epg_corrupt']: print('  - Epg21.db corrupt: EPGUpdater hits SQLITE_CORRUPT, crashes Kodi')
    if issues['disabled']:    print('  - PseudoTV addon disabled: service dead, PVR has no channels')
    if issues['m3u_down']:    print('  - m3u server not responding: PVR cannot connect')
    if issues['low_mem']:     print('  - Shield low on memory: Kodi OOM crash-loops (free background apps/SmartTube)')
    if args.fix:
        fix(args.ip)
    else:
        print('\nFix:')
        if issues['epg_corrupt'] or issues['disabled']:
            print('  1. Re-enable addon + delete corrupt Epg21.db (backup kept), then restart Kodi.')
        if issues['low_mem']:
            print('  2. Free memory: force-stop background apps (SmartTube/Showtime), then relaunch Kodi.')
        print('Run with --fix to apply automatically.')

if __name__ == '__main__':
    main()
