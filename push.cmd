cd\
D:
cd\GitHub\PseudoTV_Live

start "" /min cmd /c rd /s /q D:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live\
start "" /wait RoboCopy.exe  "C:\portable_data\addons\plugin.video.pseudotv.live" "D:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" *.* /E /IM /IS
start "" /wait addon_generator.py

start "" /wait /min cmd /c rd /s /q \\192.168.0.51\xbmc\portable_data\addons\plugin.video.pseudotv.live\
start "" /wait robocopy  "D:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" "\\192.168.0.51\xbmc\portable_data\addons\plugin.video.pseudotv.live\\" *.* /E /IM /IS

start "" /wait /min cmd /c rd /s /q \\192.168.0.123\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\plugin.video.pseudotv.live\
start "" /wait robocopy "D:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" "\\192.168.0.123\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\plugin.video.pseudotv.live\\" *.* /E /COPY:DT /NODCOPY

start "" /wait /min cmd /c rd /s /q \\192.168.0.124\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\plugin.video.pseudotv.live\
start "" /wait robocopy "D:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" "\\192.168.0.124\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\plugin.video.pseudotv.live\\" *.* /E /COPY:DT /NODCOPY


