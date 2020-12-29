import random

proxy_list = [
    '117.765.46.26:44708'
]


def random_proxy():
    proxy = random.choice(proxy_list)
    return proxy
