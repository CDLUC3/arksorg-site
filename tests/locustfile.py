import random
import string
from locust import HttpUser, task, between

targets = [
"ark:24973/",
"ark:10265/",
"ark:40699/",
"ark:21205/",
"ark:28733/",
"ark:23263/",
"ark:72509/",
"ark:88435/",
"ark:41043/",
"ark:24630/",
"ark:18472/",
"ark:78325/",
"ark:77978/",
"ark:13030/",
"ark:58826/",
"ark:45492/",
"ark:70296/",
"ark:73876/",
"ark:88434/",
"ark:21549/",
"ark:18471/",
"ark:27366/",
"ark:48565/",
"ark:44803/",
"ark:45487/",
"ark:20867/",
"ark:55410/",
"ark:59854/",
"ark:74558/",
"ark:73535/",
"ark:57460/",
"ark:17106/",
"ark:80358/",
"ark:43436/",
"ark:88926/",
"ark:62929/",
"ark:28722/",
"ark:45150/",
"ark:72164/",
"ark:29419/",
"ark:99160/",
"ark:87920/",
"ark:88925/",
"ark:27363/",
"ark:60882/",
"ark:85147/",
"ark:20523/",
"ark:34890/",
"ark:80030/",
"ark:83454/",
"ark:39335/",
"ark:73879/",
"ark:64986/",
"ark:26683/",
"ark:77916/",
"ark:64300/",
"ark:58488/",
"ark:73878/",
"ark:32837/",
"ark:19153/",
"ark:18816/",
"ark:11289/",
"ark:32491/",
"ark:81968/",
"ark:65669/",
"ark:75788/",
"ark:53358/",
"ark:20522/",
"ark:19153/",
"ark:33862/",
"ark:71484/",
"ark:64301/",
"ark:81220/",
"ark:32153/",
"ark:37280/",
"ark:27019/",
"ark:44807/",
"ark:74901/",
"ark:19153/",
"ark:88120/",
"ark:87943/",
"ark:46518/",
"ark:33520/",
"ark:61907/",
"ark:86085/",
"ark:43435/",
"ark:43098/",
"ark:19153/",
"ark:19153/",
"ark:13004/",
"ark:75242/",
"ark:54379/",
"ark:29413/",
"ark:20180/",
"ark:61561/",
"ark:31810/",
"ark:71485/",
"ark:74219/",
"ark:81986/",
"ark:70458/",
]

def generate_random_string(length):
    """
    Generates a random string of a specified length
    containing uppercase letters, lowercase letters, and digits.
    """
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

class MyUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    @task
    def index(self):
        self.client.get("/")

    @task
    def api(self):
        self.client.get("/api")

    @task
    def resolve(self):
        target = random.choice(targets)
        sfx = generate_random_string(8)
        self.client.get(f"/{target}{sfx}", allow_redirects=False)

    @task
    def info(self):
        target = random.choice(targets)
        sfx = generate_random_string(8)
        self.client.get(f"/.info/{target}{sfx}")
