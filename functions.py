import contextlib
import subprocess
import sys
from pathlib import Path
from threading import Thread
from time import sleep


#######################################################################################
#                               PATHLIB FUNCTIONS                                     #
#######################################################################################
# unlink all files in a directory and remove the directory
def rmdir(rm_dir: str, keep_dir: bool = True) -> None:
    def unlink_files(path_to_rm: Path) -> None:
        try:
            for file in path_to_rm.iterdir():
                if file.is_file():
                    file.unlink()
                else:
                    unlink_files(path_to_rm)
        except FileNotFoundError:
            print(f"Couldn't remove non existent directory: {path_to_rm}, ignoring")

    # convert string to Path object
    rm_dir_as_path = Path(rm_dir)
    try:
        unlink_files(rm_dir_as_path)
    except RecursionError:  # python doesn't work for folders with a lot of subfolders
        print(f"Failed to remove {rm_dir} with python, using bash")
        bash(f"rm -rf {rm_dir_as_path.absolute().as_posix()}/*")
    # Remove emtpy directory
    if not keep_dir:
        try:
            rm_dir_as_path.rmdir()
        except FileNotFoundError:  # Directory doesn't exist, because bash was used
            return


# remove a single file
def rmfile(file: str, force: bool = False) -> None:
    if force:  # for symbolic links
        Path(file).unlink(missing_ok=True)
    file_as_path = Path(file)
    with contextlib.suppress(FileNotFoundError):
        file_as_path.unlink()


# make directory
def mkdir(mk_dir: str, create_parents: bool = False) -> None:
    mk_dir_as_path = Path(mk_dir)
    if not mk_dir_as_path.exists():
        mk_dir_as_path.mkdir(parents=create_parents)


def path_exists(path_str: str) -> bool:
    return Path(path_str).exists()


# recursively copy files from a dir into another dir
def cpdir(src_as_str: str, dst_as_string: str) -> None:  # dst_dir must be a full path, including the new dir name
    src_as_path = Path(src_as_str)
    dst_as_path = Path(dst_as_string)
    if src_as_path.exists():
        if not dst_as_path.exists():
            mkdir(dst_as_string)
        bash(f"cp -rp {src_as_path.absolute().as_posix()}/* {dst_as_path.absolute().as_posix()}")
    else:
        raise FileNotFoundError(f"No such directory: {src_as_path.absolute().as_posix()}")


def cpfile(src_as_str: str, dst_as_str: str) -> None:  # "/etc/resolv.conf", "/var/some_config/resolv.conf"
    src_as_path = Path(src_as_str)
    dst_as_path = Path(dst_as_str)
    if src_as_path.exists():
        dst_as_path.write_bytes(src_as_path.read_bytes())
    else:
        raise FileNotFoundError(f"No such file: {src_as_path.absolute().as_posix()}")


#######################################################################################
#                               BASH FUNCTIONS                                        #
#######################################################################################

# return the output of a command
def bash(command: str) -> str:
    try:
        output = subprocess.check_output(command, shell=True, text=True).strip()
        return output
    except:
        print(f"failed to run command: {command}")


#######################################################################################
#                                    PRINT FUNCTIONS                                  #
#######################################################################################


def print_warning(message: str) -> None:
    print("\033[93m" + message + "\033[0m", flush=True)


def print_error(message: str) -> None:
    print("\033[91m" + message + "\033[0m", flush=True)


def print_status(message: str) -> None:
    print("\033[94m" + message + "\033[0m", flush=True)


def print_question(message: str) -> None:
    print("\033[92m" + message + "\033[0m", flush=True)


def print_header(message: str) -> None:
    print("\033[95m" + message + "\033[0m", flush=True)

