import os.path
import shutil
import subprocess
import time

from bs4 import BeautifulSoup
import requests


class Animate:
    def __init__(self, search_name, fuzzy_name: list, real_name, current_chapter, jump_url, magnet, file_name):
        self.search_name = search_name  # 网页上用来搜索的关键字
        self.fuzzy_name: list = fuzzy_name  # 搜出来的结果进行模糊匹配
        self.real_name = real_name  # 本地存储时的真正名字
        self.current_chapter = current_chapter  # 第x集
        self.jump_url = jump_url  # 网页跳转的url
        self.magnet = magnet  # 磁力
        self.file_name = file_name  # 磁力下载的文件名

    def __str__(self):
        return (f"Animate: search_name={self.search_name} "
                f"fuzzy_name={self.fuzzy_name} "
                f"real_name={self.real_name} "
                f"current_chapter={self.current_chapter} "
                f"jump_url={self.jump_url} "
                f"magnet={self.magnet} "
                f"file_name={self.file_name} ")


storage_path = 'D:\\animate'
db_file_name = 'db.txt'
base_url = 'https://www.comicat.org'
magnet_prefix = 'magnet:?xt=urn:btih:'
animate_list = [
    Animate(
        '俄语的',
        ["俄語", "俄语", "不时轻声地以俄语遮羞的邻座艾莉同学", "不時輕聲地以俄語遮羞的鄰座艾琳同學"],
        "不时轻声地以俄语遮羞的邻座艾莉同学",
        "04",
        None,
        None,
        None),
    Animate(
        '鹿乃子',
        ["鹿乃子乃子乃子虎視眈眈", "Shikanoko"],
        "鹿乃子乃子乃子虎視眈眈",
        "03",
        None,
        None,
        None),
    Animate(
        'hana',
        ["亦叶亦花", "Hana Nare"],
        "亦叶亦花",
        "03",
        None,
        None,
        None),
    Animate(
        '我推的孩子',
        ["我推的孩子", "Oshi no Ko"],
        "我推的孩子",
        "14",
        None,
        None,
        None),
    Animate(
        'Mayonaka',
        ["深夜重拳", "Mayonaka Pubch"],
        "深夜重拳",
        "03",
        None,
        None,
        None),
    Animate(
        'atri',
        ["亚托莉", "亞托莉", "Atri"],
        "亚托莉我挚爱的时光",
        "02",
        None,
        None,
        None),
    Animate(
        'Monogatari',
        ["物语系列", "Monogatari"],
        "物语系列",
        "03",
        None,
        None,
        None),
    Animate(
        '小市民',
        ["小市民", "MonogatariShoushimin"],
        "小市民",
        "03",
        None,
        None,
        None),
    Animate(
        '夜樱家',
        ["夜樱家", "Yozakura"],
        "夜樱家的大作战",
        "14",
        None,
        None,
        None),
]


