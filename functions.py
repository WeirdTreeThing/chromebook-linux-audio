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
    def copy_files(src: Path, dst: Path) -> None:
        # create dst dir if it doesn't exist
        mkdir(dst.absolute().as_posix(), create_parents=True)
        for src_file in src.iterdir():
            if src_file.is_file():
                dst_file = dst.joinpath(src_file.stem + src_file.suffix)
                dst_file.write_bytes(src_file.read_bytes())
            elif src_file.is_dir():
                if src_file.exists():
                    new_dst = dst.joinpath(src_file.stem + src_file.suffix)
                    copy_files(src_file, new_dst)
                else:
                    raise FileNotFoundError(f"No such file or directory: {src_file.absolute().as_posix()}")

    src_as_path = Path(src_as_str)
    dst_as_path = Path(dst_as_string)
    if src_as_path.exists():
        if not dst_as_path.exists():
            mkdir(dst_as_string)
        '''
        try:
            copy_files(src_as_path, dst_as_path)
        except RecursionError:
            print("\033[93m" + f"Failed to copy {root_src} to {root_dst}, using bash" + "\033[0m")
            bash(f"cp -rp {src_as_path.absolute().as_posix()} {dst_as_path.absolute().as_posix()}")
        '''
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
                    void_package: str = ""):
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
        # Immutable variants of Fedora such as Fedora Silverblue use `rpm-ostree` instead of `dnf`
        if (is_fedora_immutable()):
            bash(f"rpm-ostree install -y {rpm_package}")
        else:
            bash(f"dnf install -y {rpm_package}")
    else:
        print_error(f"Unknown package manager! Please install {deb_package} using your package manager.")

def is_fedora_immutable():
    return Path('/usr/bin/rpm-ostree').exists()