#######################################################################################
#                             PACKAGE MANAGER FUNCTIONS                               #
#######################################################################################
def install_package(arch_package: str = "", deb_package: str = "", rpm_package: str = "", suse_package: str = "",
                    void_package: str = "", alpine_package: str = ""):
    with open("/etc/os-release", "r") as file:
        distro = file.read()
    if distro.lower().__contains__("arch"):
        bash(f"pacman -S --noconfirm --needed {arch_package}")
    elif distro.lower().__contains__("void"):
        bash(f"xbps-install -y {void_package}")
    elif distro.lower().__contains__("ubuntu") or distro.lower().__contains__("debian"):
        bash(f"apt-get install -y {deb_package}")
    elif distro.lower().__contains__("suse"):
        bash(f"zypper --non-interactive install {suse_package}")
    elif distro.lower().__contains__("fedora"):
        bash(f"dnf install -y {rpm_package}")
    elif distro.lower().__contains__("alpine"):
        bash(f"apk add --no-interactive {alpine_package}")
    else:
        print_error(f"Unknown package manager! Please install {arch_package} using your package manager.")

#######################################################################################
#                          PLATFORM-SPECIFIC CONFIG FUNCTIONS                         #
#######################################################################################
def platform_config(platform, args):
    match platform:
        case "bdw" | "byt" | "bsw":
            hifi2_sof_config()
            check_sof_fw()
        case "skl" | "kbl" | "apl":
            avs_config(args)
        case "glk" | "cml" | "tgl" | "jsl":
            check_sof_fw()
        case "adl":
            adl_sof_config()
            check_sof_fw()
        case "mtl":
            mtl_sof_config()
            check_sof_fw()
        case "st":
            st_warning()
        case "mdn":
            mdn_config()

def get_platform():
    # first check if we are on a chromeb{ook,ox,ase,let} (either sys_vendor or product_family includes "google" (case-insensitive for old devices where it was GOOGLE))
    # product_family *usually* will tell us the platform
    # some platforms (jsl, byt) dont have a product_family so instead check the id of pci device 00:00.0 (chipset/pch)
    # for some reason, cyan also doesnt have this set even though every other bsw board does
    # samus and buddy are BDW but use intel SST
    print_header("Detecting platform")
    platform = ""
    sv = ""
    pf = ""
    pn = ""

    with open("/sys/class/dmi/id/sys_vendor") as sys_vendor:
        sv = sys_vendor.read().strip().lower()
    with open("/sys/class/dmi/id/product_family") as product_family:
        pf = product_family.read().strip().lower()
    with open("/sys/class/dmi/id/product_name") as product_name:
        pn = product_name.read().strip().lower()

    # some people are morons
    if pn == "crosvm":
        print_error("This script can not and will not do anything in the crostini vm!")
        exit(1)

    if not "google" in sv and not "google" in pf and not Path("/dev/cros_ec").exists():
        print_error("This script is not supported on non-Chrome devices!")
        exit(1)

    if not len(pf) == 0:
        match pf:
            case "intel_strago":
                print_status("Detected Intel Braswell")
                platform = "bsw"
            case "google_glados":
                print_status("Detected Intel Skylake")
                platform = "skl"
            case "google_coral" | "google_reef":
                print_status("Detected Intel Apollolake")
                platform = "apl"
            case "google_atlas" | "google_poppy" | "google_nami" | "google_nautilus" | "google_nocturne" | "google_rammus" | "google_soraka" | "google_eve" | "google_fizz" | "google_kalista" | "google_endeavour":
                print_status("Detected Intel Kabylake")
                platform = "kbl"
            case "google_octopus":
                print_status("Detected Intel Geminilake")
                platform = "glk"
            case "google_hatch" | "google_puff":
                print_status("Detected Intel Cometlake")
                platform = "cml"
            case "google_dedede":
                print_status("Detected Intel Jasperlake")
                platform = "jsl"
            case "google_volteer":
                print_status("Detected Intel Tigerlake")
                platform = "tgl"
            case "google_brya" | "google_brask":
                print_status("Detected Intel Alderlake")
                platform = "adl"
            case "google_nissa":
                print_status("Detected Intel Alderlake-N")
                platform = "adl"
            case "google_rex":
                print_status("Detected Intel Meteorlake")
                platform = "mtl"
            case "google_kahlee":
                print_status("Detected AMD StoneyRidge")
                platform = "st"
            case "google_zork":
                print_status("Detected AMD Picasso/Dali")
                platform = "pco"
            case "google_guybrush":
                print_status("Detected AMD Cezanne")
                platform = "czn"
            case "google_skyrim":
                print_status("Detected AMD Mendocino")
                platform = "mdn"
            case _:
                print_error(f"Unknown platform/baseboard: {pf}")
                exit(1)
        return platform
    else:
        # Cyan special case
        if pn == "cyan":
            print_status("Detected Intel Braswell")
            return "bsw"
        # BDW special cases (every other BDW uses HDA audio)
        if pn == "samus" or pn == "buddy":
            print_status("Detected Intel Broadwell")
            return "bdw"
        id = ""
        with open("/sys/bus/pci/devices/0000:00:00.0/device") as devid:
            id = devid.read().strip()
        # BYT special case - check if pci dev id is 0x0f00
        if id == "0x0f00":
            print_status("Detected Intel Baytrail")
            return "byt"
        # JSL special case - check if pci dev id is 0x4e22 or 0x4e12 or 0x4e26
        if id == "0x4e22" or id == "0x4e12" or id == "0x4e26":
            print_status("Detected Intel Jasperlake")
            return "jsl"

