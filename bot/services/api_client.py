
import aiohttp
from bot.utils.logger import logger
from bot.model.place import Place

async def add_custom_place(place: Place, session: aiohttp.ClientSession):
    data_to_post = {
        "id": 0,
        "nameOfPlace": f"{place.NameOfPlace}",
        "address": f"{place.Address}",
        "description": f"{place.Description}",
        "photo1": f"{place.Photo1}",
        "photo2": f"{place.Photo2}",
        "photo3": f"{place.Photo3}",
        "photo4": f"{place.Photo4}",
        "photo5": f"{place.Photo5}"
    }
    try:
        async with session.post(f"https://localhost:7124/api/custom/addPlace", json=data_to_post, ssl=False) as response:
            if response.status == 200:
                logger.info("custom place added")
                return True
            else:
                return False
    except Exception as e:
        logger.error(f"API Request Error: {e}")

