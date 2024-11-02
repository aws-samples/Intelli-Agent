# get weather tool
import requests

def get_weather(city_name:str):
    if not isinstance(city_name, str):
        raise TypeError("City name must be a string")

    key_selection = {
        "current_condition": [
            "temp_C",
            "FeelsLikeC",
            "humidity",
            "weatherDesc",
            "observation_time",
        ],
    }
    
    try:
        resp = requests.get(f"https://wttr.in/{city_name}?format=j1")
        resp.raise_for_status()
        resp = resp.json()
        ret = {k: {_v: resp[k][0][_v] for _v in v} for k, v in key_selection.items()}
    except:
        import traceback

        ret = ("Error encountered while fetching weather data!\n" + traceback.format_exc()
        )

    return str(ret)


def lambda_handler(event_body,context=None):
    result = get_weather(**event_body['kwargs'])
    return {"code":0, "result": result}