def mdn_config():
    print_header("Installing MDN SOF firmware")
    mkdir("/lib/firmware/amd/sof/community", create_parents=True)
    mkdir("/lib/firmware/amd/sof-tplg", create_parents=True)
    cpdir("blobs/mdn/fw", "/lib/firmware/amd/sof/community")
    cpdir("blobs/mdn/tplg", "/lib/firmware/amd/sof-tplg")

def st_warning():
    print_warning("WARNING: Audio on AMD StoneyRidge Chromebooks requires a patched kernel.")
    print_warning("You can get a prebuilt kernel for Debian/Ubuntu/Fedora from https://chrultrabook.sakamoto.pl/stoneyridge-kernel/")
    print_warning("For other distros, a patch file is included in that same link, under the patches directory.")


def avs_config(args):
    # Only show the warning to devices with max98357a
    override_avs = False
    if path_exists("/sys/bus/acpi/devices/MX98357A:00"):
        if args.force_avs_install:
            print_error(
                "WARNING: Your device has max98357a and can cause permanent damage to your speakers if you set the volume too loud!")
            while input('Type "I understand the risk of permanently damaging my speakers" in all caps to continue: ')\
                != "I UNDERSTAND THE RISK OF PERMANENTLY DAMAGING MY SPEAKERS":
                print_error("Try again")
            override_avs = True
        else:
            print_error(
                "WARNING: Your device has max98357a and can cause permanent damage to your speakers if you "
                    "set the volume too loud! As a safety precaution devices with max98357a have speakers "
                    "disabled until a fix is in place. Headphones and HDMI audio are safe from this.")
            print_question("If you want to disable this check, restart the script with --force-avs-install")

            while input('Type "I Understand my speakers will not work since my device has max98357a!" in all caps to continue: ')\
                != "I UNDERSTAND MY SPEAKERS WILL NOT WORK SINCE MY DEVICE HAS MAX98357A!":
                print_error("Try again")
            override_avs = False

    print_header("Enabling AVS driver")
    cpfile("conf/avs/snd-avs.conf", "/etc/modprobe.d/snd-avs.conf")

    # Delete topology for max98357a to prevent it from working until there is a volume limiter.
    if not override_avs:
        rmfile("/lib/firmware/intel/avs/max98357a-tplg.bin")

def check_sof_fw():
    if not path_exists("/lib/firmware/intel/sof"):
        print_error("SOF firmware is missing, audio will not work!")
        print_error("Please install the SOF firmware package (usually sof-firmware) with your package manager")

