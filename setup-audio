#!/usr/bin/env python3

import argparse
import json
import os
import sys
from functions import *

# parse arguments from the cli. Only for testing/advanced use.
def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_name", type=str, nargs=1, default=[""],
                        help="Override board name.")
    parser.add_argument("--enable-debug", action='store_const', const="Enabling", dest="debug",
                        help="Enable audio debugging.")
    parser.add_argument("--disable-debug", action='store_const', const="Disabling", dest="debug",
                        help="Disable audio debugging.")
    parser.add_argument("--force-avs-install", action="store_true", dest="force_avs_install", default=False,
                        help="DANGEROUS: Force enable AVS install. MIGHT CAUSE PERMANENT DAMAGE TO SPEAKERS!")
    return parser.parse_args()


def avs_audio(board, username):
    if args.debug:
        print_status(f"{args.debug} AVS debugging")
        if args.debug == "Enabling":
            cpfile("conf/avs/snd-avs-dbg.conf", "/etc/modprobe.d/snd-avs-dbg.conf")
        else:
            rmfile("/etc/modprobe.d/snd-avs-dbg.conf")
        print_status("Done, please reboot for changes to take effect.")
        exit()

    print_status("Installing AVS")
    # Only show the warning to devices with max98357a
    override_avs = False
    if path_exists("/sys/bus/acpi/devices/MX98357A:00"):
        if args.force_avs_install:
            print_error(
                "WARNING: Your device has max98357a and can cause permanent damage to your speakers if you set the volume too loud!")
            user_input = input('Type "I understand the risk of permanently damaging my speakers" in all caps to continue: ')
            while user_input != "I UNDERSTAND THE RISK OF PERMANENTLY DAMAGING MY SPEAKERS":
                user_input = input(
                    'Type "I understand the risk of permanently damaging my speakers" in all caps to continue: ')
            override_avs = True
        else:
            print_error(
                "WARNING: Your device has max98357a and can cause permanent damage to your speakers if you "
                "set the volume too loud! As a safety precaution devices with max98357a have speakers "
                "disabled until a fix is in place. Headphones and HDMI audio are safe from this.")
            print_question("If you want to disable this check, restart the script with --force-avs-install")

            user_input = input(
                'Type "I Understand my speakers will not work since my device has max98357a!" in all caps to continue: ')
            while user_input != "I UNDERSTAND MY SPEAKERS WILL NOT WORK IF MY DEVICE HAS MAX98357A!":
                user_input = input(
                    'Type "I Understand my speakers will not work since my device has max98357a!" in all caps to continue: ')
            override_avs = False

    # Copy ucms
    print_status("Installing UCM configuration")
    rmdir("/tmp/chromebook-ucm-conf")
    bash("git clone https://github.com/WeirdTreeThing/chromebook-ucm-conf /tmp/chromebook-ucm-conf")
    cpdir("/tmp/chromebook-ucm-conf/avs", "/usr/share/alsa/ucm2/conf.d/")

    # avs tplg is from https://github.com/thesofproject/avs-topology-xml
    print_status("Installing topology")
    cpdir("conf/avs/tplg", "/lib/firmware/intel/avs")
    print_status("Installing modprobe config")
    cpfile("conf/avs/snd-avs.conf", "/etc/modprobe.d/snd-avs.conf")

    # Install wireplumber config for dmic if wireplumber is installed on the system
    if path_exists("/usr/bin/wireplumber"):
        print_status("Installing wireplumber config (fixes internal mic)")
        mkdir("/etc/wireplumber/main.lua.d/", create_parents=True)
        cpfile("conf/avs/51-avs-dmic.lua", "/etc/wireplumber/main.lua.d/51-avs-dmic.lua")

    # updated avs dsp firmware recently got merged upstream but is not packaged in any distro yet
    print_status("Installing AVS firmware")
    mkdir("/lib/firmware/intel/avs/skl")
    mkdir("/lib/firmware/intel/avs/apl")
    urlretrieve("https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/intel/avs/apl/"
                "dsp_basefw.bin", filename="/lib/firmware/intel/avs/apl/dsp_basefw.bin")
    urlretrieve("https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/intel/avs/skl/"
                "dsp_basefw.bin", filename="/lib/firmware/intel/avs/skl/dsp_basefw.bin")

    # Install specific blobs for rammus and nocturne
    if board in ["rammus", "shyvana", "leona"]:
        extract_blobs("rammus")
        print_error("WARNING: You will need a chromeos kernel for speakers to work!")
    if board == "nocturne":
        extract_blobs("nocturne")
        print_error("WARNING: You will need a chromeos kernel for speakers to work!")

    # Delete topology for max98357a to prevent it from working until there is a volume limiter.
    if not override_avs:
        rmfile("/lib/firmware/intel/avs/max98357a-tplg.bin")

    if not path_exists(f"/lib/modules/{bash('uname -r')}/kernel/sound/soc/intel/avs"):
        print_error("Looks like your kernel doesn't have the avs modules. Make sure you are on at least 6.0 with avs enabled")
        exit(0)

    # Service for automatically switching between speakers and headphones
    user_input = input("Would you like to install the automatic speaker and headphone "
                       "switching service? (Y/n) ").lower()
    if user_input != "n":
        print_status("Installing auto switcher")
        bash("git clone https://github.com/WeirdTreeThing/avs-auto-switcher /tmp/avs-auto-switcher")
        cpfile("/tmp/avs-auto-switcher/avs-auto-switcher", "/usr/local/bin/avs-auto-switcher")
        bash("chmod +x /usr/local/bin/avs-auto-switcher")
        cpfile("/tmp/avs-auto-switcher/avs-auto-switcher.service",
               "/usr/lib/systemd/user/avs-auto-switcher.service")
        print_status("Installing deps")
        install_package("acpid", "acpid", "acpid", "acpid", "acpid")
        # Fedoras acpid package includes a power.sh script that breaks the power button behavior
        # The script has not been updated in 6 years either and is not included on other distros
        rmfile("/etc/acpi/actions/power.sh")
        if path_exists("/usr/bin/systemctl"):
            bash("systemctl enable acpid")
            bash(f"systemctl --machine={username}@.host --user --now enable avs-auto-switcher")
        else:
            print_warning("Warning: You are running a non-systemd distro. "
                          "You will need to manually start the acpid and avs-auto-switcher services")