def read_property():
    db_path = os.path.join(storage_path, db_file_name)
    with open(db_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for i in range(0, len(lines)):
            line = lines[i].strip()
            if line:
                real_name, current_chapter = line.split('-', 1)
                animate_list[i].current_chapter = current_chapter
    print('read property success')


def save_property():
    db_path = os.path.join(storage_path, db_file_name)
    with open(db_path, 'w', encoding='utf-8') as file:
        for obj in animate_list:
            file.write(f"{obj.real_name}-{increment_string_number(obj.current_chapter)}\n")
    print('save property success')


def increment_string_number(number_str):
    # 将字符串转换为整数
    num = int(number_str)

    # 加一
    num += 1

    # 根据加一后的结果进行处理
    if num == 10:
        # 如果结果是10，转换为字符串"10"
        return "10"
    else:
        # 否则，保持两位数的字符串表示
        # 使用zfill方法确保字符串总是两位数，例如"9"变成"09"
        return str(num).zfill(2)


def get_links():
    print('start to get link')
    for animate in animate_list:
        time.sleep(1)
        url = f"{base_url}/search.php?keyword={animate.search_name}"

        payload = {}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        html = response.text
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(html, 'html.parser')

        # 查找目标标签
        target_tag = 'tbody'
        target_id = 'data_list'
        target_element = soup.find(target_tag, id=target_id)

        # 查找tr标签
        tr_tags = target_element.find_all('tr')

        # 创建list对象
        result_list = []

        href_list = []
        magnet_list = []
        # 遍历tr标签，查找td标签
        for tr_tag in tr_tags:
            td_tags = tr_tag.find_all('td')
            # check size
            html_animate_size = td_tags[3].text
            # bytes，gb过滤
            if html_animate_size[-2:].lower() == "es" or html_animate_size[-2:].lower() == "gb" or float(html_animate_size[:-2]) > 900:
                continue

            if check(animate, td_tags[2].text):
                a_tag = td_tags[2].find('a')
                if a_tag:
                    href_value = a_tag['href']
                    href_list.append(href_value)
                    animate.jump_url = href_value
                    a, magnet = href_value.split('-')
                    animate.magnet = magnet_prefix + magnet[:-5]
                    magnet_list.append(magnet)
            if len(magnet_list) > 0:
                break
        #     row_data = []
        #     for td_tag in td_tags:
        #         row_data.append(td_tag.text)
        #     result_list.append(row_data)
        # print(result_list)
    for animate in animate_list:
        if animate.magnet == '' or animate.magnet is None:
            print(f'{animate.real_name} link not found')


def check(animate: Animate, html_animate_name: str) -> bool:
    # 集数在名字的后面，并且集数的数字前后不能有其他数字。文件值不能超过900m。
    fuzzy_name_index = None
    for f in animate.fuzzy_name:
        index = html_animate_name.find(f)
        if index != -1:
            fuzzy_name_index = index
    if fuzzy_name_index is None:
        print('animate fuzzy name not found: ' + animate.real_name)
        return False

    for i in range(fuzzy_name_index, len(html_animate_name) - 1):
        pair = html_animate_name[i] + html_animate_name[i + 1]
        if (pair == str(animate.current_chapter)
                and not html_animate_name[i - 1].isdigit()
                and i + 2 < len(html_animate_name)
                and not html_animate_name[i + 2].isdigit()):
            return True

    return False


def download_magnet():
    print('start to download magnet')
    for animate in animate_list:
        if animate.magnet is None or animate.magnet == '':
            continue
        initial_files = get_all_files(storage_path)
        call_bitcomet(animate.magnet)
        cnt = 0
        for cnt in range(0, 20):
            time.sleep(6)
            cnt += 1
            new_files = get_all_files(storage_path)
            added_files = [file for file in new_files if file not in initial_files]
            if added_files is not None and len(added_files) > 0:
                animate.file_name = added_files[0]
                break


def check_all_task_success():
    print('start to check task')
    # 校验所有下载任务是否完成，时长一个小时
    for cnt in range(0, 600):
        time.sleep(6)
        cnt += 1
        if cnt % 10 == 0:
            print(f'{cnt * 6} sec passed')
        all_completed = True
        for animate in animate_list:
            if animate.file_name is None:
                continue
            file_name = os.path.basename(animate.file_name)[:-4]
            for file in get_all_files(storage_path):
                if file_name in file and file.endswith('.bc!'):
                    if cnt % 10 == 0:
                        print(f'wait for {file}')
                    all_completed = False
        if all_completed:
            return True
    return False


def move_success_animate():
    print("start to move animate")
    for animate in animate_list:
        if animate.file_name is None:
            continue
        file_name = os.path.basename(animate.file_name)[:-4]
        for file in get_all_files(storage_path):
            if file_name in file and '.bc' not in file:
                move_file(storage_path, os.path.join(storage_path, animate.real_name), file_name)


def move_file(source_dir, destination_dir, filename):
    # 检查源目录中是否存在目标文件
    file_path = os.path.join(source_dir, filename)
    if os.path.isfile(file_path):
        # 移动文件到目标目录
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        destination_path = os.path.join(destination_dir, filename)
        shutil.copy2(file_path, destination_path)
        print(f"文件 {filename} 移动成功！")
    else:
        print(f"文件 {filename} 不存在于目录 {source_dir} 中！")


def call_bitcomet(magnet):
    command = f"\"C:\\Program Files\\BitComet\\bitcomet\" --url {magnet} -s --tray"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stderr != "":
        raise Exception('call bitcomet error: ' + command)


def get_all_files(folder_path):
    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)
    return file_list


read_property()
get_links()
download_magnet()
check_all_task_success()
move_success_animate()
save_property()
for animate in animate_list:
    print(animate)