# for parse
import traceback
import asyncio
import aiohttp
import os


PROXY = None
# PROXY = "http://127.0.0.1:7890"
TIMEOUT = 10

# latest 则保存到 /${project}/${version}/ 下，否则直接保存到 /${project}/ 下

async def extend_tasks(tasks: list, results: list = []):
    await asyncio.gather(*tasks)
    for task in tasks:
        results.extend(task.result())
    return results

async def _get(url: str, timeout : int = TIMEOUT, no_proxy: bool =False):
    if no_proxy:
        proxy = None
    else:
        proxy = PROXY
    _i = 0 # retry times
    while _i < 3:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(timeout)) as sess:
                async with sess.get(url=url, proxy=proxy) as resp:
                    if resp.status == 200:
                        return resp
        except Exception:
            _i += 1
            traceback.print_exc()

async def _get_json(url: str, timeout : int = TIMEOUT, no_proxy: bool =False):
    _i = 0 # retry times
    if no_proxy:
        proxy = None
    else:
        proxy = PROXY
    while _i < 3:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(timeout)) as sess:
                async with sess.get(url=url, proxy=proxy) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 404:
                        return resp.status
        except Exception:
            _i += 1
            traceback.print_exc()
            
async def get_github_release(owner: str, repo: str, latest: bool = False, return_raw: bool = False):
    def parse_release(release_info: dict):
        results = []
        for asset in release_info["assets"]:
            if return_raw:
                results.append(asset)
            else:
                results.append({"name": os.path.join(repo, release_info["tag_name"], asset["name"]), "url": asset["browser_download_url"], "size": asset["size"]}) # why fucking github api not return hash
        return results

    results = []
    if latest:
        latest_release_info = await _get_json(f'https://api.github.com/repos/{owner}/{repo}/releases/latest')
        return parse_release(latest_release_info)
    else:
        release_info = await _get_json(f'https://api.github.com/repos/{owner}/{repo}/releases')
        for release in release_info:
            results.extend(parse_release(release))
    return results

async def get_jenkins_artifact(project_name: str, url: str, latest : bool = False, mkdir_for_build : bool = True):
    async def _get_build_info(url: str, mkdir_for_build : bool = False):
        results = []
        build_info = await _get_json(url)
        for artifact in build_info["artifacts"]:
            if mkdir_for_build:
                name = os.path.join(project_name, str(build_info["number"]), artifact["fileName"])
            else:
                name = os.path.join(project_name, artifact["fileName"])
            results.append({"name": name, "url": f'{build_info["url"]}artifact/{artifact["relativePath"]}'})
        return results

    results = []
    get_builds_info = await _get_json(f'{url}/api/json')
    if latest:
        latest_successful_build_url = f'{get_builds_info["lastSuccessfulBuild"]["url"]}/api/json'
        return await _get_build_info(latest_successful_build_url, mkdir_for_build=False)
    else: # all builds
        tasks = []
        for build in get_builds_info["builds"]:
            tasks.append(asyncio.create_task(_get_build_info(f'{build["url"]}api/json', mkdir_for_build=mkdir_for_build)))
        return await extend_tasks(tasks=tasks, results=results)