def apl_audio(board, username):
    print_status("Apollolake has two audio drivers:")
    print_status("SOF: Stable but doesn't work with headphones.")
    print_status("AVS: Unstable and can cause damage to speakers but supports all audio hardware.")
    print_error("NOTE: Speakers are disabled on AVS as a safety precaution. (use --force-avs-install to override)"
                "Your speakers will still work on SOF though.")

    while True:
        user_input = input("Which driver would you like to use? [sof/avs]: ")
        if user_input.lower() == "sof":
            print_status("Using sof")
            # Remove avs modprobe config if it exists
            rmfile("/etc/modprobe.d/snd-avs.conf")
            sof_audio("apl")
            # Install apl specific modprobe config
            cpfile("conf/sof/apl-sof.conf", "/etc/modprobe.d/apl-sof.conf")
            break
        elif user_input.lower() == "avs":
            print_status("Using avs")
            # Remove sof modprobe config if it exists
            rmfile("/etc/modprobe.d/snd-sof.conf")
            rmfile("/etc/modprobe.d/apl-sof.conf")
            avs_audio(board, username)
            break
        else:
            print_error(f"Invalid option: {user_input}")
            continue


def sof_audio(platform):
    if args.debug:
        print_status(f"{args.debug} SOF debugging")
        if args.debug == "Enabling":
            cpfile("conf/sof/alsa-sof-dbg.conf", "/etc/modprobe.d/snd-sof-dbg.conf")
        else:
            rmfile("/etc/modprobe.d/snd-sof-dbg.conf")
        print_status("Done, please reboot for changes to take effect.")
        exit()

    print_status("Installing SOF")

    # Install required packages
    print_status("Installing SOF firmware")
    install_package("sof-firmware", "firmware-sof-signed", "alsa-sof-firmware", "sof-firmware", "sof-firmware")
    install_package("linux-firmware", "firmware-linux-free firmware-linux-nonfree", "linux-firmware",
                    "kernel-firmware", "linux-firmware")
    install_package("alsa-utils", "alsa-utils", "alsa-utils", "alsa-utils", "alsa-utils")

    # Force sof driver
    print_status("Installing modprobe config")
    cpfile("conf/sof/snd-sof.conf", "/etc/modprobe.d/snd-sof.conf")
    
    print_status("Installing UCM configuration")
    rmdir("/tmp/chromebook-ucm-conf")
    bash("git clone https://github.com/WeirdTreeThing/chromebook-ucm-conf /tmp/chromebook-ucm-conf")
    match platform:
        case "apl":
            cpdir("/tmp/chromebook-ucm-conf/apl/sof-bxtda7219ma", "/usr/share/alsa/ucm2/conf.d/sof-bxtda7219ma")
        case "glk":
            cpdir("/tmp/chromebook-ucm-conf/glk/sof-glkda7219ma", "/usr/share/alsa/ucm2/conf.d/sof-glkda7219ma")
            cpdir("/tmp/chromebook-ucm-conf/glk/sof-cs42l42", "/usr/share/alsa/ucm2/conf.d/sof-cs42l42")
            cpdir("/tmp/chromebook-ucm-conf/glk/sof-glkrt5682ma", "/usr/share/alsa/ucm2/conf.d/sof-glkrt5682ma")
        case "cml":
            cpdir("/tmp/chromebook-ucm-conf/cml/sof-rt5682", "/usr/share/alsa/ucm2/conf.d/sof-rt5682")
            cpdir("/tmp/chromebook-ucm-conf/cml/sof-cmlda7219ma", "/usr/share/alsa/ucm2/conf.d/sof-cmlda7219ma")
            cpdir("/tmp/chromebook-ucm-conf/cml/sof-cml_rt1011_", "/usr/share/alsa/ucm2/conf.d/sof-cml_rt1011_")
        case "tgl":
            cpdir("/tmp/chromebook-ucm-conf/tgl/sof-rt5682", "/usr/share/alsa/ucm2/conf.d/sof-rt5682")
        case "jsl":
            cpdir("/tmp/chromebook-ucm-conf/jsl/sof-rt5682", "/usr/share/alsa/ucm2/conf.d/sof-rt5682")
            cpdir("/tmp/chromebook-ucm-conf/jsl/sof-da7219max98", "/usr/share/alsa/ucm2/conf.d/sof-da7219max98")
            cpdir("/tmp/chromebook-ucm-conf/jsl/sof-cs42l42", "/usr/share/alsa/ucm2/conf.d/sof-cs42l42")
            # JSL needs tplg build from upstream which have not been shipped in distros yet
            cpdir("conf/sof/tplg", "/lib/firmware/intel/sof-tplg")
        case "adl":
            cpdir("/tmp/chromebook-ucm-conf/adl/sof-rt5682", "/usr/share/alsa/ucm2/conf.d/sof-rt5682")
            cpdir("/tmp/chromebook-ucm-conf/adl/sof-nau8825", "/usr/share/alsa/ucm2/conf.d/sof-nau8825")

    # Common dmic split ucm
    cpdir("/tmp/chromebook-ucm-conf/dmic-common", "/usr/share/alsa/ucm2/conf.d/dmic-common")

    # Common hdmi configurations
    cpdir("/tmp/chromebook-ucm-conf/hdmi-common", "/usr/share/alsa/ucm2/conf.d/hdmi-common")


