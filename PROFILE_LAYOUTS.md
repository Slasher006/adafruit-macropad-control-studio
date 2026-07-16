# Included MacroPad profiles

All built-in profiles use 5% key brightness. Keys are listed left-to-right, top-to-bottom.

Key colors use one functional risk spectrum: green (`#00FF66`) for safe/start/create actions, lime (`#B8FF00`) for navigation, yellow (`#FFD000`) for neutral toggles and selections, orange (`#FF7A00`) for caution or system-changing actions, and red (`#FF2020`) for destructive, stop, remove, close, or mute actions. Pressed keys turn white.

| Profile | Row 1 | Row 2 | Row 3 | Row 4 | Encoder press |
| --- | --- | --- | --- | --- | --- |
| VS Code | Command palette, Quick open, Explorer | Project search, Source control, Save | Format, Definition, Rename | Debug, Breakpoint, Problems | Toggle terminal |
| Firefox | Back, Forward, Reload | New tab, Close tab, Restore tab | Previous tab, Next tab, Address bar | Find, Downloads, Fullscreen | Address bar |
| VLC | Play/pause, Stop, Fullscreen | Previous, Jump back, Next | Slower, Normal speed, Faster | Volume down, Mute, Volume up | Play/pause |
| i3wm | Terminal, Launcher, Close | Focus left, Focus up, Focus right | Move left, Focus down, Move right | Horizontal split, Vertical split, Fullscreen | Toggle floating |
| Discord | Quick switcher, Channel search, Global search | Microphone mute, Deafen, Upload | Previous channel, Next channel, Emoji | Previous server, Next server, GIF | Quick switcher |
| LM Studio | New chat, New folder, Discover | Runtimes, Settings, Theme | Copy, Paste, Cut | Undo, Redo, Select all | New chat |
| Manjaro Terminal | Check updates, Upgrade, Pacman update | Search, Install, Build AUR | Remove, Package info, Orphans | Clean cache, Service status, Boot warnings | Cancel command |
| ComfyUI | Queue, Queue front, Interrupt | Undo, Redo, Delete | Save, Load, Select all | Collapse, Mute, Bypass | Settings |
| SSH | Connect, Custom port, Identity key | Jump host, Local tunnel, Remote tunnel | SCP upload, SCP download, SFTP | Keygen, Agent, Show config | Cancel/disconnect |
| Audio Controls | Mute, Volume down, Volume up | Previous, Play/pause, Next | Stop, Volume down 5, Volume up 5 | Record, Eject, Play/pause | Mute |
| Quicklaunch | Firefox, Terminal, VS Code | Caja, Discord, LM Studio | — | — | Application launcher |
| System Control | Restart i3, Reboot, Shutdown in 60 min | Shutdown now, Cancel shutdown, — | — | — | Terminal interrupt |

The Manjaro Terminal and SSH profiles insert editable command templates into the focused terminal but deliberately do not press Enter. Review or complete the command, then run it yourself.

The i3wm profile uses `Super`/`Mod4` (`GUI` in the profile schema), which is the common Manjaro i3 setup. Change `GUI` to `ALT` in the configurator if your `$mod` is `Mod1`.

System Control executes its reboot and shutdown commands after opening a terminal and waiting 800 ms for it to receive focus. Red keys act immediately; the green Cancel key runs `shutdown -c` to cancel a scheduled shutdown.

## Shortcut references

- [VS Code default Linux shortcuts](https://code.visualstudio.com/docs/reference/default-keybindings)
- [Firefox keyboard shortcuts](https://support.mozilla.org/en-US/kb/keyboard-shortcuts-perform-firefox-tasks-quickly)
- [VLC most-used hotkeys](https://docs.videolan.me/vlc-user/desktop/3.0/en/basic/hotkeys.html)
- [i3 default keybindings](https://i3wm.org/docs/userguide.html)
- [Discord shortcuts and navigation](https://support.discord.com/hc/en-us/articles/31232432266647-Discord-Commands-Shortcuts-and-Navigation-Guide)
- [LM Studio chat, model, settings, theme, and runtime shortcuts](https://lmstudio.ai/docs/app)
- [ComfyUI keyboard shortcuts](https://docs.comfy.org/interface/shortcuts)
- [Manjaro Pamac commands](https://wiki.manjaro.org/index.php?title=Pamac) and [system-maintenance guidance](https://wiki.manjaro.org/index.php?title=System_Maintenance)
- [OpenSSH client](https://man.openbsd.org/ssh), [SCP](https://man.openbsd.org/scp.1), and [key generation](https://man.openbsd.org/ssh-keygen)