async def vanilla(source: str = "mojang", allow_type: list[str] = ["release"]):
    '''
    获取所有版本的信息

    :param source: 版本信息源
    :param type: 版本类型 release、snapshot

    '''
    
    async def _get_version_jar(url: str):
        version_info = await _get_json(url)
        if "server" in version_info["downloads"]:
            if source == "mcbbs" or source == "bmclapi":
                jar_url = version_info["downloads"]["server"]["url"].replace("https://piston-data.mojang.com", f"https://{version_manifest_domain}").replace("https://launcher.mojang.com", f"https://{version_manifest_domain}")
            else:
                jar_url = version_info["downloads"]["server"]["url"]
            return {"url": jar_url, "name": os.path.join("vanilla", f'{version_info["id"]}.jar'), "sha1": version_info["downloads"]["server"]["sha1"], "size": version_info["downloads"]["server"]["size"]}
        else:
            return {}

    if source == "mojang":
        version_manifest_domain = "launchermeta.mojang.com"
    elif source == "bmclapi":
        version_manifest_domain = "bmclapi2.bangbang93.com"
    elif source == "mcbbs":
        version_manifest_domain = "download.mcbbs.net"
    
    version_manifest = await _get_json(f"https://{version_manifest_domain}/mc/game/version_manifest_v2.json")
    
    # 获取全部版本 URL 列表
    version_info_urls = []
    for version in version_manifest["versions"]:
        if version["type"] in allow_type:
            version_info_urls.append(version["url"])
    
    tasks = []
    results = []
    # 异步遍历版本 URL 列表
    for version_url in version_info_urls:
        if source == "bmclapi" or source == "mcbbs":
            version_url = version_url.replace("piston-meta.mojang.com", version_manifest_domain)
        tasks.append(asyncio.create_task(_get_version_jar(version_url)))
    await asyncio.gather(*tasks)
    for task in tasks:
        results.append(task.result())
    return results

async def papermc(latest: bool = True): # https://docs.papermc.io/misc/downloads-api
    '''
    获取最新的构建版本
    project 有
    "paper",
    "travertine",
    "waterfall",
    "velocity"
    '''

    async def get_papermc_version(project: str, version: str):
        results = []
        version_info = await _get_json(f"https://papermc.io/api/v2/projects/{project}/versions/{version}/builds")
        if latest:
            build_info = version_info["builds"][-1]
            return [{"name": os.path.join(project, build_info["downloads"]["application"]["name"]), "url": f'https://api.papermc.io/v2/projects/{project}/versions/{version}/builds/{build_info["build"]}/downloads/{build_info["downloads"]["application"]["name"]}', "sha256": build_info["downloads"]["application"]["sha256"]}]
        else:
            for build_info in version_info["builds"]:
                results.append({"name": os.path.join(project, version, build_info["downloads"]["application"]["name"]), "url": f'https://api.papermc.io/v2/projects/{project}/versions/{version}/builds/{build_info["build"]}/downloads/{build_info["downloads"]["application"]["name"]}', "sha256": build_info["downloads"]["application"]["sha256"]})
            return results

    projects = (await _get_json("https://papermc.io/api/v2/projects"))["projects"]
    tasks = []
    for project in projects:
        project_info = await _get_json(f"https://papermc.io/api/v2/projects/{project}")
        for version in project_info["versions"]:
            tasks.append(asyncio.create_task(get_papermc_version(project, version)))
    return await extend_tasks(tasks=tasks)

async def mohist(latest: bool = False): # https://mohistmc.com/api
    results = []
    for version in ["1.7.10", "1.12.2", "1.16.5", "1.19.3"]: # 手动更新吧...
        if latest:
            latest_build_info = await _get_json(f"https://mohistmc.com/api/{version}/latest") # 获取最新构建信息
            results.append({"url": latest_build_info["url"], "sha1": latest_build_info["fullsha"], "name": os.path.join("mohist", latest_build_info["name"])}) # 量少，懒得异步了
        else:
            build_info = await _get_json(f"https://mohistmc.com/api/{version}")
            for build in build_info:
                results.append({"url": build["url"], "sha1": build["fullsha"], "name": os.path.join("mohist", version, build["name"])})
    return results

async def nukkitx(latest: bool = False): # https://ci.opencollab.dev/job/NukkitX/
    return await get_jenkins_artifact("nukkitx", "https://ci.opencollab.dev/job/NukkitX/job/Nukkit/job/master", latest=latest)

async def bungeecord(latest: bool = False):
    return await get_jenkins_artifact("bungeecord", "https://ci.md-5.net/job/BungeeCord", latest=latest)

async def geyser(latest: bool = False):
    return await get_jenkins_artifact("geyser", "https://ci.opencollab.dev/job/GeyserMC/job/Geyser/job/master", latest=latest)

