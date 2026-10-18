import urllib.request
import json

url = "https://493ce1c9-ffb2-4dab-b1c2-b28e5cb606a5.us-west-1-0.aws.cloud.qdrant.io:6333/collections"
api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MzdjYzk4ZGItMTgzNy00MTU1LThmMmQtNGFiMjA4MDkzYjE3In0.0isGevH0vr7ZzMgjEfKNVFM24Db5uNVQfsoLVHm6kZY"

req = urllib.request.Request(url)
req.add_header("api-key", api_key)

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())
    print(data)