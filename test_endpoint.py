import requests


def main():
    with requests.Session() as session:
        login = session.post(
            "http://127.0.0.1:8000/auth/token",
            data={"username": "manager", "password": "manager123"},
        )
        print(f"Login Status Code: {login.status_code}")
        response = session.get("http://127.0.0.1:8000/manager/orders/")
        print(f"Orders Status Code: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    main()
