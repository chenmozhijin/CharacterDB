# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright (c) 2024 沉默の金
import json
import logging
import time

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="[%(levelname)s]%(asctime)s(%(lineno)d):%(message)s")
surname_list = []
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"


def get_surnames(page: int) -> list:
    surnames = []
    url = "https://myoji-yurai.net/prefectureRanking.htm"
    params = {
        "prefecture": "全国",
        "page": page,
    }
    response = requests.get(url, params=params, timeout=10, headers={"User-Agent": UA})
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    content: BeautifulSoup = soup.find("div", {"id": "content"})
    for table in content.find_all("table", {'class': 'simple'}):
        thead = table.find("thead")
        if thead is None or thead.text != "\n\n順位\n名字\n人数":
            continue

        for tr in table.find_all("tr", {'class': 'odd'}):
            for a in tr.find_all("a"):
                surnames.append(a.text)
    return surnames


for page in range(80):
    logging.info(f"Getting surnames from page {page}")
    surname_list.extend(get_surnames(page))
    time.sleep(1)

with open("jp_surnames.json", "w", encoding="utf-8") as f:
    json.dump(surname_list, f, ensure_ascii=False, indent=4)
