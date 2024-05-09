# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright (c) 2024 沉默の金
from __future__ import annotations

import json
import logging
import os
import re

import opencc
from janome.tokenizer import Token, Tokenizer
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="[%(levelname)s]%(asctime)s(%(lineno)d):%(message)s")

known_ja_names = ["亜門", "死神様", "宇白順", "九鳳院紫"]
maybe_ja_names = []
results = []

s2t_converter = opencc.OpenCC("s2t.json")
t2s_converter = opencc.OpenCC("t2s.json")

t = Tokenizer()


def get_jawiki_char_names(char_name: str) -> list[str]:
    result = []
    spilt_brackets = re.findall(r"\((.*?)\)", char_name)
    spilt_brackets += re.findall(r"（(.*?)）", char_name)
    no_brackets_names = re.split(r"\(.*?\)|（.*?）", char_name)
    for bracket in spilt_brackets:
        if re.findall(r"通称|版|,|-|\d\d\d\d|#", bracket):
            continue
        result.append(bracket)
    for name in no_brackets_names:
        if "#" in name:
            continue
        ja_en = re.findall(r"([\u3040-\u309F\u30A0-\u30FF・])+\s+([a-zA-Z ]+)", name.strip())
        if ja_en:
            for item in ja_en:
                result.extend(item)
        result.append(name)
    return list(set(result))


