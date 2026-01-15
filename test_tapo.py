import os
from pprint import pprint
import asyncio

from dotenv import load_dotenv
from tplinkcloud import TPLinkDeviceManager

load_dotenv()

email = os.getenv("TAPO_EMAIL")
password = os.getenv("TAPO_PASSWORD")
device_manager = TPLinkDeviceManager(email, password)


async def get_device_status():
    devices = await device_manager.get_devices()

    if not devices:
        raise Exception("Devices not found")

    device = devices[0]
    device_info = device.device_info

    if device_info.device_name != "P100":
        raise Exception("Device found but unknown name")
    print("Device info= ")
    pprint(device_info.__dict__)
    print()

    return device_info.status


async def main():
    status = await get_device_status()
    print(f"{status=}")


if __name__ == "__main__":
    asyncio.run(main())
