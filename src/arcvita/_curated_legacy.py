from __future__ import annotations

from arcvita.models import Endeavor

OFFLINE: dict[str, dict] = {
    "Q4604": {"name_zh": "孔子", "name_en": "Confucius", "birth_date": "-551-09-28", "death_date": "-479-04-11", "birth_place": "曲阜", "occupations": ["思想家", "教育家"], "era": "春秋", "archetype": "奠基型", "dilemmas": ["怀才不遇", "被误解"], "summary_zh": "春秋时期思想家、教育家，儒家学派创始人，以仁与礼为核心，整理六经、讲学授徒。", "summary_first_person": "我周游列国而不得用，归而修诗书——若道不行，便让它在后世行。", "lesson": "在不被采纳时，转而做可传承的体系。"},
    "Q162427": {"name_zh": "秦始皇", "name_en": "Qin Shi Huang", "birth_date": "-259-02-18", "death_date": "-210-07-10", "birth_place": "邯郸", "occupations": ["皇帝"], "era": "战国末/秦", "archetype": "统合型", "dilemmas": ["过度扩张"], "summary_zh": "首位完成华夏大一统的君主，统一度量衡与文字，北击匈奴、南征百越，亦以严刑峻法埋下速亡之因。", "summary_first_person": "我以铁与法把六国压成一块版图，却忘了版图需要人心来粘合。", "lesson": "以速度完成的统一，若无制度与人心的消化，终会反噬。"},
    "Q179544": {"name_zh": "诸葛亮", "name_en": "Zhuge Liang", "birth_date": "181-01-01", "death_date": "234-10-08", "birth_place": "阳都", "occupations": ["政治家", "军事家"], "era": "三国", "archetype": "统筹型", "dilemmas": ["从零开始", "被误解", "至暗时刻"], "summary_zh": "蜀汉丞相，隆中对策定三分，治蜀以严明，六出祁山未竟而殁。", "summary_first_person": "我知天时不在蜀，却仍以人事尽天命——鞠躬尽瘁，死而后已。", "lesson": "明知胜算不大仍做最周密的准备，是另一种勇敢。"},
    "Q7074": {"name_zh": "李白", "name_en": "Li Bai", "birth_date": "701-01-01", "death_date": "762-01-01", "birth_place": "碎叶", "occupations": ["诗人"], "era": "唐", "archetype": "表现型", "dilemmas": ["怀才不遇", "被流放"], "summary_zh": "唐代浪漫主义诗人，诗风豪放飘逸，与杜甫并称李杜，一生漂泊而诗不辍。", "summary_first_person": "我欲乘风归去，又在人间把酒——诗是我对无常的回击。", "lesson": "把漂泊活成风格，也是一种做事。"},
    "Q316452": {"name_zh": "王阳明", "name_en": "Wang Yangming", "birth_date": "1472-10-31", "death_date": "1529-01-09", "birth_place": "余姚", "occupations": ["思想家", "军事家"], "era": "明", "archetype": "知行型", "dilemmas": ["被贬", "被流放", "转型阵痛"], "summary_zh": "心学集大成者，龙场悟道，知行合一；平宁王之乱，立德立功立言。", "summary_first_person": "我在龙场的瘴气里悟到：心外无物，破山中贼易，破心中贼难。", "lesson": "把内修与实干合一，学问才不悬空。"},
    "Q193533": {"name_zh": "张衡", "name_en": "Zhang Heng", "birth_date": "78-01-01", "death_date": "139-01-01", "birth_place": "南阳", "occupations": ["科学家", "文学家"], "era": "东汉", "archetype": "格物型", "dilemmas": ["技术瓶颈"], "summary_zh": "东汉科学家、文学家，发明地动仪、浑天仪，兼通历算与辞赋。", "summary_first_person": "我在简陋的铜壶里听见大地的颤动，想用器物让天人可测。", "lesson": "把好奇心做成可用的器物，影响才长久。"},
    "Q133847": {"name_zh": "郑和", "name_en": "Zheng He", "birth_date": "1371-01-01", "death_date": "1433-01-01", "birth_place": "昆明", "occupations": ["航海家", "外交家"], "era": "明", "archetype": "开拓型", "dilemmas": ["从零开始"], "summary_zh": "明代航海家，七下西洋，船队远至非洲东岸，开海上丝路先声。", "summary_first_person": "我以船为笔，在无边的海上写下朝贡与贸易的两行字。", "lesson": "以开放换来的秩序，比以封闭求得的安全更广阔。"},
    "Q334053": {"name_zh": "林则徐", "name_en": "Lin Zexu", "birth_date": "1785-08-30", "death_date": "1850-11-22", "birth_place": "福州", "occupations": ["政治家"], "era": "清", "archetype": "担当型", "dilemmas": ["被贬", "被误解"], "summary_zh": "清末政治家，虎门销烟，睁眼看世界第一人，力主禁烟抗英。", "summary_first_person": "我在虎门点起的那把火，烧的是鸦片，也是国人的沉睡。", "lesson": "在众醉时保持清醒，需要付出代价也必须去做。"},
    "Q23114": {"name_zh": "鲁迅", "name_en": "Lu Xun", "birth_date": "1881-09-25", "death_date": "1936-10-19", "birth_place": "绍兴", "occupations": ["作家", "思想家"], "era": "民国", "archetype": "批判型", "dilemmas": ["被误解", "转型阵痛"], "summary_zh": "现代文学奠基人，以笔为刀，解剖国民性；弃医从文，欲医人心。", "summary_first_person": "我在铁屋子里呐喊，明知未必能醒，也不能沉默。", "lesson": "在沉默的时代，说真话本身就是行动。"},
    "Q184080": {"name_zh": "钱学森", "name_en": "Qian Xuesen", "birth_date": "1911-12-11", "death_date": "2009-10-31", "birth_place": "杭州", "occupations": ["科学家"], "era": "现代", "archetype": "攻关型", "dilemmas": ["被流放", "从零开始", "技术瓶颈"], "summary_zh": "空气动力学家，两弹一星元勋，历经羁留而归，奠定中国航天事业。", "summary_first_person": "我在异国的实验室里计算归期——科学无国界，但科学家有祖国。", "lesson": "把个人专长与家国需要对齐，价值会被放大百倍。"},
    "Q37230": {"name_zh": "邓小平", "name_en": "Deng Xiaoping", "birth_date": "1904-08-22", "death_date": "1997-02-19", "birth_place": "广安", "occupations": ["政治家"], "era": "现代", "archetype": "转型型", "dilemmas": ["被贬", "转型阵痛", "至暗时刻"], "summary_zh": "改革开放总设计师，三起三落而不改其志，以务实推动中国现代化。", "summary_first_person": "我三次跌倒，三次爬起——不争论，先让一部分人试试看。", "lesson": "在争议中用可验证的小步快跑换取大方向的正确。"},
    "Q334642": {"name_zh": "袁隆平", "name_en": "Yuan Longping", "birth_date": "1930-09-07", "death_date": "2021-05-22", "birth_place": "北京", "occupations": ["科学家"], "era": "现代", "archetype": "深耕型", "dilemmas": ["技术瓶颈", "从零开始"], "summary_zh": "杂交水稻之父，毕生在稻田里解决吃饭问题，让中国人把饭碗端在自己手里。", "summary_first_person": "我愿做一粒种子，在田垄间寻找让更多人吃饱的答案。", "lesson": "在一个问题上做到极致，就是对世界最大的善意。"},
    "Q913": {"name_zh": "苏格拉底", "name_en": "Socrates", "birth_date": "-470-01-01", "death_date": "-399-01-01", "birth_place": "雅典", "occupations": ["哲学家"], "era": "古希腊", "archetype": "诘问型", "dilemmas": ["被误解"], "summary_zh": "古希腊哲学奠基人，以诘问法探求真知，因坚持信念而饮鸩就义。", "summary_first_person": "我自知无知——在不断的追问里，人才能靠近真实的自己。", "lesson": "敢于质疑常识，是走出迷茫的第一步。"},
    "Q1048": {"name_zh": "凯撒", "name_en": "Julius Caesar", "birth_date": "-100-07-12", "death_date": "-44-03-15", "birth_place": "罗马", "occupations": ["政治家", "军事家"], "era": "古罗马", "archetype": "决断型", "dilemmas": ["众叛亲离"], "summary_zh": "罗马统帅与独裁官，征服高卢，跨过卢比孔河，终遇刺于元老院。", "summary_first_person": "我跨过卢比孔河时知道已无退路——骰子已经掷下。", "lesson": "跨过关键的卢比孔河前，必须想清退路已断的代价。"},
    "Q720": {"name_zh": "成吉思汗", "name_en": "Genghis Khan", "birth_date": "1162-01-01", "death_date": "1227-08-18", "birth_place": "斡难河", "occupations": ["政治家", "军事家"], "era": "蒙古帝国", "archetype": "组织型", "dilemmas": ["从零开始", "过度扩张"], "summary_zh": "蒙古帝国奠基者，以骑射与组织力统一草原，西征欧亚。", "summary_first_person": "我从被逐的少年到万户之主，靠的是让分散的力量拧成一股。", "lesson": "把乌合之众组织起来，比单打独斗走得更远。"},
    "Q762": {"name_zh": "达·芬奇", "name_en": "Leonardo da Vinci", "birth_date": "1452-04-15", "death_date": "1519-05-02", "birth_place": "芬奇", "occupations": ["艺术家", "科学家"], "era": "文艺复兴", "archetype": "通才型", "dilemmas": ["怀才不遇"], "summary_zh": "文艺复兴全才，画《蒙娜丽莎》与《最后的晚餐》，手稿遍及解剖、飞行与水利。", "summary_first_person": "我在画布与解剖台之间往返——想画得像，先要看得真。", "lesson": "跨界不是分心，而是用一领域的深度照亮另一领域。"},
    "Q935": {"name_zh": "牛顿", "name_en": "Isaac Newton", "birth_date": "1643-01-04", "death_date": "1727-03-31", "birth_place": "伍尔斯索普", "occupations": ["科学家"], "era": "17世纪", "archetype": "体系型", "dilemmas": ["技术瓶颈", "被误解"], "summary_zh": "英国物理学家，奠定经典力学与光学，著《自然哲学的数学原理》。", "summary_first_person": "我站在巨人的肩上——把零散的直觉压成可计算的定律。", "lesson": "长期沉淀后的一次体系化交付，能改变时代坐标。"},
    "Q517": {"name_zh": "拿破仑", "name_en": "Napoleon", "birth_date": "1769-08-15", "death_date": "1821-05-05", "birth_place": "阿雅克肖", "occupations": ["政治家", "军事家"], "era": "19世纪初", "archetype": "扩张型", "dilemmas": ["过度扩张", "众叛亲离"], "summary_zh": "法国皇帝，以军事天才与《民法典》闻名，远征俄国后帝国崩溃。", "summary_first_person": "我在意大利的急行军里学会用意志改写地图，却在俄国的寒冬里学会敬畏边界。", "lesson": "早期胜利最易让人高估边界，过度扩张会反噬。"},
    "Q7186": {"name_zh": "居里夫人", "name_en": "Marie Curie", "birth_date": "1867-11-07", "death_date": "1934-07-04", "birth_place": "华沙", "occupations": ["科学家"], "era": "19-20世纪", "archetype": "专精型", "dilemmas": ["技术瓶颈", "被误解"], "summary_zh": "波兰裔法国物理学家，两获诺贝尔奖，发现镭与钋，开放射性研究先河。", "summary_first_person": "我在漏风的棚屋里提炼镭——微光虽弱，却足以照见一个新世界。", "lesson": "在艰苦的条件下坚持精确，是对未来的投资。"},
    "Q937": {"name_zh": "爱因斯坦", "name_en": "Albert Einstein", "birth_date": "1879-03-14", "death_date": "1955-04-18", "birth_place": "乌尔姆", "occupations": ["科学家"], "era": "20世纪", "archetype": "思想型", "dilemmas": ["被误解", "被流放", "技术瓶颈"], "summary_zh": "德裔物理学家，提出相对论，1905奇迹年改写时空观念。", "summary_first_person": "我在专利局的桌前追光——想让时间与空间从背景变成主角。", "lesson": "给自己一段不被打扰的深思期，答案会在尽头等你。"},
    "Q1001": {"name_zh": "甘地", "name_en": "Mahatma Gandhi", "birth_date": "1869-10-02", "death_date": "1948-01-30", "birth_place": "波尔班达尔", "occupations": ["政治家"], "era": "20世纪", "archetype": "感召型", "dilemmas": ["至暗时刻"], "summary_zh": "印度民族运动领袖，以非暴力不合作争取独立，苦行而坚定。", "summary_first_person": "我以纺车与绝食对抗帝国——柔软的坚持比坚硬的对抗更难被摧毁。", "lesson": "以非暴力的自律去对抗庞大的不公，需要更大的勇气。"},
    "Q8016": {"name_zh": "丘吉尔", "name_en": "Winston Churchill", "birth_date": "1874-11-30", "death_date": "1965-01-24", "birth_place": "伦敦", "occupations": ["政治家", "作家"], "era": "20世纪", "archetype": "领导型", "dilemmas": ["至暗时刻", "被误解"], "summary_zh": "英国首相，二战中以演讲与决断领导英国渡过至暗时刻，获诺贝尔文学奖。", "summary_first_person": "我在伦敦的废墟里对议会说：我们将在海滩上战斗——语言成了武器。", "lesson": "在至暗时刻，清晰的叙事本身就是领导力。"},
    "Q8023": {"name_zh": "曼德拉", "name_en": "Nelson Mandela", "birth_date": "1918-07-18", "death_date": "2013-12-05", "birth_place": "库努", "occupations": ["政治家"], "era": "20世纪", "archetype": "和解型", "dilemmas": ["被流放", "至暗时刻"], "summary_zh": "南非反种族隔离领袖，27年狱中不改其志，出狱后以和解而非复仇建国。", "summary_first_person": "我在罗本岛的石场里学会：仇恨是自己的囚笼，和解才是自由。", "lesson": "最长的坚持需要最柔软的心去收尾。"},
    "Q19837": {"name_zh": "乔布斯", "name_en": "Steve Jobs", "birth_date": "1955-02-24", "death_date": "2011-10-05", "birth_place": "旧金山", "occupations": ["企业家"], "era": "当代", "archetype": "产品型", "dilemmas": ["被流放", "从零开始", "转型阵痛"], "summary_zh": "苹果公司创始人，以产品与设计重塑个人计算与移动时代，历经被逐而回归。", "summary_first_person": "我被自己创立的公司赶走，却在荒野里找回了对产品的直觉。", "lesson": "被逐是重生的机会，专注比聪明更稀缺。"},
    "Q352": {"name_zh": "希特勒", "name_en": "Adolf Hitler", "birth_date": "1889-04-20", "death_date": "1945-04-30", "birth_place": "布劳瑙", "occupations": ["政治家"], "era": "20世纪", "archetype": "动员型", "dilemmas": ["众叛亲离", "过度扩张"], "summary_zh": "德国纳粹党首，发动二战与大屠杀，极端教训人物。", "summary_first_person": "（教训人物，不作第一视角美化）以仇恨与谎言动员的权力，终将以毁灭自证其错。", "lesson": "以仇恨为燃料的动员，短期有效、长期必毁。"},
}