def load_data() -> (  # noqa: PLR0915
    tuple[
        list[dict],
        dict,
        dict,
        list,
        dict[str, list[dict]],
        dict[str, dict],
        dict[str, tuple[str, str]],
        dict[str, dict],
    ]
):
    logging.info("开始加载jp_surnames.json")
    with open("jp_surnames.json", encoding="utf-8") as file:
        jp_surnames = json.load(file)

    logging.info("开始加载jawiki相关数据")
    with open("jawiki.json", encoding="utf-8") as file:
        jawiki: dict = json.load(file)

    jawiki_mapping = {}
    for w_id, value in tqdm(jawiki.items()):
        w_chars: dict = value.get("char", [])
        for w_char in w_chars.items():
            for name in get_jawiki_char_names(w_char[0]):
                if name not in jawiki_mapping:
                    jawiki_mapping[name] = []
                jawiki_mapping[name].append((w_id, w_char[0]))
    logging.info("开始加载bangumi相关数据")
    logging.info("开始加载character.jsonlines")
    with open("character.jsonlines", encoding="utf-8") as file:
        contents = [json.loads(line) for line in file]
    logging.info("开始加载subject-characters.jsonlines")
    with open("subject-characters.jsonlines", encoding="utf-8") as file:
        subject_characters = [json.loads(line) for line in file]
    logging.info("开始加载subject.jsonlines")
    with open("subject.jsonlines", encoding="utf-8") as file:
        o_subjects = [json.loads(line) for line in file]

    logging.info("开始加载VNDB相关数据")

    logging.info("开始加载chars_traits")
    chars_traits: dict[str, list] = {}
    # tsv header: id	tid	spoil	lie
    with open(os.path.join("vndb", "db", "chars_traits"), encoding="utf-8") as file:
        for line in tqdm(file):
            info_list = line.split("\t")
            if info_list[0] not in chars_traits:
                chars_traits[info_list[0]] = []
            chars_traits[info_list[0]].append(info_list[1])

    logging.info("开始加载traits")
    traits: dict[str, str] = {}
    # tsv header: id	gid	gorder	defaultspoil	sexual	searchable	applicable	name	alias	description
    with open(os.path.join("vndb", "db", "traits"), encoding="utf-8") as file:
        for line in tqdm(file):
            info_list = line.split("\t")
            traits[info_list[0]] = info_list[7]

    logging.info("开始加载traits_parent")
    traits_parent: dict[str, str] = {}
    traits_parents: set = set()
    # tsv header: id	parent	main
    with open(os.path.join("vndb", "db", "traits_parents"), encoding="utf-8") as file:
        for line in tqdm(file):
            info_list = line.split("\t")
            traits_parent[info_list[0]] = info_list[1]
            traits_parents.add(info_list[1])

    logging.info("开始加载vn_titles")
    vn_titles: dict[str, list] = {}  # vid titles
    # tsv header: id	lang	official	title	latin
    with open(os.path.join("vndb", "db", "vn_titles"), encoding="utf-8") as file:
        for line in tqdm(file):
            info_list = line.split("\t")
            if info_list[0] not in vn_titles:
                vn_titles[info_list[0]] = []
            vn_titles[info_list[0]].append(info_list[3])

    logging.info("开始加载chars_vns")
    chars_vns: dict[str, list] = {}
    # tsv header: id	vid	rid	role	spoil
    with open(os.path.join("vndb", "db", "chars_vns"), encoding="utf-8") as file:
        for line in tqdm(file):
            info_list = line.split("\t")
            if info_list[0] not in chars_vns:
                chars_vns[info_list[0]] = []
            chars_vns[info_list[0]].append(info_list[1])

    logging.info("开始加载chars")
    chars: dict[str, dict] = {}
    name_chars_mapping: dict[str, list[dict]] = {}
    # tsv header: id	image	gender	spoil_gender	bloodt	cup_size	main	s_bust	s_waist	s_hip	b_month	b_day	height	weight	main_spoil	age	name	latin	alias	description
    with open(os.path.join("vndb", "db", "chars"), encoding="utf-8") as file:
        for line in tqdm(file):
            info_list = line.split("\t")
            for index, item in enumerate(info_list):
                if item in ["\\N", "", "unknown"]:
                    info_list[index] = None

            char_subjects = []
            for vn_id in chars_vns.get(info_list[0], []):
                if vn_id not in vn_titles:
                    continue
                char_subjects.extend(vn_titles[vn_id])

            info_dict = {
                "id": info_list[0],
                # "image": info_list[1],
                # "gender": info_list[2],
                # "spoil_gender": info_list[3],
                "bloodt": info_list[4],
                "cup_size": info_list[5],
                "main": info_list[6],
                "bust": info_list[7],
                "waist": info_list[8],
                "s_hip": info_list[9],
                "b_month": info_list[10],
                "b_day": info_list[11],
                "height": info_list[12],
                "weight": info_list[13],
                "age": info_list[15],
                "name": info_list[16],
                "latin": info_list[17],
                "subjects": char_subjects,
                "traits": {},
            }
            chars[info_dict["id"]] = info_dict

            if info_list[16]:
                if info_list[16] not in name_chars_mapping:
                    name_chars_mapping[info_list[16]] = []
                if info_list[16].replace(" ", "") not in name_chars_mapping:
                    name_chars_mapping[info_list[16].replace(" ", "")] = []
                name_chars_mapping[info_list[16]].append(info_dict["id"])
                name_chars_mapping[info_list[16].replace(" ", "")].append(info_dict["id"])
            if info_list[17]:
                if info_list[17] not in name_chars_mapping:
                    name_chars_mapping[info_list[17]] = []
                name_chars_mapping[info_list[17]].append(info_dict["id"])

    logging.info("开始处理subjects")
    o_subjects_dict = {item["id"]: item for item in o_subjects}
    o_subjects = None
    subjects_mapping = {}

    logging.info("开始处理subject-characters映射表")
    total = len(subject_characters)
    for subject_character in tqdm(subject_characters, total=total):
        character_id = subject_character["character_id"]
        subject_id = subject_character["subject_id"]
        role_type = subject_character["type"]  # 角色类型,1为主要角色,2为次要角色

        subject = o_subjects_dict.get(subject_id)

        if subject is None:
            continue
        subject_name = subject["name"]
        subject_zh_name = subject["name_cn"]
        subject_type: int = subject["type"]
        if character_id not in subjects_mapping:
            subjects_mapping[character_id] = []
        subjects_mapping[character_id].append(
            {
                "id": subject_id,
                "name": subject_name,
                "zh_name": subject_zh_name,
                "type": subject_type,
                "role_type": role_type,
            },
        )

    logging.info("开始处理chars")
    total = len(chars_traits)
    for char_id, trait_ids in tqdm(chars_traits.items(), total=total):
        traits_dict = {}
        for trait_id in trait_ids:
            # if trait_id not in traits_parents:
            trait = traits[trait_id][:]
            parent_list = []

            next_id = trait_id[:]
            while True:
                traits_parent_id = traits_parent.get(next_id)
                if traits_parent_id:
                    traits_parent_name = traits[traits_parent_id][:]
                    parent_list.append(traits_parent_name)
                else:
                    break
                next_id = traits_parent_id
                parent_list.reverse()

            if parent_list[0] not in traits_dict:
                traits_dict[parent_list[0]] = []
            traits_dict[parent_list[0]].append(trait)

        chars[char_id]["traits"] = traits_dict
    return (
        contents,
        subjects_mapping,
        o_subjects_dict,
        jp_surnames,
        name_chars_mapping,
        chars,
        jawiki_mapping,
        jawiki,
    )


