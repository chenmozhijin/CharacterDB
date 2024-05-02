# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright (c) 2024 沉默の金
from __future__ import annotations

import html
import json
import logging

import mwparserfromhell
import regex as re
from lxml import etree
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="[%(levelname)s]%(asctime)s(%(lineno)d):%(message)s")
subjects = {}
# 定义解析器并打开 XML 文件
context = etree.iterparse(r"Z:\yy\project\Dataset\zhwiki-latest-pages-articles.xml", events=("start", "end"))
template_names = {}
have_char_list = []


def process_jawiki_content(content: str) -> str:
    global template_names

    def content_clear(content: str) -> str:
        content = re.sub(r"<!--.*?-->", "", content)
        content = re.sub(r"<!--\s*|\s*-->", "", content)
        content = re.sub(r"\{\{[^}]*$", "", content)

        return content.strip()
    wikicode = mwparserfromhell.parse(content)
    # 遍历所有链接,并替换为链接文字
    for link in wikicode.filter_wikilinks():
        link_title = link.title
        try:
            wikicode.replace(link, link_title)
        except Exception:
            logging.exception("模板处理错误")

    # 遍历所有模板，并替换为普通文本
    to_replace = []
    for template in wikicode.filter_templates():
        # 获取模板名
        template_plain_text = ""
        template_name = template.name
        if str(template_name) in template_names:
            template_names[str(template_name)] += 1
        else:
            template_names[str(template_name)] = 1
        # 获取模板参数
        template_params = template.params
        try:
            match template_name:
                case "R" | "Refnest" | "refnest" | "Sfn" | "efn" | "Efn2" | "efn2" | "ISBN2" | "Anchors" | "anchors":
                    template_plain_text = ""
                case "仮リンク" | "en":
                    template_plain_text = str(template.get(1).value)
                case "要出典範囲":
                    template_plain_text = str(template.get("1").value)
                    if not template_plain_text:
                        template_plain_text = str(template.get(1).value)
                case "Visible anchor" | "Vanc":
                    template_plain_text = str(template.get(1).value)
                case "読み仮名" | "Ruby" | "ruby" | "読み仮名_ruby不使用" | "読み仮名 ruby不使用":
                    if template.get(2).value:
                        template_plain_text = f"{template.get(1).value}({template.get(2).value})"
                    else:
                        template_plain_text = str(template.get(1).value)
                case "!":
                    template_plain_text = "|"
                case "補助漢字フォント" | "JIS2004フォント":
                    if "&#" in template.get(1).value:
                        template_plain_text = html.unescape(str(template.get(1).value))
                    else:
                        template_plain_text = str(template.get(1).value)
                case "lang" | "Lang":
                    template_plain_text = str(template.get(2).value)
                case "Harvnb" | "Harvnb ":
                    if "=" not in template_params[1]:
                        template_plain_text = str(template.get(1).value) + str(template.get(2).value)
                    else:
                        template_plain_text = str(template.get(1).value)
        except Exception:
            logging.exception("模板处理错误")
        else:
            to_replace.append((template, template_plain_text))

    to_replace.reverse()
    for template, template_plain_text in to_replace:
        for index, content in enumerate(to_replace):
            template_, template_plain_text_ = content
            if str(template) in template_plain_text_:
                to_replace[index] = (template_, template_plain_text.replace(str(template), template_plain_text_))
                break
        else:
            try:
                wikicode.replace(template, template_plain_text)
            except Exception:  # noqa: PERF203
                logging.exception("模板处理错误")

    return content_clear(wikicode.strip_code())


def process_jawiki_titles(titles: list[str]) -> list:
    def title_clear(title: str) -> str:
        if title.startswith("映画"):
            title = re.sub(r"^映画", "", title).strip()
        title = re.sub(r"<(.*?)>.*?<\\\1>", "", title)
        title = re.sub(r"\(.*?\)", "", title)
        title = re.sub(r"（.*?）", "", title)
        title = re.sub(r"【.*?】", "", title)
        title = re.sub(r"<.*?>", "", title)
        # title = re.sub(r"\[\[(.*?)\]\]", r"\1", title)

        return title.strip()

    result_titles = []
    for title in titles:
        no_chear_titles = []
        if title.strip().startswith(("|", "(", "（", "【")):
            continue
        if "<br />" in title or "<br>" in title:
            parts = []
            parts_ = title.split("<br />")
            for part in parts_:
                if "<br>" in part:
                    parts.extend(part.split("<br>"))
                else:
                    parts.append(part)
            if not parts[0].endswith("版"):
                no_chear_titles.append(parts[0])
            for part in parts[1:]:
                if part.strip().startswith(("|", "※", "(", "（", "【")):
                    continue
                if part.strip().endswith("版"):
                    continue
                if "-" in part and ":" in part:
                    # 时间段
                    continue
                no_chear_titles.append(part)
        else:
            no_chear_titles.append(title)
        result_titles.extend([process_jawiki_content(title_clear(t)) for t in no_chear_titles])

    return list(set(result_titles))


