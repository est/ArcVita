"""分割史记.md为独立章节文件，按“卷X”切割"""
import json
import pathlib
import re

SRC = pathlib.Path("/home/me/proj/daizhigev20/史藏/正史/史记.md")
OUT = pathlib.Path("data/raw/shiji")
OUT.mkdir(parents=True, exist_ok=True)

# 先秦范围：卷1-卷92（本纪+世家+列传）
PRE_QIN_MAX_CHAPTER = 92

# 先秦人物精选（从史记章节中筛选做事完整的人物）
PRE_QIN_PERSONS = {
    # 本纪
    "卷一": ["黄帝", "尧", "舜"],
    "卷二": ["禹"],
    "卷三": ["汤"],
    "卷四": ["文王", "武王", "周公"],
    "卷五": ["秦穆公"],
    # 世家
    "卷三十一": ["太伯", "季札"],
    "卷三十二": ["齐太公", "管仲"],
    "卷三十三": ["周公旦"],
    "卷三十六": ["勾践"],
    "卷三十七": ["卫武公"],
    "卷三十八": ["微子"],
    "卷三十九": ["晋文公", "重耳"],
    "卷四十二": ["郑庄公"],
    "卷四十三": ["赵武灵王"],
    "卷四十四": ["魏文侯", "信陵君"],
    "卷四十五": ["韩非"],
    "卷四十七": ["孔子"],
    "卷四十八": ["陈涉"],
    # 列传
    "卷六十一": ["伯夷", "叔齐"],
    "卷六十二": ["管仲", "晏婴"],
    "卷六十三": ["老子", "韩非"],
    "卷六十五": ["孙武", "吴起"],
    "卷六十六": ["伍子胥"],
    "卷六十七": ["子贡", "子路"],
    "卷六十八": ["商鞅"],
    "卷六十九": ["苏秦"],
    "卷七十": ["张仪"],
    "卷七十三": ["白起", "王翦"],
    "卷七十四": ["孟子", "荀子"],
    "卷七十五": ["孟尝君"],
    "卷七十六": ["平原君"],
    "卷七十七": ["信陵君"],
    "卷七十八": ["春申君"],
    "卷七十九": ["范雎"],
    "卷八十": ["乐毅", "田单"],
    "卷八十一": ["廉颇", "蔺相如"],
    "卷八十二": ["田单"],
    "卷八十四": ["屈原"],
    "卷八十五": ["吕不韦", "李斯"],
    "卷八十六": ["荆轲"],
    "卷八十八": ["蒙恬"],
}

# Read the full file
text = SRC.read_text(encoding="utf-8")

# Split by "卷X" headers
chapter_pattern = re.compile(r'^(卷[一二三四五六七八九十百千]+)\s+(.+?)\s*$', re.MULTILINE)
chapters = list(chapter_pattern.finditer(text))

manifest = []
for i, m in enumerate(chapters):
    chapter_num = m.group(1)
    chapter_title = m.group(2)
    start = m.end()
    end = chapters[i+1].start() if i+1 < len(chapters) else len(text)
    content = text[start:end].strip()

    # Extract chapter number for sorting
    num_match = re.match(r'卷(\d+)', chapter_num) or re.match(r'卷([\u4e00-\u9fff]+)', chapter_num)
    if num_match:
        try:
            n = int(num_match.group(1))
        except ValueError:
            # Chinese numerals
            cn_map = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
                      '十一':11,'十二':12,'十三':13,'十四':14,'十五':15,'十六':16,'十七':17,
                      '十八':18,'十九':19,'二十':20,'二十一':21,'二十二':22,'二十三':23,
                      '二十四':24,'二十五':25,'二十六':26,'二十七':27,'二十八':28,'二十九':29,
                      '三十':30,'三十一':31,'三十二':32,'三十三':33,'三十四':34,'三十五':35,
                      '三十六':36,'三十七':37,'三十八':38,'三十九':39,'四十':40,'四十一':41,
                      '四十二':42,'四十三':43,'四十四':44,'四十五':45,'四十六':46,'四十七':47,
                      '四十八':48,'四十九':49,'五十':50}
            n = cn_map.get(num_match.group(1), 0)
    else:
        n = 0

    if n > PRE_QIN_MAX_CHAPTER:
        continue

    # Save chapter file
    fname = f"卷{n:03d}_{chapter_title[:20].replace(' ', '_')}.md"
    fpath = OUT / fname
    fpath.write_text(f"---\ntitle: 史记 {chapter_num} {chapter_title}\nchapter: {n}\ntype: shiji\n---\n\n{content}\n", encoding="utf-8")

    # Check if it's a pre-Qin chapter worth extracting
    persons = PRE_QIN_PERSONS.get(chapter_num, [])
    is_pre_qin = n <= 92 and any(k in chapter_title for k in ["本纪", "世家", "列传"])

    manifest.append({
        "file": str(fpath),
        "chapter": chapter_num,
        "title": chapter_title,
        "chapter_num": n,
        "type": "本纪" if "本纪" in chapter_title else "世家" if "世家" in chapter_title else "列传",
        "persons_hint": persons,
        "is_pre_qin": is_pre_qin and n <= 92,
        "size": len(content),
    })

# Write manifest
manifest_path = OUT / "manifest.jsonl"
with manifest_path.open("w", encoding="utf-8") as f:
    for item in manifest:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

# Stats
pre_qin = [m for m in manifest if m["is_pre_qin"]]
print(f"总章节: {len(manifest)}, 先秦章节: {len(pre_qin)}")
for m in pre_qin[:10]:
    print(f"  {m['chapter']} {m['title'][:30]} | {m['persons_hint']}")
print("...")
print(f"先秦人物候选: {sum(len(m['persons_hint']) for m in pre_qin)} 人")