def symlink_tplg(path, tplg1, tplg2):
    if path_exists(f"{path}/{tplg1}.tplg"):
        bash(f"ln -sf {path}/{tplg1}.tplg {path}/{tplg2}.tplg")
    if path_exists(f"{path}/{tplg1}.tplg.xz"):
        bash(f"ln -sf {path}/{tplg1}.tplg.xz {path}/{tplg2}.tplg.xz")
    if path_exists(f"{path}/{tplg1}.tplg.zst"):
        bash(f"ln -sf {path}/{tplg1}.tplg.zst {path}/{tplg2}.tplg.zst")

def install_downstream_tplg(tplg, dest):
    if path_exists(f"{dest}"):
        cpfile(f"{tplg}", f"{dest}")
    if path_exists(f"{dest}.xz"):
        bash(f"xz -c {tplg} > {dest}.xz")
    if path_exists(f"{dest}.zst"):
        bash(f"zst {tplg} -o {dest}.zst")

def adl_sof_config():
    # Special tplg cases
    # RPL devices load tplg with a different file name than ADL, despite being the exact same file as their ADL counterparts
    # sof-bin currently doesn't include these symlinks, so we create them ourselves
    tplgs = ["cs35l41", "max98357a-rt5682-4ch", "max98357a-rt5682", "max98360a-cs42l42", "max98360a-da7219", "max98360a-nau8825", "max98360a-rt5682-2way", "max98360a-rt5682-4ch", "max98360a-rt5682", "max98373-nau8825", "max98390-rt5682", "max98390-ssp2-rt5682-ssp0", "nau8825", "rt1019-nau8825", "rt1019-rt5682", "rt5682", "rt711", "sdw-max98373-rt5682"]
    for tplg in tplgs:
        symlink_tplg("/lib/firmware/intel/sof-tplg", f"sof-adl-{tplg}", f"sof-rpl-{tplg}")
    # sof-adl-max98360a-cs42l42.tplg is symlinked to sof-adl-max98360a-rt5682.tplg in ChromeOS
    symlink_tplg("/lib/firmware/intel/sof-tplg", "sof-adl-max98360a-rt5682", "sof-adl-max98360a-cs42l42")
    # upstream sof-adl-rt1019-rt5682 is broken currently
    install_downstream_tplg("blobs/adl/sof-adl-rt1019-rt5682.tplg", "/lib/firmware/intel/sof-tplg/sof-adl-rt1019-rt5682.tplg")

def mtl_sof_config():
    print_header("Enabling SOF driver")
    cpfile("conf/sof/mtl-sof.conf", "/etc/modprobe.d/mtl-sof.conf")

def hifi2_sof_config():
    print_header("Forcing SOF driver in debug mode")
    cpfile("conf/sof/hifi2-sof.conf", "/etc/modprobe.d/hifi2-sof.conf")

#######################################################################################
#                                   GENERAL FUNCTIONS                                 #
#######################################################################################
def check_nix():
    with open("/etc/os-release") as os:
        if "ID=nixos" in os.read():
            print_error("NixOS is not supported")
            exit(1)

def check_arch():
    # dmi doesnt exist on arm chromebooks
    if not path_exists("/sys/devices/virtual/dmi/id/"):
        print_error("ARM Chromebooks are not supported by this script. See your distro's documentation for audio support status.")
        exit(1)

