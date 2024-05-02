# 角色信息数据库

## 数据结构

```json
{
    "id": "bangumi的角色id(可以通过https://bgm.tv/character/角色id 访问角色页面)",
    "zh": ["角色中文名"],
    "jp": ["角色日文名"],
    "en": ["角色英文名"],
    "kana": ["角色日文假名"],
    "gender": "性别",
    "subjects": [
        {"id": "角色出演的作品id",
         "name": "作品名称",
         "zh_name": "作品中文名",
         "type": "作品类型(1:书籍 2: 动画 3:音乐 4: 游戏)",
         "role_type": "角色扮演类型(1: 主要角色 2: 配角 3: 客串)",
        }
    ],
    "info": {
        "id": "VNDB角色id(可以通过https://vndb.org/角色id 访问角色页面)",
        "bloodt": "血型",
        "cup_size": "罩杯",
        "main": "角色主体的id",
        "bust": "胸围",
        "waist": "腰围",
        "s_hip": "臀围",
        "b_month": "生日月份",
        "b_day": "生日日期",
        "height": "身高",
        "weight": "体重",
        "age": "年龄",
        "subjects": ["角色出演的作品名称(vndb)"],
        "traits": {"角色特征"}
    },
    "tags": ["角色标签(从维基百科与bangumi分析得到,可能有错误)"]
}
```

## 数据来源

[bangumi](https://bgm.tv/)  
[VNDB](https://vndb.org/)  
[维基百科](https://ja.wikipedia.org/)  

请遵循数据来源的许可协议：  
[bangumi](https://bgm.tv/about/copyright)  
[VNDB](https://vndb.org/d17#4)  
[维基百科](https://dumps.wikimedia.org/legal.html)  
