import requests
import traceback
import os
import re
import sys

TIMEOUT = 300

JavaMajorVersion = {
    61: "JAVA_HOME_17_X64",
    60: "JAVA_HOME_16_X64",
    55: "JAVA_HOME_11_X64",
    52: "JAVA_HOME_8_X64"
}

def _get(url: str, timeout : int = TIMEOUT) -> requests.Response:
    _i = 0
    while _i < 3:
        try:
            headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.76"}
            res = requests.get(url, timeout=timeout, headers=headers)
            if res.status_code == 200:
                return res
            else:
                return res.status_code
        except Exception:
            _i += 1
            traceback.print_exc()

def get_bukit_version():
    res = _get("https://hub.spigotmc.org/versions")
    text = res.text
    version_list = re.findall('<a href="(1\..+?).json">', text)
    return version_list

def choose_java_version(oldversion: int, newversion: int) -> int:
    for JavaVersion in JavaMajorVersion:
        if JavaVersion <= newversion and JavaVersion >= oldversion:
            return JavaMajorVersion[JavaVersion]
    else:
        return None

def get_buildtool():
    with open("buildtools.jar", "wb") as f:
        f.write(_get("https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar").content)
    print('Get BuildTools.jar')

def write_command_start_sh(command: str):
    with open("start.sh", "a") as f:
        f.write(f'{command}\n')
        f.write(f"echo '{command} Completed'\n")

def init_version(version: str):
    version_info = _get(f"https://hub.spigotmc.org/versions/{version}.json").json()
    if "javaVersions" in version_info:
        java_path = os.path.join(os.getenv(choose_java_version(version_info["javaVersions"][0], version_info["javaVersions"][1])), "bin", "java")
    else:
        java_path = os.path.join(os.getenv("JAVA_HOME"), "bin", "java")
    write_command_start_sh(f'{java_path} -jar buildtools.jar --rev {version} --output-dir achieved')
#     write_command_start_sh(f'{java_path} -jar buildtools.jar --rev {version} --compile craftbukkit --output-dir achieved') # build for craftbukkit

        
def main():
    get_buildtool()
    if len(sys.argv) >= 2:
        print(f'找到 {sys.argv[1:]}')
        for version in sys.argv[1:]:
            init_version(version)
    else:
        bukkit_version = get_bukit_version()
        print(f'找到 {bukkit_version}')
        for version in bukkit_version:
            init_version(version)
            
if __name__ == "__main__":
    main()