async def floodgate(latest: bool = False):
    return await get_jenkins_artifact("floodgate", "https://ci.opencollab.dev/job/GeyserMC/job/Floodgate/job/master", latest=latest)

async def purpur(latest: bool = False):
    purpur_api = "api.purpurmc.org"
    async def _get_purpur_build(version: str, build: int):
        version_info = await _get_json(f'https://{purpur_api}/v2/purpur/{version}/{build}')
        if version_info["result"] == "SUCCESS":
            return {"url": f'https://{purpur_api}/v2/purpur/{version}/{build}/download', "md5": version_info["md5"], "name": os.path.join("purpur", version, f'purpur-{version_info["version"]}-{version_info["build"]}.jar')}

    async def _get_purpur_latest_build(version: str):
        if latest:
            return await _get_purpur_build(version, "latest")
        else:
            while True:
                version_info = await _get_json(f'https://{purpur_api}/v2/purpur/{version}/{version_info["build"]-1}') # 防止 Failed build
                if version_info["result"] == "SUCCESS":
                    return {"url": f'https://{purpur_api}/v2/purpur/{version}/{version_info["build"]-1}/download', "md5": version_info["md5"], "name": f'purpur-{version_info["version"]}-{version_info["build"]}.jar'}

    project_info = await _get_json(f'https://{purpur_api}/v2/purpur')
    results, tasks = [], []
    for version in project_info["versions"]:
        tasks.append(asyncio.create_task(_get_purpur_latest_build(version)))
    await asyncio.gather(*tasks)
    for task in tasks:
        results.append(task.result())
    return results

async def sponge(latest: bool = False):
    async def _get_sponge_build(type: str, build_id: str):
        results = []
        version_info = await _get_json(f'https://dl-api-new.spongepowered.org/api/v2/groups/org.spongepowered/artifacts/{type}/versions/{build_id}')
        for asset in version_info["assets"]:
            # if asset["extension"] == "jar": # only jar (?)
            results.append({"url": asset["downloadUrl"], "sha1": asset["sha1"], "md5": asset["md5"], "name": os.path.join(type, version, asset["downloadUrl"].split("/")[-1])})
        return results

    async def _get_sponge_version(type: str, version: str):
        if latest:
            version_info = await _get_json(f'https://dl-api-new.spongepowered.org/api/v2/groups/org.spongepowered/artifacts/{type}/versions?recommended=true&tags=minecraft:{version}&limit=1')
            if version_info == 404:
                version_info = await _get_json(f'https://dl-api-new.spongepowered.org/api/v2/groups/org.spongepowered/artifacts/{type}/versions?tags=minecraft:{version}&limit=1') # No recommended version
        else:
            version_info = await _get_json(f'https://dl-api-new.spongepowered.org/api/v2/groups/org.spongepowered/artifacts/{type}/versions?tags=minecraft:{version}')
        tasks = []
        for build_id in version_info["artifacts"]:
            tasks.append(asyncio.create_task(_get_sponge_build(type, build_id)))
        return await extend_tasks(tasks=tasks)

    types = ["spongevanilla", "spongeforge"]

    tasks = []
    for type in types:
        vanilla_versions_info = await _get_json(f'https://dl-api-new.spongepowered.org/api/v2/groups/org.spongepowered/artifacts/{type}')
        for version in vanilla_versions_info["tags"]["minecraft"]:
            tasks.append(asyncio.create_task(_get_sponge_version(type, version)))
    return await extend_tasks(tasks=tasks)

async def pufferfish(latest: bool = False):
    tasks = []
    tasks.append(asyncio.create_task(get_jenkins_artifact("pufferfish", "https://ci.pufferfish.host/job/Pufferfish-Purpur-1.17", latest=latest)))
    tasks.append(asyncio.create_task(get_jenkins_artifact("pufferfish", "https://ci.pufferfish.host/job/Pufferfish-Purpur-1.18", latest=latest)))
    tasks.append(asyncio.create_task(get_jenkins_artifact("pufferfish", "https://ci.pufferfish.host/job/Pufferfish-1.17", latest=latest)))
    tasks.append(asyncio.create_task(get_jenkins_artifact("pufferfish", "https://ci.pufferfish.host/job/Pufferfish-1.18", latest=latest)))
    tasks.append(asyncio.create_task(get_jenkins_artifact("pufferfish", "https://ci.pufferfish.host/job/Pufferfish-1.19", latest=latest)))
    return await extend_tasks(tasks=tasks)

