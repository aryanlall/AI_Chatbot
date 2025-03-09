import requests

url = "http://127.0.0.1:5000/request"
data = {
    "agent_type": "nlp",
    "query": "When is the next backlog exam?"
}

response = requests.post(url, json=data)
print("Response:", response.json())
