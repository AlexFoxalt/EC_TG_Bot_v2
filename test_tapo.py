import asyncio
import os
from tapo import ApiClient
from dotenv import load_dotenv

load_dotenv()

tapo_email = os.getenv("TAPO_EMAIL")
tapo_password = os.getenv("TAPO_PASSWORD")
device_ip = os.getenv("TAPO_DEVICE_IP")
client = ApiClient(tapo_email, tapo_password)


async def main():
    device = await client.p100(device_ip)
    device_info = await device.get_device_info()
    print(device_info.device_on)


if __name__ == "__main__":
    asyncio.run(main())