def check_kernel_config(platform):
    active_kernel = bash("uname -r")
    print_header(f"Checking kernel config for {active_kernel}")

    config = ""
    if path_exists(f"/boot/config-{active_kernel}"):
        with open(f"/boot/config-{active_kernel}") as file:
            config = file.read()
    elif path_exists("/proc/config.gz"):
        bash(f"zcat /proc/config.gz > /tmp/config-{active_kernel}")
        with open(f"/tmp/config-{active_kernel}") as file:
            config = file.read()
    elif path_exists("/boot/config"):
        with open("/boot/config") as file:
            config = file.read()
    else:
        # throw hands up in the air crying
        print_error("Unable to read kernel config!")
        return

    # List of kernel config strings for audio hardware
    module_configs = []

    match platform: # may not want to check for machine drivers here but whatever it works good enough for now
        case "bdw": # Maybe I should use catpt for bdw instead of sof
            module_configs += ["SND_SOC_INTEL_BDW_RT5650_MACH", "SND_SOC_INTEL_BDW_RT5677_MACH", "SND_SOC_SOF_BROADWELL"]
        case "byt":
            module_configs += ["SND_SOC_INTEL_BYTCR_RT5640_MACH", "SND_SOC_SOF_BAYTRAIL"]
        case "bsw":
            module_configs += ["SND_SOC_INTEL_CHT_BSW_RT5645_MACH", "SND_SOC_INTEL_CHT_BSW_MAX98090_TI_MACH", "SND_SOC_SOF_BAYTRAIL"]
        case "skl" | "kbl" | "apl":
            module_configs += ["SND_SOC_INTEL_AVS", "SND_SOC_INTEL_AVS_MACH_DA7219", "SND_SOC_INTEL_AVS_MACH_DMIC", "SND_SOC_INTEL_AVS_MACH_HDAUDIO", "SND_SOC_INTEL_AVS_MACH_MAX98927", "SND_SOC_INTEL_AVS_MACH_MAX98357A", "SND_SOC_INTEL_AVS_MACH_MAX98373", "SND_SOC_INTEL_AVS_MACH_NAU8825", "SND_SOC_INTEL_AVS_MACH_RT5514", "SND_SOC_INTEL_AVS_MACH_RT5663", "SND_SOC_INTEL_AVS_MACH_SSM4567"]
        case "glk":
            module_configs += ["SND_SOC_SOF_GEMINILAKE", "SND_SOC_INTEL_SOF_CS42L42_MACH", "SND_SOC_INTEL_SOF_RT5682_MACH", "SND_SOC_INTEL_SOF_DA7219_MACH"]
        case "cml":
            module_configs += ["SND_SOC_SOF_COMETLAKE", "SND_SOC_INTEL_SOF_RT5682_MACH", "SND_SOC_INTEL_SOF_DA7219_MACH"]
        case "tgl":
            module_configs += ["SND_SOC_SOF_TIGERLAKE", "SND_SOC_INTEL_SOF_RT5682_MACH"]
        case "jsl":
            module_configs += ["SND_SOC_SOF_ICELAKE", "SND_SOC_INTEL_SOF_RT5682_MACH", "SND_SOC_INTEL_SOF_DA7219_MACH", "SND_SOC_INTEL_SOF_CS42L42_MACH"]
        case "adl":
            module_configs += ["SND_SOC_SOF_ALDERLAKE", "SND_SOC_INTEL_SOF_CS42L42_MACH", "SND_SOC_INTEL_SOF_DA7219_MACH", "SND_SOC_INTEL_SOF_RT5682_MACH", "SND_SOC_INTEL_SOF_NAU8825_MACH", "SND_SOC_INTEL_SOF_SSP_AMP_MACH"]
        case "mtl":
            module_configs += [""] # TODO: fill this out
        case "st":
            module_configs += ["SND_SOC_AMD_ACP", "SND_SOC_AMD_CZ_DA7219MX98357_MACH"]
        case "pco":
            module_configs += ["SND_SOC_AMD_ACP3x", "SND_SOC_AMD_RV_RT5682_MACH"]
        case "czn":
            module_configs += [""] # TODO: fill this out
        case "mdn":
            module_configs += ["SND_SOC_SOF_AMD_REMBRANDT", "SND_AMD_ASOC_REMBRANDT"]

    for codec in get_codecs():
        match codec:
            case "max98357a" | "max98360a":
                module_configs.append("SND_SOC_MAX98357A")
            case "max98373":
                module_configs.append("SND_SOC_MAX98373")
            case "max98927":
                module_configs.append("SND_SOC_MAX98927")
            case "max98390":
                module_configs.append("SND_SOC_MAX98390")
            case "rt1011":
                module_configs.append("SND_SOC_RT1011")
            case "rt1015":
                module_configs.append("SND_SOC_RT1015")
            case "rt1015p" | "rt1019p":
                module_configs.append("SND_SOC_RT1015P")
            case "rt1019":
                module_configs.append("SND_SOC_RT1019")
            case "rt5682":
                module_configs.append("SND_SOC_RT5682")
            case "rt5682s":
                module_configs.append("SND_SOC_RT5682S")
            case "rt5663":
                module_configs.append("SND_SOC_RT5663")
            case "cs42l42":
                module_configs.append("SND_SOC_CS42L42")
            case "da7219":
                module_configs.append("SND_SOC_DA7219")
            case "nau8825":
                module_configs.append("SND_SOC_NAU8825")
            case "max98090":
                module_configs.append("SND_SOC_MAX98090")
            case "rt5650":
                module_configs.append("SND_SOC_RT5645")
            case "rt5677":
                module_configs.append("SND_SOC_RT5677")
            case "rt5514":
                module_configs.append("SND_SOC_RT5514")
            case "CrosEC audio codec":
                module_configs.append("SND_SOC_CROS_EC_CODEC")
    failed = 0
    for module in module_configs:
        if not f"{module}=" in config:
            failed = 1
            print_error(f"Warning: Kernel is missing module '{module}', audio may not work.")
    if not failed:
        print_status("Kernel config check passed")