ENDEAVORS_OFFLINE: dict[str, list[dict]] = {
    "Q4604": [
        {"title_zh": "周游列国与讲学", "domain": "文化/政治", "start_date": "-497", "end_date": "-484", "places": ["鲁", "卫", "陈", "蔡"], "description_zh": "我带着弟子在诸侯间辗转，屡遭冷遇却不改其志；在陈蔡之间断粮，仍弦歌不辍——道不行，吾辈当以身示范。", "outcome": "弟子三千，儒家雏形形成", "lesson": "在逆境中保持一致的言行，比一时的采纳更长久。"},
        {"title_zh": "整理六经", "domain": "文化", "start_date": "-484", "end_date": "-479", "places": ["鲁"], "description_zh": "归鲁后不再求仕，转而删诗书、定礼乐；我想为后世留下一套可依的文脉，让人在迷茫时有章可循。", "outcome": "六经成型", "lesson": "做成一套可传承的体系，胜过做成一件事。"},
    ],
    "Q162427": [
        {"title_zh": "统一六国", "domain": "军事/政治", "start_date": "-230", "end_date": "-221", "places": ["咸阳", "邯郸", "临淄"], "description_zh": "我以远交近攻与郡县制把六国一一点名，地图第一次被压成一块。", "outcome": "建立秦朝，大一统", "lesson": "统一需要制度消化，否则速度即隐患。"},
        {"title_zh": "制度统一与巡行", "domain": "政治", "start_date": "-221", "end_date": "-210", "places": ["咸阳", "泰山", "会稽", "沙丘"], "description_zh": "书同文、车同轨，我在五次巡行中把标准压进每一寸土地。", "outcome": "度量衡文字货币统一", "lesson": "标准化是杠杆，过度则是负担。"},
    ],
    "Q179544": [
        {"title_zh": "隆中对策与入蜀", "domain": "政治", "start_date": "207", "end_date": "214", "places": ["隆中", "荆州", "成都"], "description_zh": "我在茅庐里为刘备画出三分天下的草图，随后入蜀定成都，让偏安之地有了可守的根基。", "outcome": "三分格局初定，蜀汉立国", "lesson": "一张可执行的路线图，胜过十句空洞的口号。", "phases": [{"name": "酝酿", "start_date": "207", "end_date": "208", "place": "隆中", "highlight": "三顾茅庐 — 成语诞生"}, {"name": "破局", "start_date": "208", "end_date": "208", "place": "赤壁", "highlight": "赤壁之战 — 以少胜多名场面"}, {"name": "收束", "start_date": "212", "end_date": "214", "place": "成都", "highlight": "入蜀定成都 — 立足点建成"}]},
        {"title_zh": "治蜀与北伐", "domain": "政治/军事", "start_date": "223", "end_date": "234", "places": ["成都", "汉中", "祁山", "五丈原"], "description_zh": "白帝托孤后我以严明治蜀，六出祁山，明知国力不及仍以人事尽天命，五丈原的秋风里燃尽最后一盏灯。", "outcome": "蜀汉国力稳固，北伐未竟", "lesson": "竭尽人事是对天命最体面的回应。", "phases": [{"name": "治蜀", "start_date": "223", "end_date": "227", "place": "成都", "highlight": "《出师表》— 名篇诞生 227"}, {"name": "北伐", "start_date": "228", "end_date": "234", "place": "祁山", "highlight": "六出祁山 — 周期性攻关"}, {"name": "收束", "start_date": "234", "end_date": "234", "place": "五丈原", "highlight": "星落五丈原 — 悲壮终局"}]},
    ],
    "Q7074": [
        {"title_zh": "漫游与求仕", "domain": "文化", "start_date": "725", "end_date": "744", "places": ["长安", "洛阳", "黄河"], "description_zh": "我仗剑游历，欲以诗与才华求仕，却在长安的酒肆里看清权门的冷暖。", "outcome": "诗名大盛，供奉翰林", "lesson": "才华需要舞台，但不必依附单一舞台。"},
        {"title_zh": "翰林与放逐", "domain": "文化", "start_date": "744", "end_date": "762", "places": ["长安", "梁园", "夜郎"], "description_zh": "翰林岁月短暂，赐金放还后我更自由也更漂泊，诗在流放路上反而更辽阔。", "outcome": "《蜀道难》《将进酒》等名篇", "lesson": "失去体制庇护后，创作反而回归本体。", "phases": [{"name": "翰林", "start_date": "744", "end_date": "744", "place": "长安", "highlight": "《蜀道难》— 代表作"}, {"name": "放逐", "start_date": "744", "end_date": "762", "place": "夜郎", "highlight": "《将进酒》— 名篇诞生"}]},
    ],
    "Q316452": [
        {"title_zh": "龙场悟道", "domain": "思想", "start_date": "1508", "end_date": "1510", "places": ["贵阳", "龙场"], "description_zh": "被贬龙场，瘴气与孤独中我悟到心即理，知行合一的种子在此萌发。", "outcome": "心学雏形形成", "lesson": "低谷是思想成型的最好土壤。", "phases": [{"name": "贬谪", "start_date": "1508", "end_date": "1508", "place": "龙场", "highlight": "谪居龙场 — 至暗起点"}, {"name": "悟道", "start_date": "1508", "end_date": "1510", "place": "龙场", "highlight": "龙场悟道 — 知行合一提出"}]},
        {"title_zh": "平宸濠与讲学", "domain": "军事/文化", "start_date": "1519", "end_date": "1528", "places": ["南昌", "绍兴"], "description_zh": "以极快速度平定宁王之乱，随后在绍兴、赣州讲学，让心学从战场的决断流向日常的修为。", "outcome": "立德立功立言", "lesson": "把战场的决断力迁移到学问，知行才合一。", "phases": [{"name": "平叛", "start_date": "1519", "end_date": "1519", "place": "南昌", "highlight": "三十五日平宸濠 — 战争名场面"}, {"name": "讲学", "start_date": "1521", "end_date": "1528", "place": "绍兴", "highlight": "《传习录》 — 代表作"}]},
    ],
    "Q193533": [
        {"title_zh": "浑天仪与地动仪", "domain": "科学", "start_date": "117", "end_date": "132", "places": ["洛阳"], "description_zh": "我在洛阳的观象台与作坊间往返，试图让天体的运行与大地的颤动可在器物上被看见、被记录。", "outcome": "地动仪、浑天仪问世", "lesson": "把观测做成仪器，知识才可传递。", "phases": [{"name": "研制", "start_date": "117", "end_date": "125", "place": "洛阳", "highlight": "浑天仪成"}, {"name": "验证", "start_date": "132", "end_date": "132", "place": "洛阳", "highlight": "地动仪验震 — 发明名场面"}]},
    ],
    "Q133847": [
        {"title_zh": "七下西洋", "domain": "航海/外交", "start_date": "1405", "end_date": "1433", "places": ["南京", "马六甲", "古里", "非洲东岸"], "description_zh": "我率庞大船队七度远航，以朝贡与贸易织就海上网络，也让世界第一次如此具体地出现在中原眼前。", "outcome": "海上丝路鼎盛，万国来朝", "lesson": "以开放求得的连接，比封闭求得的安全更持久。", "phases": [{"name": "筹备", "start_date": "1405", "end_date": "1405", "place": "南京", "highlight": "首下西洋 1405 — 启航名场面"}, {"name": "远航", "start_date": "1405", "end_date": "1430", "place": "马六甲", "highlight": "三下西洋至古里 — 周期高峰"}, {"name": "终章", "start_date": "1430", "end_date": "1433", "place": "非洲东岸", "highlight": "卒于古里 — 以身殉航"}]},
    ],
    "Q334053": [
        {"title_zh": "虎门销烟与抗英", "domain": "政治", "start_date": "1839", "end_date": "1842", "places": ["广州", "虎门"], "description_zh": "我在虎门点火销烟，以强硬对抗鸦片贸易；战争失利后被贬新疆，仍修水利、思变法。", "outcome": "虎门销烟，睁眼看世界", "lesson": "在众醉时清醒，需要承担被误解的代价。", "phases": [{"name": "销烟", "start_date": "1839", "end_date": "1839", "place": "虎门", "highlight": "虎门销烟 1839-06-03 — 名场面"}, {"name": "抗英", "start_date": "1840", "end_date": "1842", "place": "广州", "highlight": "被贬伊犁 — 至暗起点"}, {"name": "再起", "start_date": "1842", "end_date": "1850", "place": "新疆", "highlight": "修坎儿井 — 实干收束"}]},
    ],
    "Q23114": [
        {"title_zh": "弃医从文与呐喊", "domain": "文化", "start_date": "1906", "end_date": "1925", "places": ["东京", "绍兴", "北京"], "description_zh": "我在仙台学医时看见国人的麻木，转而以笔为刀；在北京的铁屋子里，我选择呐喊。", "outcome": "《狂人日记》《呐喊》奠定现代文学", "lesson": "说真话需要勇气，不说则无人会说。", "phases": [{"name": "抉择", "start_date": "1906", "end_date": "1906", "place": "东京", "highlight": "弃医从文 — 人生转折名场面"}, {"name": "呐喊", "start_date": "1918", "end_date": "1923", "place": "北京", "highlight": "《狂人日记》1918 — 代表作"}]},
        {"title_zh": "左联与晚年论战", "domain": "文化", "start_date": "1930", "end_date": "1936", "places": ["上海"], "description_zh": "在上海的论战与苦闷中，我以杂文回应时代的每一次颤动，直至燃尽。", "outcome": "杂文成为时代镜子", "lesson": "在高压下保持独立的表达，是知识分子的本分。"},
    ],
    "Q184080": [
        {"title_zh": "归国与两弹一星", "domain": "科学", "start_date": "1955", "end_date": "1970", "places": ["洛杉矶", "北京", "酒泉"], "description_zh": "历经五年羁留回到祖国，我把空气动力学的计算压进导弹与火箭的图纸，让中国有了可仰望的星空。", "outcome": "两弹一星奠基", "lesson": "把个人专长与家国需要对齐，价值被放大百倍。", "phases": [{"name": "羁留", "start_date": "1950", "end_date": "1955", "place": "洛杉矶", "highlight": "被羁留 — 至暗起点"}, {"name": "归国", "start_date": "1955", "end_date": "1956", "place": "北京", "highlight": "归国 1955 — 转折名场面"}, {"name": "攻关", "start_date": "1956", "end_date": "1970", "place": "酒泉", "highlight": "东方红一号 1970-04-24 — 代表作/发明"}]},
    ],
    "Q37230": [
        {"title_zh": "改革开放", "domain": "政治", "start_date": "1978", "end_date": "1992", "places": ["北京", "深圳", "上海"], "description_zh": "我以小步快跑的方式让一部分地区先试起来，用可验证的成果去说服更大的体制。", "outcome": "中国现代化起飞，深圳特区南巡定调", "lesson": "在争议中用试点换共识，比空谈方向更有效。", "phases": [{"name": "破局", "start_date": "1978", "end_date": "1980", "place": "北京", "highlight": "十一届三中全会 1978-12-18 — 决策名场面"}, {"name": "试点", "start_date": "1980", "end_date": "1984", "place": "深圳", "highlight": "设深圳特区 1980 — 制度发明"}, {"name": "定调", "start_date": "1992", "end_date": "1992", "place": "深圳", "highlight": "南方谈话 1992 — 演讲名场面"}]},
    ],
    "Q334642": [
        {"title_zh": "杂交水稻攻关", "domain": "科学", "start_date": "1964", "end_date": "2000", "places": ["长沙", "三亚", "海南"], "description_zh": "我在稻田里寻找让水稻也拥有杂交优势的可能，海南的烈日与长沙的试验田是我的实验室。", "outcome": "杂交水稻大面积推广", "lesson": "在一个问题上做到极致，就是对世界最大的善意。", "phases": [{"name": "发现", "start_date": "1964", "end_date": "1964", "place": "长沙", "highlight": "发现不育株 1964 — 起点名场面"}, {"name": "失败与坚持", "start_date": "1968", "end_date": "1970", "place": "三亚", "highlight": "材料被毁仍坚持 — 至暗时刻"}, {"name": "突破", "start_date": "1973", "end_date": "1973", "place": "长沙", "highlight": "三系配套 1973 — 发明名场面"}, {"name": "推广", "start_date": "1976", "end_date": "2000", "place": "海南", "highlight": "大面积推广 — 成事儿收束"}]},
    ],
    "Q913": [{"title_zh": "街头诘问与审判", "domain": "思想", "start_date": "-430", "end_date": "-399", "places": ["雅典"], "description_zh": "我在集市与青年对话，以不断的诘问剥开自以为是的确定性；审判席上我选择饮鸩而非逃离。", "outcome": "奠定西方哲学方法", "lesson": "敢于承认无知，是走出迷茫的第一步。"}],
    "Q1048": [{"title_zh": "高卢战争与卢比孔河", "domain": "军事/政治", "start_date": "-58", "end_date": "-44", "places": ["高卢", "罗马", "卢比孔河"], "description_zh": "我以八年征服高卢，随后跨过卢比孔河——知道已无退路，骰子已经掷下。", "outcome": "成为罗马独裁官", "lesson": "关键跨越前，必须想清不可逆的代价。", "phases": [{"name": "征服", "start_date": "-58", "end_date": "-50", "place": "高卢", "highlight": "八年高卢战争 — 周期攻关"}, {"name": "抉择", "start_date": "-49", "end_date": "-49", "place": "卢比孔河", "highlight": "跨过卢比孔河 — 决策名场面，成语/典故诞生"}, {"name": "收束", "start_date": "-44", "end_date": "-44", "place": "罗马", "highlight": "遇刺 — 悲壮终局"}]}],
    "Q720": [{"title_zh": "统一蒙古与西征", "domain": "军事/政治", "start_date": "1206", "end_date": "1227", "places": ["斡难河", "撒马尔罕", "欧亚草原"], "description_zh": "我把分散的部落拧成一股，以十进位与驿站把草原组织成可远征的机器，西征的马蹄踏至欧亚腹地。", "outcome": "蒙古帝国建立，欧亚交通打通", "lesson": "组织力比个人勇武更能改变版图。"}],
    "Q762": [{"title_zh": "佛罗伦萨与米兰创作", "domain": "艺术/科学", "start_date": "1482", "end_date": "1519", "places": ["佛罗伦萨", "米兰", "法国昂布瓦斯"], "description_zh": "我在画室与解剖台之间往返，想以精确的观察让艺术与科学在同一张纸上相遇。", "outcome": "《最后的晚餐》《蒙娜丽莎》，大量手稿", "lesson": "跨界不是分心，是用一领域的深度照亮另一领域。", "phases": [{"name": "佛罗伦萨", "start_date": "1482", "end_date": "1499", "place": "佛罗伦萨", "highlight": "《最后的晚餐》1495-1498 — 代表作"}, {"name": "米兰与漂泊", "start_date": "1503", "end_date": "1519", "place": "昂布瓦斯", "highlight": "《蒙娜丽莎》1503起 — 代表作"}]}],
    "Q935": [{"title_zh": "光学与颜色研究", "domain": "科学", "start_date": "1666", "end_date": "1672", "places": ["剑桥", "伦敦"], "description_zh": "躲避瘟疫回到伍尔斯索普，却在棱镜前看见白光的秘密；我把光拆开又合上，论文投向皇家学会，争议随之而来。", "outcome": "光学论文奠定近代光学基础", "lesson": "在孤独的实验里坚持可重复的证据，比雄辩更有力。"}, {"title_zh": "万有引力与天体力学", "domain": "科学", "start_date": "1684", "end_date": "1687", "places": ["剑桥", "伦敦"], "description_zh": "从苹果的下落到月球的轨道，我试图让同一条定律贯穿天地；在与胡克的争执中学会用数学把直觉钉牢。", "outcome": "提出万有引力定律，统一天上地下力学", "lesson": "把不同尺度纳入同一原理，是最值得的做事方式。"}],
    "Q517": [{"title_zh": "意大利战役与崛起", "domain": "军事/政治", "start_date": "1796", "end_date": "1797", "places": ["意大利", "巴黎"], "description_zh": "以少胜多的急行军与心理战让我一战成名，也让我第一次相信意志可以改写地图。", "outcome": "控制北意大利，声望飙升", "lesson": "早期的胜利最容易让人高估边界。"}, {"title_zh": "称帝与法典", "domain": "政治", "start_date": "1804", "end_date": "1807", "places": ["巴黎"], "description_zh": "我把革命的成果装进《民法典》，试图用法律固定住动荡的法国。", "outcome": "《拿破仑法典》颁布", "lesson": "制度化的成果比个人光环走得更远。"}, {"title_zh": "远征俄国与衰落", "domain": "军事", "start_date": "1812", "end_date": "1815", "places": ["莫斯科", "莱比锡", "滑铁卢"], "description_zh": "莫斯科的大火与寒冬把补给线拉断，莱比锡与滑铁卢把同一个错误重复了两遍。", "outcome": "帝国崩溃，流放圣赫勒拿", "lesson": "过度扩张会让每次胜利都成为下次失败的预付款。"}],
    "Q7186": [{"title_zh": "镭的提炼与两获诺奖", "domain": "科学", "start_date": "1898", "end_date": "1911", "places": ["巴黎"], "description_zh": "我在漏风的棚屋里与皮埃尔提炼沥青铀矿，微弱的荧光照见一个新世界；两次诺奖背后是数吨矿石与无数个夜晚。", "outcome": "发现镭与钋，两获诺贝尔奖", "lesson": "在艰苦的条件下坚持精确，是对未来的投资。", "phases": [{"name": "发现", "start_date": "1898", "end_date": "1898", "place": "巴黎", "highlight": "发现镭与钋 1898 — 发明名场面"}, {"name": "首奖", "start_date": "1903", "end_date": "1903", "place": "斯德哥尔摩", "highlight": "首获诺奖 1903 — 奖项名场面"}, {"name": "再奖", "start_date": "1911", "end_date": "1911", "place": "斯德哥尔摩", "highlight": "再获诺奖 1911 — 代表作收束"}]}],
    "Q937": [{"title_zh": "奇迹年与相对论", "domain": "科学", "start_date": "1905", "end_date": "1915", "places": ["伯尔尼", "柏林"], "description_zh": "专利局的桌前，我在思想实验里追光；从狭义到广义，十年间把时空从背景变成了主角。", "outcome": "狭义与广义相对论", "lesson": "给自己一段不被打扰的深思期，答案会在尽头等你。", "phases": [{"name": "奇迹年", "start_date": "1905", "end_date": "1905", "place": "伯尔尼", "highlight": "奇迹年四篇论文 1905 — 代表作"}, {"name": "广义", "start_date": "1915", "end_date": "1915", "place": "柏林", "highlight": "广义相对论 1915 — 代表作"}, {"name": "流亡", "start_date": "1933", "end_date": "1933", "place": "普林斯顿", "highlight": "流亡美国 — 至暗转折"}]}],
    "Q1001": [{"title_zh": "非暴力不合作", "domain": "政治", "start_date": "1920", "end_date": "1947", "places": ["孟买", "德班", "德里"], "description_zh": "我以纺车、绝食与长途跋涉对抗帝国，用自律的非暴力去对抗庞大的不公。", "outcome": "印度独立运动走向成功", "lesson": "柔软的坚持比坚硬的对抗更难被摧毁。", "phases": [{"name": "南非淬炼", "start_date": "1893", "end_date": "1915", "place": "德班", "highlight": "南非抗争 — 方法成型"}, {"name": "食盐进军", "start_date": "1930", "end_date": "1930", "place": "古吉拉特", "highlight": "食盐进军 1930-03-12 — 名场面"}, {"name": "独立", "start_date": "1947", "end_date": "1947", "place": "德里", "highlight": "印度独立 1947 — 收束"}]}],
    "Q8016": [{"title_zh": "二战领导与演讲", "domain": "政治/军事", "start_date": "1940", "end_date": "1945", "places": ["伦敦"], "description_zh": "敦刻尔克之后我对议会说我们将在海滩上战斗；在伦敦的废墟里，语言成了武器。", "outcome": "领导英国渡过二战，获诺贝尔文学奖", "lesson": "在至暗时刻，清晰的叙事本身就是领导力。", "phases": [{"name": "就任", "start_date": "1940", "end_date": "1940", "place": "伦敦", "highlight": "出任首相 1940-05-10 — 临危受命"}, {"name": "演讲", "start_date": "1940", "end_date": "1940", "place": "伦敦", "highlight": "至暗演讲 1940-06-04 — 演讲名场面"}, {"name": "胜利", "start_date": "1945", "end_date": "1945", "place": "伦敦", "highlight": "二战胜利 — 收束"}]}],
    "Q8023": [{"title_zh": "狱中27年与和解建国", "domain": "政治", "start_date": "1964", "end_date": "1994", "places": ["罗本岛", "开普敦", "比勒陀利亚"], "description_zh": "我在罗本岛的石场里学会：仇恨是自己的囚笼；出狱后我选择和解而非复仇，让分裂的国家得以缝合。", "outcome": "南非种族隔离终结，首任黑人总统", "lesson": "最长的坚持需要最柔软的心去收尾。", "phases": [{"name": "入狱", "start_date": "1964", "end_date": "1964", "place": "罗本岛", "highlight": "终身监禁 1964 — 至暗起点"}, {"name": "坚持", "start_date": "1964", "end_date": "1990", "place": "罗本岛", "highlight": "27年狱中 — 周期本体"}, {"name": "和解", "start_date": "1990", "end_date": "1994", "place": "比勒陀利亚", "highlight": "当选总统 1994 — 收束名场面"}]}],
    "Q19837": [{"title_zh": "被逐与回归", "domain": "商业/技术", "start_date": "1985", "end_date": "1997", "places": ["硅谷", "旧金山"], "description_zh": "我被自己创立的公司赶走，在NeXT与皮克斯的荒野里找回对产品的直觉；回归时把专注刻进苹果的每一道倒角。", "outcome": "iMac、iPod、iPhone 时代开启", "lesson": "被逐是重生的机会，专注比聪明更稀缺。", "phases": [{"name": "被逐", "start_date": "1985", "end_date": "1985", "place": "硅谷", "highlight": "被逐 1985 — 至暗起点"}, {"name": "荒野", "start_date": "1986", "end_date": "1996", "place": "旧金山", "highlight": "NeXT/皮克斯 — 沉淀期"}, {"name": "回归", "start_date": "1997", "end_date": "1997", "place": "旧金山", "highlight": "回归苹果 1997 — 转折名场面"}, {"name": "代表作", "start_date": "2007", "end_date": "2007", "place": "旧金山", "highlight": "iPhone 发布 2007-01-09 — 代表作名场面"}]}],
    "Q352": [{"title_zh": "夺权与战争动员", "domain": "政治/军事", "start_date": "1933", "end_date": "1945", "places": ["柏林", "华沙", "莫斯科"], "description_zh": "以仇恨与谎言动员的权力，短期内看似高效，长期必以毁灭自证其错。", "outcome": "二战爆发与纳粹覆灭", "lesson": "以仇恨为燃料的动员，短期有效、长期必毁。教训：警惕以单一敌人叙事整合社会。"}],
}