(
    contents,
    subjects_mapping,
    o_subjects_dict,
    jp_surnames,
    name_chars_mapping,
    chars,
    jawiki_mapping,
    jawiki,
) = load_data()


def clear(content: str) -> str:
    content = content.replace("\t", "")
    content = content.replace("\n", "")
    content = content.replace("\r", "")
    content = content.replace("‎", "")
    content = content.replace("\u3000", "")
    content = re.sub(r"^ +| +$", "", content)
    return re.sub(r"[（(\[【［][^)）】\]］]*[】］\])）]", "", content)


def is_english_with_symbols(text: str) -> bool:
    # 使用正则表达式匹配英文字母、数字、空格和常见符号
    pattern = r'^[a-zA-Z0-9\s\.,!@#\$%\^&\*\(\)-_=\+;:\'"\[\]\{\}<>\?/\\|`~·↓]*$'
    return bool(re.match(pattern, text))


def subject_name_compare(name1: str, name2: str) -> bool:
    def clear2(name: str) -> str:
        name = name.replace("*", "＊")  # 千恋＊万花  # noqa: RUF003
        name = name.replace("「", "")
        return name.replace("」", "")

    name1 = clear2(clear(name1.replace(" ", "")))
    name2 = clear2(clear(name2.replace(" ", "")))
    if name1 == name2:
        return True
    if len(name1) > 4 and len(name2) > 4 and name1[:4] == name2[:4]:
        return True
    return False