def bsw_audio():
    if args.debug:
        print_status(f"{args.debug} SOF BSW debugging")
        if args.debug == "Enabling":
            cpfile(f"conf/sof/bsw-sof-dbg.conf", "/etc/modprobe.d/bsw-sof-dbg.conf")
        else:
            rmfile("/etc/modprobe.d/bsw-sof-dbg.conf")
        print_status("Done, please reboot for changes to take effect.")
        exit()

    print_status("Fixing braswell/baytrail audio")
    install_package("alsa-ucm-conf", "alsa-ucm-conf", "alsa-ucm-conf", "alsa-ucm-conf", "alsa-ucm-conf")
    install_package("sof-firmware", "firmware-sof-signed", "alsa-sof-firmware", "sof-firmware", "sof-firmware")
    cpfile("conf/sof/bsw-sof.conf", "/etc/modprobe.d/bsw-sof.conf")


def amd_audio(amd_platform):
    # amd_platform is an int that represents the generation
    # 0 = stoneyridge (grunt)
    # 1 = picasso/zen2 (zork)
    # 2 = cezanne/zen3 (guybrush)
    match amd_platform:
        case 0:
            cpdir("/tmp/chromebook-ucm-conf/stoney/acpd7219m98357", "/usr/share/alsa/ucm2/conf.d/acpd7219m98357")
        case 1:
            cpdir("/tmp/chromebook-ucm-conf/picasso/acp3xalc5682m98", "/usr/share/alsa/ucm2/conf.d/acp3xalc5682m98")
            cpdir("/tmp/chromebook-ucm-conf/picasso/acp3xalc5682101", "/usr/share/alsa/ucm2/conf.d/acp3xalc5682101")
        case 2:
            cpdir("/tmp/chromebook-ucm-conf/cezanne/sof-rt5682s-rt1", "/usr/share/alsa/ucm2/conf.d/sof-rt5682s-rt1")
    print_status("After rebooting you will need to set speakers as the output device in sound settings.")