EVENTS_OFFLINE: dict[str, list[dict]] = {
    "Q4604": [
        {"date": "-551-09-28", "place_name": "曲阜", "event_type": "出生", "title_zh": "出生", "description_zh": "生于鲁国陬邑"},
        {"date": "-517", "place_name": "鲁", "event_type": "求学", "title_zh": "问礼于老子", "description_zh": "适周问礼"},
        {"date": "-497", "place_name": "卫", "event_type": "迁徙", "title_zh": "始周游列国", "description_zh": "离开鲁国，始十四年周游"},
        {"date": "-484", "place_name": "鲁", "event_type": "归隐", "title_zh": "归鲁整理六经", "description_zh": "不再求仕，转而修文"},
        {"date": "-479-04-11", "place_name": "曲阜", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于曲阜"},
    ],
    "Q162427": [
        {"date": "-259-02-18", "place_name": "邯郸", "event_type": "出生", "title_zh": "出生", "description_zh": "生于赵国邯郸"},
        {"date": "-230", "place_name": "咸阳", "event_type": "战役", "title_zh": "始灭韩", "description_zh": "十年灭六国之始"},
        {"date": "-221", "place_name": "咸阳", "event_type": "建制", "title_zh": "称皇帝、置郡县", "description_zh": "自称始皇帝"},
        {"date": "-219", "place_name": "泰山", "event_type": "巡行", "title_zh": "泰山封禅", "description_zh": "第一次东巡封禅"},
        {"date": "-210-07-10", "place_name": "沙丘", "event_type": "逝世", "title_zh": "逝于沙丘", "description_zh": "第五次巡行途中崩于沙丘"},
    ],
    "Q179544": [
        {"date": "181-01-01", "place_name": "阳都", "event_type": "出生", "title_zh": "出生", "description_zh": "生于琅琊阳都"},
        {"date": "207", "place_name": "隆中", "event_type": "际遇", "title_zh": "三顾茅庐", "description_zh": "刘备三顾茅庐，隆中对策定三分", "is_highlight": True, "highlight_type": "成语", "highlight_note": "成语 三顾茅庐，出自《三国志》，喻诚意求才"},
        {"date": "208", "place_name": "赤壁", "event_type": "战役", "title_zh": "赤壁之战", "description_zh": "联孙抗曹，奠定三分", "is_highlight": True, "highlight_type": "战役", "highlight_note": "名场面：以少胜多大决战"},
        {"date": "214", "place_name": "成都", "event_type": "建制", "title_zh": "入蜀定成都", "description_zh": "助刘备取益州"},
        {"date": "227", "place_name": "汉中", "event_type": "创作", "title_zh": "《出师表》", "description_zh": "上《出师表》率军北伐", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：鞠躬尽瘁，死而后已 出自此表"},
        {"date": "234-10-08", "place_name": "五丈原", "event_type": "逝世", "title_zh": "星落五丈原", "description_zh": "六出祁山，卒于五丈原", "is_highlight": True, "highlight_type": "成语", "highlight_note": "鞠躬尽瘁 成语意象定格于此"},
    ],
    "Q7074": [
        {"date": "701-01-01", "place_name": "碎叶", "event_type": "出生", "title_zh": "出生", "description_zh": "生于碎叶"},
        {"date": "742", "place_name": "长安", "event_type": "创作", "title_zh": "《蜀道难》成", "description_zh": "蜀道之难难于上青天", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作公布，奠定诗仙地位"},
        {"date": "744", "place_name": "长安", "event_type": "放逐", "title_zh": "赐金放还", "description_zh": "被赐金放还，漫游梁宋"},
        {"date": "752", "place_name": "梁园", "event_type": "创作", "title_zh": "《将进酒》", "description_zh": "君不见黄河之水天上来", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "名篇诞生，豪放巅峰"},
        {"date": "762-01-01", "place_name": "当涂", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于当涂"},
    ],
    "Q316452": [
        {"date": "1472-10-31", "place_name": "余姚", "event_type": "出生", "title_zh": "出生", "description_zh": "生于余姚"},
        {"date": "1508", "place_name": "龙场", "event_type": "贬谪", "title_zh": "谪居龙场", "description_zh": "因言获罪，谪贵阳龙场"},
        {"date": "1508", "place_name": "龙场", "event_type": "顿悟", "title_zh": "龙场悟道", "description_zh": "悟心即理，提出知行合一", "is_highlight": True, "highlight_type": "名言", "highlight_note": "名言 知行合一名场面诞生"},
        {"date": "1519", "place_name": "南昌", "event_type": "平叛", "title_zh": "平宸濠之乱", "description_zh": "三十五日平宁王之乱", "is_highlight": True, "highlight_type": "战役", "highlight_note": "战争名场面：以少胜多，周期极短的成事"},
        {"date": "1529-01-09", "place_name": "南安", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于江西南安途中", "is_highlight": True, "highlight_type": "名言", "highlight_note": "遗言 此心光明，亦复何言"},
    ],
    "Q193533": [
        {"date": "78-01-01", "place_name": "南阳", "event_type": "出生", "title_zh": "出生", "description_zh": "生于南阳西鄂"},
        {"date": "132", "place_name": "洛阳", "event_type": "发明", "title_zh": "地动仪成", "description_zh": "创候风地动仪，验陇西地震", "is_highlight": True, "highlight_type": "发明", "highlight_note": "发明名场面：人类首台验震器"},
        {"date": "139-01-01", "place_name": "洛阳", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于洛阳"},
    ],
    "Q133847": [
        {"date": "1371-01-01", "place_name": "昆明", "event_type": "出生", "title_zh": "出生", "description_zh": "生于云南昆阳"},
        {"date": "1405-07-11", "place_name": "南京", "event_type": "远航", "title_zh": "首下西洋启航", "description_zh": "率船队自南京起航", "is_highlight": True, "highlight_type": "远航", "highlight_note": "名场面：七下西洋之始"},
        {"date": "1433-01-01", "place_name": "古里", "event_type": "逝世", "title_zh": "卒于古里", "description_zh": "第七次下西洋归途卒于古里"},
    ],
    "Q334053": [
        {"date": "1785-08-30", "place_name": "福州", "event_type": "出生", "title_zh": "出生", "description_zh": "生于福州"},
        {"date": "1839-06-03", "place_name": "虎门", "event_type": "禁烟", "title_zh": "虎门销烟", "description_zh": "主持虎门销烟二十余日", "is_highlight": True, "highlight_type": "名言", "highlight_note": "名场面：虎门销烟，睁眼看世界起点"},
        {"date": "1839-08-01", "place_name": "广州", "event_type": "创作", "title_zh": "《四洲志》辑成", "description_zh": "主持编译《四洲志》", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：睁眼看世界第一步"},
        {"date": "1850-11-22", "place_name": "潮州", "event_type": "逝世", "title_zh": "逝世", "description_zh": "病逝于潮州普宁"},
    ],
    "Q23114": [
        {"date": "1881-09-25", "place_name": "绍兴", "event_type": "出生", "title_zh": "出生", "description_zh": "生于绍兴"},
        {"date": "1906", "place_name": "东京", "event_type": "抉择", "title_zh": "弃医从文", "description_zh": "在仙台弃医从文"},
        {"date": "1918-04-15", "place_name": "北京", "event_type": "创作", "title_zh": "《狂人日记》发表", "description_zh": "首篇白话小说", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作公布：1918-05-15《新青年》"},
        {"date": "1926", "place_name": "北京", "event_type": "创作", "title_zh": "《朝花夕拾》", "description_zh": "散文集", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作"},
        {"date": "1936-10-19", "place_name": "上海", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于上海"},
    ],
    "Q184080": [
        {"date": "1911-12-11", "place_name": "杭州", "event_type": "出生", "title_zh": "出生", "description_zh": "生于上海，籍杭州"},
        {"date": "1955-10-08", "place_name": "北京", "event_type": "归国", "title_zh": "归国", "description_zh": "经谈判回到祖国", "is_highlight": True, "highlight_type": "决策", "highlight_note": "名场面：五年羁留后归国"},
        {"date": "1970-04-24", "place_name": "酒泉", "event_type": "成就", "title_zh": "东方红一号发射", "description_zh": "主持发射首颗人造卫星", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：东方红一号 1970-04-24"},
        {"date": "2009-10-31", "place_name": "北京", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于北京"},
    ],
    "Q37230": [
        {"date": "1904-08-22", "place_name": "广安", "event_type": "出生", "title_zh": "出生", "description_zh": "生于四川广安"},
        {"date": "1978-12-18", "place_name": "北京", "event_type": "决策", "title_zh": "十一届三中全会", "description_zh": "推动改革开放", "is_highlight": True, "highlight_type": "决策", "highlight_note": "决策名场面：改革开放破局"},
        {"date": "1980-08-26", "place_name": "深圳", "event_type": "创举", "title_zh": "设深圳特区", "description_zh": "设立经济特区", "is_highlight": True, "highlight_type": "制度", "highlight_note": "制度发明：经济特区"},
        {"date": "1992-02-01", "place_name": "深圳", "event_type": "巡视", "title_zh": "南方谈话", "description_zh": "南巡讲话定调改革", "is_highlight": True, "highlight_type": "演讲", "highlight_note": "演讲名场面：南方谈话"},
        {"date": "1997-02-19", "place_name": "北京", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于北京"},
    ],
    "Q334642": [
        {"date": "1930-09-07", "place_name": "北京", "event_type": "出生", "title_zh": "出生", "description_zh": "生于北京"},
        {"date": "1964-06-01", "place_name": "长沙", "event_type": "发现", "title_zh": "发现天然雄性不育株", "description_zh": "在稻田发现关键材料"},
        {"date": "1973-10-10", "place_name": "长沙", "event_type": "育成", "title_zh": "籼型杂交水稻三系配套", "description_zh": "籼型三系配套成功", "is_highlight": True, "highlight_type": "发明", "highlight_note": "发明名场面：1973 三系配套成功"},
        {"date": "2021-05-22", "place_name": "长沙", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于长沙"},
    ],
    "Q913": [
        {"date": "-470-01-01", "place_name": "雅典", "event_type": "出生", "title_zh": "出生", "description_zh": "生于雅典"},
        {"date": "-399-05-07", "place_name": "雅典", "event_type": "审判", "title_zh": "饮鸩就义", "description_zh": "被判死刑，饮鸩而死", "is_highlight": True, "highlight_type": "名言", "highlight_note": "名言：我知我无知"},
    ],
    "Q1048": [
        {"date": "-100-07-12", "place_name": "罗马", "event_type": "出生", "title_zh": "出生", "description_zh": "生于罗马"},
        {"date": "-49-01-10", "place_name": "卢比孔河", "event_type": "抉择", "title_zh": "跨过卢比孔河", "description_zh": "率军渡河，内战爆发", "is_highlight": True, "highlight_type": "成语", "highlight_note": "典故：Alea iacta est 骰子已经掷下"},
        {"date": "-44-03-15", "place_name": "罗马", "event_type": "遇刺", "title_zh": "遇刺元老院", "description_zh": "在元老院遇刺身亡"},
    ],
    "Q720": [
        {"date": "1162-01-01", "place_name": "斡难河", "event_type": "出生", "title_zh": "出生", "description_zh": "生于斡难河畔"},
        {"date": "1206", "place_name": "斡难河", "event_type": "建制", "title_zh": "被推为成吉思汗", "description_zh": "统一蒙古诸部"},
        {"date": "1227-08-18", "place_name": "六盘山", "event_type": "逝世", "title_zh": "逝世", "description_zh": "西征途中卒于六盘山"},
    ],
    "Q762": [
        {"date": "1452-04-15", "place_name": "芬奇", "event_type": "出生", "title_zh": "出生", "description_zh": "生于佛罗伦萨芬奇镇"},
        {"date": "1495", "place_name": "米兰", "event_type": "创作", "title_zh": "《最后的晚餐》动笔", "description_zh": "为米兰圣玛利亚修道院作壁画", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：1495-1498"},
        {"date": "1503", "place_name": "佛罗伦萨", "event_type": "创作", "title_zh": "《蒙娜丽莎》起笔", "description_zh": "开始创作蒙娜丽莎", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：1503起，历时多年"},
        {"date": "1519-05-02", "place_name": "昂布瓦斯", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于法国昂布瓦斯"},
    ],
    "Q935": [
        {"date": "1643-01-04", "place_name": "伍尔斯索普", "event_type": "出生", "title_zh": "出生", "description_zh": "生于林肯郡伍尔斯索普"},
        {"date": "1666", "place_name": "伍尔斯索普", "event_type": "研究", "title_zh": "棱镜分解白光", "description_zh": "瘟疫返乡，棱镜实验", "is_highlight": True, "highlight_type": "发明", "highlight_note": "发明名场面：光学奠基"},
        {"date": "1687-07-05", "place_name": "伦敦", "event_type": "创作", "title_zh": "《原理》出版", "description_zh": "自然哲学的数学原理", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：1687-07-05《自然哲学的数学原理》"},
        {"date": "1727-03-31", "place_name": "伦敦", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于伦敦"},
    ],
    "Q517": [
        {"date": "1769-08-15", "place_name": "阿雅克肖", "event_type": "出生", "title_zh": "出生", "description_zh": "生于科西嘉阿雅克肖"},
        {"date": "1804-12-02", "place_name": "巴黎", "event_type": "称帝", "title_zh": "加冕称帝", "description_zh": "加冕为法兰西皇帝", "is_highlight": True, "highlight_type": "制度", "highlight_note": "制度名场面：拿破仑法典奠基"},
        {"date": "1815-06-18", "place_name": "滑铁卢", "event_type": "战役", "title_zh": "滑铁卢战败", "description_zh": "滑铁卢战败，帝国终结", "is_highlight": True, "highlight_type": "战役", "highlight_note": "战役名场面：滑铁卢"},
        {"date": "1821-05-05", "place_name": "圣赫勒拿", "event_type": "逝世", "title_zh": "逝世", "description_zh": "流放中卒于圣赫勒拿"},
    ],
    "Q7186": [
        {"date": "1867-11-07", "place_name": "华沙", "event_type": "出生", "title_zh": "出生", "description_zh": "生于华沙"},
        {"date": "1898-12-26", "place_name": "巴黎", "event_type": "发现", "title_zh": "发现镭", "description_zh": "与皮埃尔发现镭", "is_highlight": True, "highlight_type": "发明", "highlight_note": "发明名场面：1898发现镭与钋"},
        {"date": "1903-12-10", "place_name": "斯德哥尔摩", "event_type": "获奖", "title_zh": "诺贝尔物理学奖", "description_zh": "首次获诺奖", "is_highlight": True, "highlight_type": "奖项", "highlight_note": "奖项名场面：1903"},
        {"date": "1934-07-04", "place_name": "巴黎", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于巴黎"},
    ],
    "Q937": [
        {"date": "1879-03-14", "place_name": "乌尔姆", "event_type": "出生", "title_zh": "出生", "description_zh": "生于乌尔姆"},
        {"date": "1905-06-30", "place_name": "伯尔尼", "event_type": "创作", "title_zh": "狭义相对论", "description_zh": "论动体的电动力学", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：1905奇迹年"},
        {"date": "1915-11-25", "place_name": "柏林", "event_type": "创作", "title_zh": "广义相对论", "description_zh": "场方程发表", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：1915广义相对论"},
        {"date": "1955-04-18", "place_name": "普林斯顿", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于普林斯顿"},
    ],
    "Q1001": [
        {"date": "1869-10-02", "place_name": "波尔班达尔", "event_type": "出生", "title_zh": "出生", "description_zh": "生于古吉拉特"},
        {"date": "1930-03-12", "place_name": "萨巴尔马蒂", "event_type": "抗争", "title_zh": "食盐进军", "description_zh": "率众徒步240英里制盐抗税", "is_highlight": True, "highlight_type": "战役", "highlight_note": "名场面：食盐进军 Dandi March"},
        {"date": "1948-01-30", "place_name": "德里", "event_type": "遇刺", "title_zh": "遇刺", "description_zh": "被刺身亡"},
    ],
    "Q8016": [
        {"date": "1874-11-30", "place_name": "伦敦", "event_type": "出生", "title_zh": "出生", "description_zh": "生于伦敦"},
        {"date": "1940-06-04", "place_name": "伦敦", "event_type": "演讲", "title_zh": "至暗时刻演讲", "description_zh": "We shall fight on the beaches", "is_highlight": True, "highlight_type": "演讲", "highlight_note": "演讲名场面：1940-06-04 下议院"},
        {"date": "1965-01-24", "place_name": "伦敦", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于伦敦"},
    ],
    "Q8023": [
        {"date": "1918-07-18", "place_name": "库努", "event_type": "出生", "title_zh": "出生", "description_zh": "生于特兰斯凯库努"},
        {"date": "1990-02-11", "place_name": "开普敦", "event_type": "出狱", "title_zh": "获释", "description_zh": "27年后获释", "is_highlight": True, "highlight_type": "决策", "highlight_note": "名场面：1990-02-11获释"},
        {"date": "1994-04-27", "place_name": "比勒陀利亚", "event_type": "就任", "title_zh": "当选总统", "description_zh": "当选南非首任黑人总统", "is_highlight": True, "highlight_type": "制度", "highlight_note": "制度名场面：和解建国"},
        {"date": "2013-12-05", "place_name": "约翰内斯堡", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于约翰内斯堡"},
    ],
    "Q19837": [
        {"date": "1955-02-24", "place_name": "旧金山", "event_type": "出生", "title_zh": "出生", "description_zh": "生于旧金山"},
        {"date": "1985-09-17", "place_name": "硅谷", "event_type": "放逐", "title_zh": "被逐出苹果", "description_zh": "被董事会逐出", "is_highlight": True, "highlight_type": "决策", "highlight_note": "转折名场面：被逐"},
        {"date": "1997-07-09", "place_name": "旧金山", "event_type": "回归", "title_zh": "回归苹果", "description_zh": "回归并重塑苹果", "is_highlight": True, "highlight_type": "决策", "highlight_note": "转折名场面：回归"},
        {"date": "2007-01-09", "place_name": "旧金山", "event_type": "发布", "title_zh": "iPhone 发布", "description_zh": "发布 iPhone，定义智能手机", "is_highlight": True, "highlight_type": "代表作", "highlight_note": "代表作：2007-01-09 iPhone 发布"},
        {"date": "2011-10-05", "place_name": "帕洛阿尔托", "event_type": "逝世", "title_zh": "逝世", "description_zh": "卒于帕洛阿尔托"},
    ],
    "Q352": [
        {"date": "1889-04-20", "place_name": "布劳瑙", "event_type": "出生", "title_zh": "出生", "description_zh": "生于奥匈布劳瑙"},
        {"date": "1933-01-30", "place_name": "柏林", "event_type": "夺权", "title_zh": "就任总理", "description_zh": "被任命为德国总理"},
        {"date": "1939-09-01", "place_name": "华沙", "event_type": "战争", "title_zh": "入侵波兰", "description_zh": "发动二战"},
        {"date": "1945-04-30", "place_name": "柏林", "event_type": "自杀", "title_zh": "自杀", "description_zh": "在柏林地堡自杀"},
    ],
}


def enrich_offline(seed_meta: dict[str, dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for qid, meta in seed_meta.items():
        base = dict(OFFLINE.get(qid, {}))
        if meta.get("role"):
            base["role"] = meta["role"]
        if meta.get("sensitivity"):
            base["sensitivity"] = meta["sensitivity"]
        if meta.get("visibility"):
            base["visibility"] = meta["visibility"]
        if not base:
            base = {"name_zh": meta.get("name_zh", qid)}
        eds: list[Endeavor] = []
        for idx, raw in enumerate(ENDEAVORS_OFFLINE.get(qid, []), 1):
            eds.append(
                Endeavor(
                    id=f"{qid}-endeavor-{idx}",
                    person_qid=qid,
                    title_zh=raw["title_zh"],
                    domain=raw.get("domain"),
                    start_date=raw.get("start_date"),
                    end_date=raw.get("end_date"),
                    places=raw.get("places", []),
                    description_zh=raw.get("description_zh"),
                    outcome=raw.get("outcome"),
                    lesson=raw.get("lesson"),
                    phases=raw.get("phases", []),  # type: ignore — dicts auto-coerced to Phase
                    event_ids=[],
                    sources=[f"https://www.wikidata.org/wiki/{qid}"],
                    review_status="ai_filled",
                )
            )
        base["_endeavors"] = eds
        base["_events"] = EVENTS_OFFLINE.get(qid, [])
        out[qid] = base
    return out
