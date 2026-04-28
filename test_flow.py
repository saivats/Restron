import requests


BASE_URL = "http://127.0.0.1:8000"


def main():
    session = requests.Session()

    print("Logging in as manager...")
    login_data = {"username": "manager", "password": "manager123"}
    login = session.post(f"{BASE_URL}/auth/token", data=login_data)
    print(login.status_code, login.text)
    login.raise_for_status()

    print("Health check...")
    health = session.get(f"{BASE_URL}/health")
    print(health.status_code, health.text)

    print("Manager orders...")
    orders = session.get(f"{BASE_URL}/manager/orders/")
    print(orders.status_code, orders.text[:1000])

    print("Tables...")
    tables = session.get(f"{BASE_URL}/manager/tables/")
    print(tables.status_code, tables.text[:1000])


if __name__ == "__main__":
    main()