# Rammus and Nocturne needs firmware blobs from ChromeOS
def extract_blobs(platform) -> None:
    if platform not in ["rammus", "nocturne"]:
        return
    print_question("Your device needs special firmware files for speakers to work which needs to be extracted from a "
                   "ChromeOS recovery image. The recovery image is about 2GB in size. You will need about 6GB of free"
                   " space to download and extract it.")
    user_input = input("Would you like to download and extract the firmware? [Y/n] ")
    if user_input.lower == "n":
        print_warning("Not installing firmware, speakers will not work!")
    else:
        print_status("Deleting old files")
        bash("rm -f /var/tmp/chromeos_*_recovery_stable-channel*.bin")
        rmdir("/mnt/chromeos-recovery")
        rmfile("/tmp/recovery.bin.zip")

        print_status("Installing deps")
        install_package("unzip", "unzip", "unzip", "unzip", "unzip")

        print_status("Downloading recovery image")
        if platform == "rammus":
            download_file("https://dl.google.com/dl/edgedl/chromeos/recovery/chromeos_15278.64.0_rammus_recovery_"
                          "stable-channel_mp-v2.bin.zip", "/var/tmp/recovery.bin.zip")
        else:  # nocturne
            download_file("https://dl.google.com/dl/edgedl/chromeos/recovery/chromeos_15278.64.0_nocturne_"
                          "recovery_stable-channel_mp.bin.zip", "/var/tmp/recovery.bin.zip")

        print_status("Extracting recovery image")
        bash("unzip /var/tmp/recovery.bin.zip -d /var/tmp")

        print_status("Mounting image")
        loop_dev = bash("losetup -fP --show /var/tmp/chromeos_*_recovery_*.bin")
        mkdir("/mnt/chromeos-recovery")
        bash(f"mount {loop_dev}p3 /mnt/chromeos-recovery -o ro")

        print_status("Extracting firmware")
        # extract avs firmware
        cpdir("/mnt/chromeos-recovery/lib/firmware/intel/avs", "/lib/firmware/intel/avs")

        # extract dsm config
        if platform == "rammus":
            mkdir("/usr/lib/rammus-dsm/", create_parents=True)
            cpfile("/mnt/chromeos-recovery/opt/google/dsm/shyvana/dsmparam.bin",
                   "/usr/lib/rammus-dsm/dsmparam.bin")  # Shyvana and leona have the same dsmparam.bin file
            cpdir("/mnt/chromeos-recovery/lib/firmware/intel/avs", "/lib/firmware/intel/avs")
        elif platform == "nocturne":
            mkdir("/usr/lib/nocturne-dsm/", create_parents=True)
            cpfile("/mnt/chromeos-recovery/opt/google/dsm/dsmparam.bin", "/usr/lib/nocturne-dsm/dsmparam.bin")

        print_status("Cleaning up")
        bash("umount -lf /mnt/chromeos-recovery")
        rmdir("/mnt/chromeos-recovery", keep_dir=False)
        bash(f"losetup -d {loop_dev}")
        bash("rm -f /var/tmp/chromeos_*_recovery_stable-channel*.bin")
        rmdir("/mnt/chromeos-recovery")
        rmfile("/tmp/recovery.bin.zip")


if __name__ == "__main__":
    if os.geteuid() == 0 and not path_exists("/tmp/username"):
        print_error("Please start the script as non-root/without sudo")
        exit(1)

    args = process_args()  # process args before elevating to root for better ux

    # Restart script as root
    if os.geteuid() != 0:
        # save username
        with open("/tmp/username", "w") as file:
            file.write(os.getlogin())

        # restart script as root
        # make the two people that use doas happy
        if path_exists("/usr/bin/doas"):
            doas_args = ['doas', sys.executable] + sys.argv + [os.environ]
            os.execlpe('doas', *doas_args)
        # other 99 percent of linux users
        sudo_args = ['sudo', sys.executable] + sys.argv + [os.environ]
        os.execlpe('sudo', *sudo_args)

    # read username
    with open("/tmp/username", "r") as file:
        user_id = file.read()

    # Important message
    print_warning("WARNING: this audio script is not fully functional yet!")

    if args.board_name[0] == "":
        # Get the board name from dmi
        with open("/sys/devices/virtual/dmi/id/product_name", "r") as dmi:
            device_board = dmi.read().lower().strip()
    else:  # use the board name from the args, for testing only
        device_board = str(args.board_name[0]).lower().strip()
        print_warning(f"Board name overriden to: {device_board}")

    with open("conf/board-generations.json", "r") as file:
        boards = json.load(file)

    try:
        match boards[device_board]:
            case "byt" | "bsw":
                bsw_audio()
            case "skl" | "kbl":
                avs_audio(device_board, user_id)
            case "apl":
                apl_audio(device_board, user_id)
            case "glk" | "cml" | "jsl" | "tgl" | "adl":
                sof_audio(boards[device_board])
            case "stoney":
                amd_audio(0)
            case "picasso":
                amd_audio(1)
            case "cezanne":
                amd_audio(2)
            case _:
                print_error(f"Unknown/Unsupported chromebook model: {device_board}")
                exit(1)
    except KeyError:
        print_error(f"Unknown/Unsupported chromebook model: {device_board}")
        exit(1)

    print_header("Audio installed successfully! Reboot to finish setup.")
