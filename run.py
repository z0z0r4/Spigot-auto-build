import requests
import traceback
import os
import re

PROXY = None
# PROXY = "http://127.0.0.1:7890"
TIMEOUT = 300

JavaMajorVersion = {
    61: "JAVA_HOME_17_X64",
    60: "JAVA_HOME_16_X64",
    55: "JAVA_HOME_11_X64",
    52: "JAVA_HOME_8_X64"
}

def _get(url: str, timeout : int = TIMEOUT, no_proxy: bool =False) -> requests.Response:
    if no_proxy:
        proxy = None
    else:
        proxy = PROXY
    _i = 0
    while _i < 3:
        try:
            headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.76"}
            res = requests.get(url, proxies=proxy, timeout=timeout, headers=headers)
            if res.status_code == 200:
                return res
            else:
                return res.status_code
        except Exception:
            _i += 1
            traceback.print_exc()

def get_bukit_version():
    res = _get("https://hub.spigotmc.org/versions")
    if res.status_code == 200:
        text = res.text
    else:
        return None
    version_list = re.findall('<a href="(1\..+?).json">',text)
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

# def build(version: str, java_path: str):
#     os.system()

def write_start_sh(command: str):
    with open("start.sh", "w") as f:
        f.write(f'#!/bin/bash\n{command}')

def main():
    bukkit_version = get_bukit_version()
    print(f'bukkit_version')
    get_buildtool()
    # for version in bukkit_version:
    #     version_info = _get(f"https://hub.spigotmc.org/versions/{version}.json").json()
    #     if version_info["javaVersions"] in MinecraftVersion:
    #         # build(version, os.path.join(os.getenv(choose_java_version(version_info["javaVersions"][0], version_info["javaVersions"][1])), "bin", "java"))
    version_info = _get(f"https://hub.spigotmc.org/versions/1.19.3.json").json()
    java_path = os.path.join(os.getenv(choose_java_version(version_info["javaVersions"][0], version_info["javaVersions"][1])), "bin", "java")
    write_start_sh(f'{java_path} -jar buildtools.jar --rev 1.19.3 --output-dir achieved')

if __name__ == "__main__":
    # asyncio.run(setup_java(52))
    print(os.getenv("SYSTEMDRIVE"))
    get_buildtool()
    main()
