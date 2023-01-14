import asyncio
import requests
import traceback
import os
import re

PROXY = None
# PROXY = "http://127.0.0.1:7890"
TIMEOUT = 300

JavaMajorVersion = {
    63: 19,
    62: 18,
    61: 17,
    60: 16,
    59: 15,
    58: 14,
    57: 13,
    56: 12,
    55: 11,
    54: 10,
    53: 9,
    52: 8
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

async def setup_java(version: int):
    if version in JavaMajorVersion:
        version = JavaMajorVersion[version]
        info_url = f'https://api.adoptium.net/v3/assets/latest/{version}/hotspot?os=linux&architecture=x64&image_type=jdk'
        java_info = _get(url=info_url).json()
        if len(java_info) > 0:
            java_info = java_info[0]
            java_link = java_info["binary"]["package"]["link"]
            java_tar_gz_res = _get(java_link)
            with open(java_info["binary"]["package"]["name"], "wb") as java_tar_gz:
                java_tar_gz.write(java_tar_gz_res.content)
            os.system(f'tar -zxvf {java_info["binary"]["package"]["name"]} -C java/{version}')
            os.system(f'java/{version}/bin/java -version')
    else:
        print(f"Not found {version}")
        
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
    print('::set-output name=test_report::Get BuildTools.jar')

# def build(version: str, java_path: str):
#     os.system()

def write_start_sh(command: str):
    with open("start.sh", "w") as f:
        f.write(f'#!/bin/bash\n{command}')

def main():
    bukkit_version = get_bukit_version()
    print(f'::set-output name=test_report::{bukkit_version}')
    get_buildtool()
    # for version in bukkit_version:
    #     version_info = _get(f"https://hub.spigotmc.org/versions/{version}.json").json()
    #     if version_info["javaVersions"] in MinecraftVersion:
    #         # build(version, os.path.join(os.getenv(choose_java_version(version_info["javaVersions"][0], version_info["javaVersions"][1])), "bin", "java"))
    version_info = _get(f"https://hub.spigotmc.org/versions/1.19.3.json").json()
    java_path = os.path.join(os.getenv(choose_java_version(version_info["javaVersions"][0], version_info["javaVersions"][1])), "bin", "java")
    write_start_sh(f'{os.path.join(java_path, "bin", "java")} -jar buildtools.jar --rev 1.19.3 --output-dir achieved')

if __name__ == "__main__":
    # asyncio.run(setup_java(52))
    print(os.environ)
    # get_buildtool()
#     main()
