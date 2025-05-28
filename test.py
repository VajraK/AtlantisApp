import requests

token = "zShLF0tH6jnspwWkNk9uafy6R7O3u2Ia"
headers = {"Authorization": f"Token {token}"}

response = requests.get("http://localhost:3000/api/applications/", headers=headers)

print(response.status_code)
print(response.text)