def is_japanese(text: str) -> bool:
    # 使用正则表达式匹配日文字符范围
    if re.search(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", text):
        return True
    return False


def include_japanese(text: str) -> bool:
    if re.search(r"[\u3040-\u309F\u30A0-\u30FF]", text):
        return True
    return False


def is_jp_name(text: str) -> bool:
    if is_english_with_symbols(text):
        return False
    if include_japanese(text):
        return True
    if is_japanese(text) and s2t_converter.convert(text) == text and len(text) > 3:
        return True
    if text in known_ja_names:
        return True
    return any(text.startswith(jp_surname) for jp_surname in jp_surnames)


def is_zh_name(text: str) -> bool:
    text = text.strip()
    if " " in text:
        return False
    if not re.fullmatch(r"[\u4E00-\u9FFF）（)(]+", text):
        return False
    if t2s_converter.convert(text) != text:
        return False
    return True


def is_from_ja_subject(subjects: list[dict]) -> bool:
    subject_ids = [subject["id"] for subject in subjects]
    for subject_id in subject_ids:
        subject = o_subjects_dict.get(subject_id)
        if subject is None:
            continue
        if include_japanese(subject["name"]):
            return True
        tags = [t["name"] for t in subject.get("tags", [])]
        for tag in tags:
            if tag in ["日本", "日本动画", "日本漫画", "日系"]:
                return True
    return False


def is_from_zh_subject(subjects: list[dict]) -> bool:
    subject_ids = [subject["id"] for subject in subjects]
    for subject_id in subject_ids:
        subject = o_subjects_dict.get(subject_id)
        if subject is None:
            continue
        tags = [t["name"] for t in subject.get("tags", [])]
        for tag in tags:
            if tag in [
                "国产",
                "中国",
                "中国动画",
                "国产动画",
                "国产游戏",
                "中国大陆",
                "国产Galgame",
            ]:
                return True
    return False


def get_jawiki_text(names: list[str], subjects: list[dict]) -> tuple[list, list]:
    result = []
    w_names = []
    for name in names:
        id_names = jawiki_mapping.get(name, [])
        for id_name in id_names:
            w_id = id_name[0]
            w_name = id_name[1]
            w_subjecs = jawiki[w_id]["titles"]
            for subject in subjects:
                for w_subject in w_subjecs:
                    if subject_name_compare(w_subject, subject["name"]):
                        w_names += get_jawiki_char_names(w_name)
                        result.append(jawiki[w_id]["char"][w_name].strip())
    return list(set(result)), list(set(w_names))


def get_token_info(token: Token) -> tuple[str, str]:
    if token.extra:
        return token.extra[0], token.node.surface
    return token.node.part_of_speech, token.node.surface


def analyze(names: list[str], subjects: list[dict], summary: str) -> tuple[list, list]:  # noqa: PLR0915
    def p(summary: str) -> list:  # noqa: PLR0915
        result = []
        summary = summary.strip()
        if not summary:
            return result
        is_ja = include_japanese(summary)
        summary_s: list[str] = re.split(r"[。，,]|\r\n", summary)
        summary_s: list[str] = [s for s in summary_s if s.strip() != ""]
        zh_num = [
            "一",
            "二",
            "三",
            "四",
            "五",
            "六",
            "七",
            "八",
            "九",
            "十",
            "十一",
            "十二",
            "十三",
            "十四",
            "十五",
            "十六",
            "十七",
            "十八",
            "十九",
            "二十",
        ]
        zh_num_re = rf"(?:{'|'.join(zh_num)})"
        zh = {
            re.compile(r"(?:男|女)?主角"): False,
            re.compile(r"(?:男|女)?主人公"): False,
            "主要人物": False,
            "妹妹": True,
            "姊姊": True,
            "姊夫": True,
            "姐姐": True,
            "哥哥": True,
            re.compile(r"(?:亲生)?父亲"): True,
            re.compile(r"(?:亲生)?母亲"): True,
            "爷爷": True,
            "奶奶": True,
            "外公": True,
            "外婆": True,
            re.compile(r"外?祖父"): True,
            re.compile(r"外?祖母"): True,
            "丈夫": True,
            "妻子": True,
            re.compile(r"前?恋人"): True,
            re.compile(r"前?(?:男|女)朋友"): True,
            re.compile(r"前(?:夫|妻)"): True,
            "团长": True,
            re.compile(r"(?:大|小)?儿子"): True,
            re.compile(r"(?:大|小)?女儿"): True,
            "混血儿": False,
            "独生(?:女|子)": True,
            re.compile(r"骑士"): False,
            re.compile(r"(?:转|留|男|女|.年级)?学生"): False,
            re.compile(r"(?:大学|高中|初中|小学)生"): False,
            re.compile(r"(?:后|前)辈"): True,
            "师弟": True,
            "师妹": True,
            "店小二": False,
            re.compile(r"美?少女"): False,
            "搭档": True,
            "少年": False,
            "伙伴": False,
            "小姐": False,
            "千金": False,
            "随侍": False,
            "隨從": False,
            "从者": True,
            "拥有者": True,
            "专家": False,
            "超能力者": False,
            re.compile(r"(?:男|女)孩"): False,
            "同班同学": True,
            re.compile(r"(?:男|女)?医生"): False,
            re.compile(r"(?:男|女)?警察"): False,
            re.compile(r"(?:男|女)?老师"): False,
            "刑警": False,
            "(?:天才)?黑客": False,
            "制作人": True,
            "当家": True,
            "助手": True,
            "女仆": False,
            "故友": True,
            "飞行员": False,
            "科学家": False,
            "研究员": False,
            "首领": True,
            re.compile(rf"第?{zh_num_re}公主"): False,
        }
        ja = {
            '目的のために使役される者': ('被利用者', True),
            '姦計を企てる者': ('阴谋家', False),
            '最後の生き残り': ('最后幸存者', False),
            '組織のリーダー': ('组织领导者', False),
            '仲直りした人物': ('和解者', False),
            '罠に落ちた人物': ('陷阱受害者', False),
            '腹違いの妹': ('同父异母的妹妹', True),
            '腹違いの姉': ('同父异母的姐姐', True),
            '腹違いの長兄': ('同父异母的长兄', True),
            '腹違いの兄': ('同父异母的兄弟', True),
            '腹違いの弟': ('同父异母的弟弟', True),
            'バイオロイド': ('生化人', False),
            '忘れられた者': ('被遗忘者', False),
            'アンドロイド': ('人造人', False),
            '遭遇する人物': ('遭遇者', False),
            '謎めいた人物': ('神秘人物', False),
            '騙された人物': ('被欺骗者', False),
            '守るべき存在': ('值得守护者', False),
            '悪行の犠牲者': ('罪恶受害者', False),
            '虐待の被害者': ('虐待受害者', False),
            '苦悩する人物': ('苦恼者', False),
            '実験の被験者': ('实验对象', False),
            '封印されし者': ('被封印者', False),
            '翻弄される者': ('被玩弄者', False),
            '謎めいた存在': ('神秘存在', False),
            '義理の兄弟': ('继兄弟', True),
            '義理の姉妹': ('继姐妹', True),
            '義理の息子': ('继子', True),
            '義理の祖父': ('继祖父', True),
            '義理の祖母': ('继祖母', True),
            '義理の叔父': ('继叔父', True),
            '義理の叔母': ('继叔母', True),
            '対立する者': ('对立者', False),
            '偽りの仲間': ('虚假同伴', True),
            '英雄の師匠': ('英雄导师', False),
            '学問の師匠': ('学问导师', False),
            '闇の支配者': ('暗黑支配者', False),
            '悲劇の人物': ('悲剧人物', False),
            '苦しむ人物': ('受苦者', False),
            '使役する者': ('利用者', False),
            '後悔する者': ('后悔者', False),
            '謎めいた男': ('神秘男子', False),
            '謎めいた女': ('神秘女子', False),
            '魅了する者': ('魅惑者', False),
            '愛憎の対象': ('爱憎对象', False),
            '人生の指針': ('人生导师', True),
            '生徒会長': ('学生会长', False),
            '女性医師': ('女医生', False),
            '女子大生': ('女大学生', False),
            'ロボット': ('机器人', False),
            '義理の父': ('继父', True),
            '義理の母': ('继母', True),
            '義理の娘': ('继女', True),
            '義理の孫': ('继孙子/继孙女', True),
            '義理の 姪': ('继侄女/继侄子', True),
            '担任教師': ('班主任', False),
            '競争相手': ('竞争对手', True),
            'ライバル': ('对手', True),
            '裏切り者': ('叛徒', False),
            '結婚相手': ('配偶', False),
            '不倫相手': ('外遇对象', False),
            '影の存在': ('影子', False),
            '秘密組織': ('秘密组织', False),
            '裏の黒幕': ('幕后黑手', False),
            '人造人間': ('人造人', False),
            '心理学者': ('心理学家', False),
            '人間兵器': ('人类武器', False),
            '取り巻き': ('随从', False),
            '消えた者': ('消失者', False),
            '愛する者': ('爱人', True),
            '教える者': ('教导者', False),
            '主人公': ('主人公', False),
            '転入生': ('转学生', False),
            '老医師': ('老医生', False),
            '指揮官': ('指挥官', True),
            '警備員': ('警备员', True),
            '保安官': ('警长', True),
            '曽祖父': ('曾祖父', True),
            '従姉妹': ('堂姐妹', True),
            '従兄弟': ('堂兄弟', True),
            '幼馴染': ('青梅竹马', True),
            '同級生': ('同学', True),
            '従業員': ('员工', False),
            '捜査員': ('调查员', True),
            '配偶者': ('配偶', True),
            '嫌疑者': ('嫌疑人', False),
            '被告人': ('被告人', False),
            '守護者': ('守护者', False),
            '犯罪者': ('罪犯', False),
            '逃亡者': ('逃亡者', False),
            '裁判官': ('审判官', False),
            '追跡者': ('追踪者', False),
            '謎の男': ('神秘男子', False),
            '謎の女': ('神秘女子', False),
            '実験体': ('实验体', False),
            '生存者': ('幸存者', False),
            'スパイ': ('间谍', False),
            '諜報員': ('情报员', False),
            '内通者': ('内鬼', False),
            '依頼人': ('委托人', False),
            '復讐者': ('复仇者', False),
            '治癒者': ('治愈者', False),
            '堕落者': ('堕落者', False),
            '暗殺者': ('刺客', False),
            '尋問者': ('审讯者', False),
            '負傷者': ('受伤者', False),
            '狂信者': ('狂热者', False),
            '誘惑者': ('诱惑者', False),
            '共闘者': ('共同作战者', False),
            '再生者': ('再生者', False),
            '破滅者': ('毁灭者', False),
            '求愛者': ('求爱者', False),
            '逃避者': ('逃避者', False),
            '見習い': ('学徒', False),
            '悩む者': ('苦恼者', False),
            '掠奪者': ('掠夺者', False),
            '支配者': ('支配者', False),
            '壊す者': ('破坏者', False),
            '母親': ('母亲', True),
            '祖父': ('祖父', True),
            '老人': ('老人', False),
            '漁師': ('渔夫', False),
            '盗賊': ('盗贼', False),
            '女性': ('女性', False),
            '医師': ('医生', False),
            '警察': ('警察', False),
            '恋人': ('恋人', True),
            '戦友': ('战友', True),
            '青年': ('青年', False),
            '友人': ('友人', True),
            '彼女': ('女友', True),
            '魔物': ('魔物', False),
            '魔王': ('魔王', False),
            '神々': ('神', False),
            '王子': ('王子', False),
            '祖母': ('祖母', True),
            '叔父': ('叔父', True),
            '息子': ('儿子', True),
            '叔母': ('叔母', True),
            '伯母': ('伯母', True),
            '継父': ('继父', True),
            '義母': ('继母', True),
            '継母': ('继母', True),
            '生母': ('亲生母亲', True),
            '実母': ('亲生母亲', True),
            '養母': ('养母', True),
            '乳母': ('保姆', True),
            '従妹': ('堂姐妹', True),
            '養子': ('养子', True),
            '養女': ('养女', True),
            '先生': ('老师', False),
            '学生': ('学生', False),
            '上司': ('上司', True),
            '部下': ('部下', True),
            '同僚': ('同事', True),
            '友達': ('朋友', True),
            '恩師': ('恩师', True),
            '教師': ('老师', False),
            '恩人': ('恩人', True),
            '仲間': ('同伴', True),
            '武将': ('武将', False),
            '相棒': ('搭档', False),
            '少年': ('少年', False),
            '少女': ('少女', False),
            '家族': ('家人', True),
            '隣人': ('邻居', True),
            '仮面': ('面具', False),
            '忍者': ('忍者', False),
            '商人': ('商人', False),
            '王妃': ('王妃', False),
            '巫女': ('巫女', False),
            '司祭': ('祭司', False),
            '賢者': ('贤者', False),
            '使者': ('使者', False),
            '隊長': ('队长', False),
            '首相': ('首相', False),
            '皇子': ('皇子', False),
            '皇女': ('皇女', False),
            '手下': ('手下', False),
            '宿敵': ('宿敌', False),
            '刺客': ('刺客', False),
            '騎士': ('骑士', False),
            '女王': ('女王', False),
            '愛人': ('情人', True),
            '許婚': ('未婚夫/未婚妻', True),
            '仲人': ('媒人', False),
            '捕虜': ('俘虏', False),
            '悪党': ('恶棍', False),
            '悪魔': ('恶魔', False),
            '天使': ('天使', False),
            '妖精': ('精灵', False),
            '亡霊': ('幽灵', False),
            '英雄': ('英雄', False),
            '判事': ('法官', False),
            '探偵': ('侦探', False),
            '司法': ('司法', False),
            '証人': ('证人', False),
            '罪人': ('罪人', False),
            '報酬': ('报酬', False),
            '策士': ('谋士', False),
            '生贄': ('牺牲品', False),
            '親友': ('挚友', True),
            '父': ('父亲', True),
            '母': ('母亲', True),
            '妹': ('妹妹', True),
            '娘': ('女儿', False),
            '姉': ('姐姐', True),
            '姪': ('侄女/侄子', True),
            '兄': ('兄弟', True),
            '孫': ('孙子/孙女', True),
            '妻': ('妻子', True),
            '夫': ('丈夫', True),
            '妾': ('小妾', False),
            '帝': ('皇帝', False),
            '妃': ('妃子', False),
            '君': ('君主', False),
            '侍': ('侍', False),
            '姫': ('公主', False),
            '敵': ('敌人', False),
            '竜': ('龙', False),
        }
        # dict(sorted(ja.items(), key=lambda x: len(x[0]), reverse=True)), ensure_ascii=False, indent=4)
        for index, s in enumerate(summary_s):
            verb = False
            if is_ja:
                for key in ja:
                    if key == re.sub(r"本(?:編|作品?)の", "", s).strip():
                        result.append(ja[key][0])
                        break
                tokens = [get_token_info(token) for token in t.tokenize(s)]
                for i, token in enumerate(tokens):
                    if "動詞" in token[0]:
                        verb = True
                        break
                    if token[1] == "の":
                        before = ""
                        for t_ in tokens[:i][::-1]:
                            if t_[0].startswith("名詞"):
                                before = t_[1] + before
                            else:
                                break
                        if before == "" or before.strip() in ["腹違い"]:
                            continue
                        after = ""
                        for t_ in tokens[i + 1:i + 4]:
                            after += t_[1]
                            if after in ja:
                                ja_ = ja[after]
                                if ja_[1]:
                                    result.append(before + "的" + ja_[0])
                                else:
                                    result.append(ja_[0])
                if verb:
                    break

            else:
                if (
                    "不是" in s
                    or "有" in s
                    or "去" in s
                    or "着" in s
                    or "与" in s
                    or "所以" in s
                    or "为了" in s
                ):
                    continue
                if index == 0:
                    for key in zh:
                        match = re.match(key, s)
                        if match:
                            match_str = match.string[
                                match.regs[0][0]: match.regs[0][1]
                            ]
                            result.append(match_str)
                if "的" in s:
                    to_match = s.split("的")[-1]
                    header = "".join(s.split("的")[:-1]) + "的"
                    if "是" in header:
                        header = header.split("是")[-1]
                    for key, value in zh.items():
                        match = re.match(key, to_match)
                        if match:
                            match_str = match.string[
                                match.regs[0][0]: match.regs[0][1]
                            ]
                            if value:
                                result.append(header + match_str)
                            else:
                                result.append(match_str)

        return list(set(result))

    result = []
    jawiki_texts, w_names = get_jawiki_text(names, subjects)
    if jawiki_texts:
        for jawiki_text in jawiki_texts:
            result.extend(p(jawiki_text))
    if summary is not None:
        result.extend(p(summary))
    return list(set(result)), w_names


logging.info("开始生成结果")
info_match_count = 0  # 匹配到的角色信息数量
tags_match_count = 0  # 匹配到的标签数量
no_zh_count = 0  # 没有中文名的角色数量
no_ja_count = 0
# 遍历contents列表中的每一项
content_total = len(contents)
for content in tqdm(contents, total=content_total):
    # 获取infobox内容
    infobox: str = content["infobox"].replace("\r\n", "\n")
    info = {}
    # 使用正则表达式从infobox中获取简体中文名
    info["name"] = [content["name"]]
    info["zh_name"] = re.findall(r"简体中文名=\s*([^\r\n|]*?)\n?\|", infobox)
    info["zh_name2"] = re.findall(r"\[第二中文名\|([^\]]+)\]", infobox)
    # 使用正则表达式从infobox中获取日文名
    info["ja_name"] = re.findall(r"\[日文名\|([^\]]+)\]", infobox)
    info["ja_name2"] = re.findall(r"\[第二日文名\|([^\]]+)\]", infobox)
    # 使用正则表达式从infobox中获取假名
    info["kana_name"] = re.findall(r"\[纯假名\|([^\]]+)\]", infobox)
    info["kana_name2"] = re.findall(r"\[第二纯假名\|([^\]]+)\]", infobox)
    # 使用正则表达式从infobox中获取英文名
    info["en_name"] = re.findall(r"\[英文名\|([^\]]+)\]", infobox)
    info["en_name2"] = re.findall(r"\[第二英文名\|([^\]]+)\]", infobox)
    info["gender"] = re.findall(r"\|性别=\s*([^\r\n]*?)\n?\|", infobox)
    info["nick_name"] = re.findall(r"\[昵称\|([^\]]+)\]", infobox)
    info["nick_name2"] = re.findall(r"\[第二昵称\|([^\]]+)\]", infobox)
    for key, item in info.items():
        if not item or item[0] == "":
            if key not in ["gender"]:
                info[key] = []
            else:
                info[key] = ""
            continue
        cleared_item = clear(item[0])
        if key not in ["gender"]:
            cleared_item = re.split(r"[／/、]", cleared_item)
        info[key] = cleared_item

    name: list[str] = info["name"]
    zh_name: list[str] = info["zh_name"] + info["zh_name2"]
    ja_name: list[str] = info["ja_name"] + info["ja_name2"]
    kana_name: list[str] = info["kana_name"] + info["kana_name2"]
    en_name: list[str] = info["en_name"] + info["en_name2"]
    gender: str = info["gender"]
    nick_name: list[str] = info["nick_name"] + info["nick_name2"]
    info = None

    subjects = subjects_mapping.get(content["id"], [])

    if not zh_name:
        for n in name:
            if (
                is_from_zh_subject(subjects) or not is_from_ja_subject(subjects)
            ) and is_zh_name(n):
                zh_name.append(n)

    if not ja_name:
        for n in name:
            if (
                (
                    (n not in zh_name or is_from_ja_subject(subjects))
                    and not is_english_with_symbols(n)
                    and is_japanese(n)
                )
                or is_jp_name(n)
            ) and (not is_from_zh_subject(subjects) or include_japanese(n)):
                ja_name.append(n)
            elif not is_english_with_symbols(n) and is_japanese(n):
                maybe_ja_names.append(n)
        if not ja_name and not kana_name:  # noqa: SIM114
            no_ja_count += 1
            # logging.warning(f"{json.dumps(content, ensure_ascii=False, indent=4)}未获取到日文名")
            # continue
        elif not ja_name:
            no_ja_count += 1
            # logging.warning(f"{json.dumps(content, ensure_ascii=False, indent=4)}未获取到日文名, 但有假名")

    if not zh_name:
        for ja_n in [*ja_name, *name]:
            if re.fullmatch(r"[\u4E00-\u9FFF· ]+", ja_n):
                zh_name.append(t2s_converter.convert(ja_n.replace(" ", "")))

    if not zh_name:
        no_zh_count += 1
        # logging.warning(f"{json.dumps(content, ensure_ascii=False, indent=4)}未获取到中文名")
        # continue

    # 匹配VNDB中的角色信息
    names = zh_name + ja_name + en_name + [name.replace(" ", "") for name in ja_name]
    for name in names:
        if name in name_chars_mapping:
            char_ids = name_chars_mapping[name]
            if len(char_ids) == 1:
                info = chars[char_ids[0]].copy()
                info_match_count += 1
                break
            else:
                # 如果匹配到多个角色, 则尝试匹配到有角色的subject

                # 完全匹配
                for char in [chars[char_id] for char_id in char_ids]:
                    subject_list = char.get("subjects", [])
                    for subject in subject_list:
                        if subject in [subject["name"] for subject in subjects] + [
                            subject["zh_name"] for subject in subjects
                        ]:
                            info = char.copy()
                            info_match_count += 1
                            break
                    else:
                        continue
                    break
                else:
                    for char in [chars[char_id] for char_id in char_ids]:
                        subject_list = char.get("subjects", [])
                        for subject1 in subject_list:
                            for subject2 in [
                                subject["name"] for subject in subjects
                            ] + [subject["zh_name"] for subject in subjects]:
                                if subject_name_compare(subject1, subject2):
                                    info = char.copy()
                                    info_match_count += 1
                                    break
                            if info:
                                break
                        else:
                            continue
                        break
                    else:
                        # logging.warning(f"{json.dumps({'bgm': content, 'bgm_subjects': subjects, 'vndb_subjects': {char['id']: char.get('subjects', []) for char in [chars[char_id] for char_id in char_ids]}}, ensure_ascii=False, indent=4)}匹配到多个角色,且无法区分")
                        continue

            break

    tags, ext_names = analyze(names, subjects, content["summary"])

    if info:
        ext_names.append(info["name"])
        info.pop("name")
        if info["latin"] and info["latin"] not in en_name:
            en_name.append(info["latin"])
        info.pop("latin")

    for name in ext_names:
        if name and name not in ja_name and is_japanese(name):
            for i, ja_name_ in enumerate(ja_name):
                if (
                    "・" not in ja_name_
                    and " " not in ja_name_
                    and " " in name
                    and ja_name_ == name.replace(" ", "")
                ):
                    ja_name[i] = name
                    break
            else:
                if re.fullmatch(r"[\u3040-\u309F\u30A0-\u30FF・ ]+", name) and name not in kana_name:
                    kana_name.append(name)
                elif (name not in kana_name
                        and (
                        " " in name
                        or "・" in name
                        or name not in [re.sub(r"[・ ]", "", n_) for n_ in ja_name])):
                    ja_name.append(name)

    if tags:
        tags_match_count += 1

    result = {
        "id": content["id"],
        "zh": list(set(zh_name)),
        "ja": list(set(ja_name)),
        "en": list(set(en_name)),
        "kana": list(set(kana_name)),
        "nick_name": list(set(nick_name)),
        "gender": gender,
        "subjects": subjects,
        "info": info,
        "tags": tags,
    }
    results.append(result)

logging.info(
    f"总角色数量: {content_total}, 处理后的角色数量: {len(results)}匹配到vndb信息的角色数量: {info_match_count} ({info_match_count / len(results) * 100:.2f} %), 有tags的角色数量{tags_match_count} ({tags_match_count / len(results) * 100:.2f} %),没有获取到中文名的角色数量: {no_zh_count}, 没有获取到日文名的角色数量{no_ja_count}")

logging.info("处理人物信息")

with open("maybe_ja_names.txt", "w", encoding="utf-8") as file:
    json.dump(maybe_ja_names, file, ensure_ascii=False, indent=4)

with open("character.jsonl", "w", encoding="utf-8") as file:
    for item in results:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")

with open("character.json", "w", encoding="utf-8") as file:
    json.dump(results, file, ensure_ascii=False, indent=4)