async def pocketmine(latest: bool = False):
    return await get_github_release("pmmp", "PocketMine-MP", latest=latest)

async def arclight(latest: bool = False):
    return await get_github_release("IzzelAliz", "Arclight", latest=latest)

async def lightfall(latest: bool = False):
    return await get_github_release("ArclightPowered", "lightfall", latest=latest)

async def catserver(latest: bool = False):
    catserver_jenkins = "https://jenkins.rbqcloud.cn:30011"
    tasks = []
    tasks.append(asyncio.create_task(get_jenkins_artifact("catserver", f"{catserver_jenkins}/job/CatServer-1.12.2", latest=latest)))
    tasks.append(asyncio.create_task(get_jenkins_artifact("catserver", f"{catserver_jenkins}/job/CatServer-1.16.5", latest=latest)))
    tasks.append(asyncio.create_task(get_jenkins_artifact("catserver", f"{catserver_jenkins}/job/CatServer-1.18.2", latest=latest)))
    return await extend_tasks(tasks=tasks)

async def forge(sourse: str = "forge", latest: bool = False):
    def format_file_info(build_info: dict, file: dict):
        mcv = build_info["mcversion"]
        ver = build_info["version"]
        # fucking forge prerelease
        if "pre" in mcv:
            url = f'https://maven.minecraftforge.net/net/minecraftforge/forge/{mcv}-{ver}-prerelease/forge-{mcv}-{ver}-prerelease-{file["category"]}.{file["format"]}'
        # if branch
        elif build_info["branch"] is not None:
            url = f'https://maven.minecraftforge.net/net/minecraftforge/forge/{mcv}-{ver}-{build_info["branch"]}/forge-{mcv}-{ver}-{build_info["branch"]}-{file["category"]}.{file["format"]}'
        else:
            url = f'https://maven.minecraftforge.net/net/minecraftforge/forge/{mcv}-{ver}/forge-{mcv}-{ver}-{file["category"]}.{file["format"]}'
        
        # 换镜像源
        if sourse == "mcbbs":
            url = url.replace("https://maven.minecraftforge.net", "https://download.mcbbs.net/maven")
        elif sourse == "bmclapi":
            url = url.replace("https://maven.minecraftforge.net", "https://bmclapi2.bangbang93.com/maven")

        name = os.path.join("forge", mcv, ver, f'forge-{mcv}-{ver}-{file["category"]}.{file["format"]}')

        if "hash" in file:
            return {"url": url, "name": name, "md5": file["hash"]}
        return {"url": url, "name": name}

    async def get_version(version: str):
        version_info = await _get_json(f'https://bmclapi2.bangbang93.com/forge/minecraft/{version}', no_proxy=True)
        results = []
        if latest:
            for file in version_info[-1]["files"]:
                results.append(format_file_info(version_info[-1], file))
        else:
            for build in version_info:
                for file in build["files"]:
                    results.append(format_file_info(build, file))
        return results

    support_versions = await _get_json("https://download.mcbbs.net/forge/minecraft", no_proxy=True)
    tasks = []
    for version in support_versions:
        tasks.append(asyncio.create_task(get_version(version)))
    return await extend_tasks(tasks=tasks)

async def spigot():
    results = []
    for file in (files := await get_github_release("ZGIT-Network", "MinecraftActions", latest=True, return_raw=True)):
        if "craftbukkit" in file["name"]:
            project_type = "craftbukkit"
        elif "spigot" in file["name"]:
            project_type = "spigot"
        else:
            continue
        results.append({"url": file["browser_download_url"], "name": os.path.join(project_type, file["name"]), "size": file["size"]})
    return results
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spigot())