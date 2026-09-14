<h1 align="center">Python script to enable audio support on Chrome devices</h1>

<h4 align="center">Note: A full install of a supported Linux distro is required! Live USB sessions will not work.</h4>

# Instructions
1.     git clone --depth 1 https://github.com/WeirdTreeThing/chromebook-linux-audio
2.     cd chromebook-linux-audio
3.     ./setup-audio

# Requirements
1. `python 3.10 or newer`
2. `git`

# Supported Devices
See the [Chrultrabook docs](https://docs.chrultrabook.com/docs/devices.html) for more info.

# Officially Supported Distros
1. Alpine Linux edge
2. Arch Linux
3. Debian Trixie
4. Fedora 43
5. OpenSUSE Tumbleweed
6. Ubuntu 25.10
7. Void Linux

# Other Distros
Other distros will likely work but will require you to manually install packages. The script will print a list of any packages you may need to install. It is required to have a relatively modern distro (no old LTS releases) as those will be missing important fixes.

# HP Elite Dragonfly Chromebook (Redrix) microphone

Redrix uses the first two channels of its four-channel DMIC PCM. Its ChromeOS configuration uses channels 0/1; the generic four-channel UCM configuration previously also exposed channels 2/3 as `Internal Microphone 2`. On the tested machine those extra channels carried a constant value and produced a pop when recording started. Removing Mic2 depends on the Redrix change in the `alsa-ucm-conf-cros` configuration installed by this script; the WirePlumber configuration below does not replace that UCM change.

For DMI product name `Redrix`, the script installs an internal-microphone priority rule with WirePlumber 0.5 or newer. This avoids automatic selection of the speaker monitor on older WirePlumber versions; WirePlumber 0.5.14 also fixes that default-source selection bug upstream. With WirePlumber 0.5.13 or newer and PipeWire 1.4.0 or newer, the script additionally installs a fixed +20 dB software preamp for Mic1. Older or undetected versions produce a message explaining that the gain was not installed. After upgrading the audio stack, rerun this script.

The +20 dB gain is an empirical compensation validated by test tones and a successful voice recording on one Redrix. The underlying reason for its low raw microphone level has not been established; this is not a firmware or topology repair, nor a calibration for other boards. A low input-volume setting can further attenuate the signal. After rebooting, select `Internal Microphone 1` in the desktop sound settings, start with input volume at 100%, and check a normal voice recording. Reduce the input volume if loud speech clips. The installer does not change per-user source selection or saved volume.

Before migrating an existing manual microphone fix, disable its preamp rules, including any in `~/.config/wireplumber/wireplumber.conf.d/`. WirePlumber merges configuration fragments across directories; leaving two +20 dB preamps active can apply +40 dB. This script manages only `60-chromebook-redrix-mic-priority.conf` and `61-chromebook-redrix-mic-gain.conf` in `/etc/wireplumber/wireplumber.conf.d/` and leaves user configuration untouched. Repeated runs replace those files and remove the applicable managed files if the detected versions no longer support them. If the system disk is moved to another board, rerunning the script removes both managed Redrix files while preserving other configuration.

# Donations
If you would like to support the work I do, consider donating [here](https://paypal.me/weirdtreething).