def extract_data() -> dict:
    logging.info("开始提取数据")
    title = None
    # 遍历解析器生成的事件流
    for event, element in tqdm(context):
        if not element.tag.endswith(("title", "text")):
            element.clear()
            continue
        if event == "start" and element.tag.endswith("title"):
            start_title = element.text
            element.clear()
        elif event == "end" and element.tag.endswith("title"):
            if start_title:
                title = start_title + element.text.strip() if element.text else start_title
            else:
                title = element.text
            start_title = None
        elif event == "start" and element.tag.endswith("text"):
            start_page_content = element.text
            element.clear()
        elif event == "end" and element.tag.endswith("text"):
            if start_page_content:
                if element.text:
                    page_content = start_page_content + element.text
                else:
                    page_content = start_page_content
            else:
                page_content = element.text
            start_page_content = None
            element.clear()

            if "角色列表" in title:
                char_texts = page_content
                title = title.replace("角色列表", "")
                have_char_list.append(title)
            else:
                if not page_content or "登場人物" not in page_content:
                    continue

                char_texts: list[str] = re.findall(r"(=+)\s*登場人物\s*\1((?:\n.*?)*?)\n\1[^=]", page_content)

                if not char_texts or char_texts[0][1].strip().startswith(("{{Main|", "{{main|")):
                    continue
                char_texts = [text[1] for text in char_texts]
            char_text_dict = {}
            char_key = None
            for char_text in char_texts:
                for line in char_text.split("\n"):
                    if line.startswith(";"):
                        char_key = line.replace(";", "").strip()
                        char_text_dict[char_key] = ""
                    elif line.startswith(":"):
                        if char_key:
                            char_text_dict[char_key] += line.replace(":", "").replace("*", "").strip()
                    else:
                        char_key = None
            if not char_text_dict:
                continue
            title_list = re.findall(r"\|(?:標題)\s*=\s*(.*)", page_content)
            title_list.append(title)
            title_list: list[str] = [t.strip() for t in set(title_list)]
            for index, title_ in enumerate(title_list):
                if title_.startswith("[[") and title_.endswith("]]"):
                    title_ = title_[2:-2]
                    if "|" in title_:
                        title_ = title_.split("|")[0]
                title_list[index] = title_
                if title_ in ["電視動畫"]:
                    title_list.remove(title_)

            subjects[len(subjects)] = {"titles": title_list, "char": char_text_dict}

        else:
            element.clear()
    logging.info("提取数据完成")
    return subjects


subjects = extract_data()
with open("zhwiki_.json", "w", encoding="utf-8") as f:
    json.dump(subjects, f, ensure_ascii=False, indent=4)
subjects = {}
with open("zhwiki_.json", encoding="utf-8") as f:
    O_subjects: dict = json.load(f)
    for key, value in O_subjects.items():
        subjects[int(key)] = value

logging.info("开始处理标题")
for i in tqdm(range(len(subjects)), total=len(subjects)):
    subjects[i]["titles"] = process_jawiki_titles(subjects[i]["titles"])

logging.info("处理标题完成")

logging.info("开始处理内容")
for i in tqdm(range(len(subjects)), total=len(subjects)):
    if i == 16:
        pass
    subject: dict = subjects[i]
    new_char_dict = {}
    for char_key, char_text in subject["char"].items():
        new_char_key = process_jawiki_content(char_key)
        new_char_text = process_jawiki_content(char_text)
        new_char_dict[new_char_key] = new_char_text
    subject["char"] = new_char_dict

logging.info("处理内容完成")


with open("template_names.json", "w", encoding="utf-8") as f:
    json.dump(template_names, f, ensure_ascii=False, indent=4)

with open("zhwiki.json", "w", encoding="utf-8") as f:
    json.dump(subjects, f, ensure_ascii=False, indent=4)
