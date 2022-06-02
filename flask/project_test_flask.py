import requests

BASE = 'http://127.0.0.1:5000/'  # server

## Test election scenario

# test_get_URL = '/api/analytics/diversity/tweets'
# response = requests.get(BASE + test_get_URL)
# print(response.json())

# test_get_URL = "/api/analytics/diversity/language"
# response = requests.get(BASE + test_get_URL)
# print(response.json())

# test_get_URL = "/api/analytics/diversity/sentiment"
# response = requests.get(BASE + test_get_URL)
# print(response.json())


## Test socioeconomic scenario

# test_get_URL = "/api/analytics/socioeconomic/tweets"
# response = requests.get(BASE + test_get_URL)
# print(response.json())

# test_get_URL = "/api/analytics/socioeconomic/seifa/"
# response = requests.get(BASE + test_get_URL)
# print(response.json())

test_get_URL = "/api/analytics/socioeconomic/election-issues/"
response = requests.get(BASE + test_get_URL)
print(response.json())