def get_codecs():
    # Get a list of codecs/amps via sysfs
    print_header("Detecting codecs")
    codec_table = {
        # Speaker amps
        "MX98357A": "max98357a",
        "MX98360A": "max98360a",
        "MX98373": "max98373",
        "MX98927": "max98927",
        "MX98390": "max98390",
        "10EC1011": "rt1011",
        "10EC1015": "rt1015",
        "RTL1015": "rt1015p",
        "10EC1019": "rt1019",
        "RTL1019": "rt1019p",
        "103C8C08": "cs35l53",
        # Headphone codecs
        "10EC5682": "rt5682",
        "RTL5682": "rt5682s",
        "10EC5663": "rt5663",
        "10134242": "cs42l42",
        "DLGS7219": "da7219",
        "10158825": "nau8825",
        # Speaker/Headphone combo codecs
        "193C9890": "max98090",
        "10EC5650": "rt5650",
        "RT5677CE": "rt5677",
        # Mic codecs
        "10EC5514": "rt5514",
        "GOOG0013": "CrosEC audio codec"
    }

    codecs = []

    for codec in codec_table:
        if path_exists(f"/sys/bus/acpi/devices/{codec}:00"):
            print_status(f"Found {codec_table[codec]}")
            codecs.append(codec_table[codec])

    return codecs

def install_ucm(branch):
    print_header("Installing UCM configuration")
    try:
        bash("rm -rf /tmp/alsa-ucm-conf-cros")
        bash(f"git clone --depth 1 https://github.com/WeirdTreeThing/alsa-ucm-conf-cros -b {branch} /tmp/alsa-ucm-conf-cros")
    except:
        print_error("Error: Failed to clone UCM repo")
        exit(1)

    cpdir("/tmp/alsa-ucm-conf-cros/ucm2", "/usr/share/alsa/ucm2/")
    cpdir("/tmp/alsa-ucm-conf-cros/overrides", "/usr/share/alsa/ucm2/conf.d")

def check_os_release():
    release = ""
    with open("/etc/os-release", "r") as rel:
        release = rel.read()
    if "noble" in release or "jammy" in release or "plucky" in release:
        print_error("Warning: Your distro is not officially supported. Expect Issues.")
        print_error("Please try a supported distro first before opening an issue. See the README for a list of supported distros.")
        return False
    return True
