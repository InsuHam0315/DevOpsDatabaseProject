from services.data_collector import fetch_its_traffic, fetch_weather

ITS_KEY = "b187e2a751d24ce58c07f2a6476239a1"
WEATHER_KEY = "f0f851acbdfb6510d6da679cac76197f7f6b4b767c32f8aecb6a7c742fa76dce"

if __name__ == "__main__":
    its_csv = fetch_its_traffic(ITS_KEY)
    weather_csv = fetch_weather(WEATHER_KEY, nx=55, ny=68)
    print("ITS:", its_csv)
    print("Weather:", weather_csv)