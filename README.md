<h1 align="center">Python script to enable audio support on Chrome devices</h1>

# Instructions
1.     git clone https://github.com/WeirdTreeThing/chromebook-linux-audio
2.     cd chromebook-linux-audio
3.     ./setup-audio

# Requirements
1. `python 3.10`
2. `git`

# Supported Devices
See the [Linux compatibility sheet](https://docs.google.com/spreadsheets/d/1udREts28cIrCL5tnPj3WpnOPOhWk76g3--tfWbtxi6Q/edit#gid=0) for more info.

# Officially Supported distros
1. Arch Linux
2. Fedora 38
3. PopOS[^1]
4. Debian 12[^2]
5. OpenSUSE
6. Void Linux

[^1]: Depending on the device, PopOS will require a custom kernel

[^2]: Debian will require a custom kernel.

For both Debian and PopOS, you can get a custom kernel [here](https://elly.rocks/tmp/BUILDROOT/linux-image-6.1.27chrultrabook-fixups_6.1.27chrultrabook-fixups-8_amd64.deb).

# Other Distros
Other distros will likely work but will require you to manually install packages, with the exception of Ubuntu and Ubuntu based distros like Linux Mint. These have outdated packages and may or may not work, you are on your own if you choose to use these.
