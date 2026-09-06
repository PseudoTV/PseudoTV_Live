# Fix: Android TV SyncChannelJobService Crash Loop

## Symptom

Kodi starts, then immediately crashes and restarts in a loop. PseudoTV shows a notification:

> Kodi is crash-looping on Android TV channel sync.
> To fix, disable the sync service via ADB.

## Cause

Kodi's `SyncChannelJobService` is an Android TV channel sync component that runs as a `JobService`. When Kodi's PVR/EPG backend is in a bad state (corrupt database, incomplete startup), this service crashes — and Android's job scheduler restarts it, creating a crash loop that prevents Kodi from ever fully starting.

**This is a Kodi issue, not a PseudoTV issue.** PseudoTV does not use Android TV channels.

## Fix (via ADB)

### Prerequisites

- [ADB (Android Debug Bridge)](https://developer.android.com/tools/adb) installed on your PC
- Shield connected to the same network
- "Network Debugging" enabled in Shield Developer Options

### Steps

**1. Connect to the Shield**

```bash
# Living Room Shield
adb connect 192.168.0.123:5555

# Bedroom Shield
adb connect 192.168.0.124:5555
```

**2. Verify connection**

```bash
adb -s 192.168.0.123:5555 shell getprop ro.product.model
# Should return: SHIELD Android TV
```

**3. Disable the crashing service**

```bash
# Living Room Shield
adb -s 192.168.0.123:5555 shell pm disable-user --user 0 org.xbmc.kodi/.channels.SyncChannelJobService

# Bedroom Shield
adb -s 192.168.0.124:5555 shell pm disable-user --user 0 org.xbmc.kodi/.channels.SyncChannelJobService
```

**4. Force-stop Kodi to break the crash loop**

```bash
adb -s 192.168.0.123:5555 shell am force-stop org.xbmc.kodi
```

**5. Reopen Kodi normally**

The crash loop should be gone. Kodi will start normally.

## Re-enable (if needed)

If you want to re-enable Android TV channel sync later:

```bash
adb -s 192.168.0.123:5555 shell pm enable --user 0 org.xbmc.kodi/.channels.SyncChannelJobService
```

**Note:** Re-enabling may cause the crash loop to return if the underlying PVR/EPG issue hasn't been resolved.

## Notes

- The disable survives reboots but **not** a Kodi reinstall/update (the component gets re-enabled on app update).
- This only disables the Android TV "Live Channels" integration. Kodi's PVR system, PseudoTV, and all other functionality are unaffected.
- If the crash loop returns after a Kodi update, re-run the disable command.
