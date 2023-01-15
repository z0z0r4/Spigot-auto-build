import traceback
import asyncio
import json
import aiohttp
import requests
import os
import platform
import hashlib
import parse

PROXY = None
# PROXY = "http://127.0.0.1:7890"
TIMEOUT = 300

CACHE_FOLDER = "cache" # 缓存目录

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

def check_hash(hash: str, path: str):
    if len(hash) == 40:
        hash_ = hashlib.sha1()
    elif len(hash) == 32:
        hash_ = hashlib.md5()
    else:
        raise ValueError("Unknown hash type")

    with open(path, "rb") as f:
        hash_.update(f.read())
        return hash_.hexdigest() == hash

async def get_file(url: str, name: str, sem: asyncio.Semaphore, timeout : int = TIMEOUT):
    async with sem:
        print(f'Downloading: {url}')
        _i = 0 # retry times
        while _i < 3:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(timeout)) as sess:
                    async with sess.get(url=url, proxy=PROXY) as resp:
                        if resp.status == 200:
                            with open(name, "wb") as f:
                                async for chunk in resp.content.iter_chunked(1024):
                                    f.write(chunk)
                            print(f'Downloaded: {name}')
                            return
                        elif resp.status == 400:
                            print(f'404 Not Found {url}')
                            break
            except Exception:
                _i += 1
                traceback.print_exc()

async def download(url: str, name: str, sem: asyncio.Semaphore):
    async with sem:
        name = os.path.join(CACHE_FOLDER, name)
        if not os.path.exists(os.path.dirname(name)):
            os.makedirs(os.path.dirname(name))
        await get_file(url, name, sem)

async def get_results(): # 添加新的镜像源
    results = []
    # results.extend(await parse.vanilla())
    # results.extend(await parse.papermc())
    # results.extend(await parse.spigot())
    # results.extend(await parse.arclight())
    # results.extend(await parse.bungeecord())
    # results.extend(await parse.floodgate())
    # results.extend(await parse.catserver())
    # results.extend(await parse.geyser())
    # results.extend(await parse.lightfall())
    # results.extend(await parse.mohist())
    # results.extend(await parse.nukkitx())
    # results.extend(await parse.pocketmine())
    # results.extend(await parse.pufferfish())
    # results.extend(await parse.sponge())
    results.extend(await parse.forge(sourse="mcbbs"))
    
    with open("result.json", "w") as res:
        json.dump(results, res)
    return results

async def main():
    results = await get_results()
    print(f"共计 {len(results)} 待处理")
    tasks = []
    sem = asyncio.Semaphore(64) # 限制 16 并发

    for result in results:
        # 校验文件是否存在且正确
        if os.path.exists(os.path.join(CACHE_FOLDER, result["name"])):
            if "md5" in result or "sha1" in result:
                if "md5" in result:
                    hash = result["md5"]
                else:
                    hash = result["sha1"]
                hash_result = check_hash(hash, os.path.join(CACHE_FOLDER, result["name"]))
                if hash_result:
                    print(f'Cached: {result["name"]}')
                    continue # 跳过已存在的文件
            os.remove(os.path.join(CACHE_FOLDER, result["name"])) # 删除不确定/不完整文件
        tasks.append(asyncio.create_task(download(result["url"], result["name"], sem)))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())