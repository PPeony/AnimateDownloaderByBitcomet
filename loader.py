import os.path
import shutil
import subprocess
import time
from typing import List
import enum
from bs4 import BeautifulSoup
import requests


class DownloadStatus(enum.Enum):
    START_DOWNLOAD = 'start download'
    DOWNLOAD_DONE = 'download done'
    MOVED = 'moved'
    TASK_COMPLETED = 'task completed'

class Animate:
    def __init__(self, search_name, fuzzy_name: str, real_name, current_chapter, jump_url, magnet, file_name, update_date, fansub_name, status=None, item_id=None):
        self.search_name = search_name  # 网页上用来搜索的关键字
        self.fuzzy_name: str = fuzzy_name  # 搜出来的结果进行模糊匹配，逗号分隔的列表
        self.real_name = real_name  # 本地存储时的真正名字
        self.current_chapter = current_chapter  # 第x集
        self.jump_url = jump_url  # 网页跳转的url
        self.magnet = magnet  # 磁力
        self.file_name = file_name  # 磁力下载的文件名
        self.status = status  # 状态，下载中/已完成
        self.item_id = item_id  # 界面中对应的item_id
        self.update_date = update_date  # 更新日期
        self.fansub_name = fansub_name  # 字幕组名字，可选

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        return (f"Animate: search_name={self.search_name} "
                f"fuzzy_name={self.fuzzy_name} "
                f"real_name={self.real_name} "
                f"current_chapter={self.current_chapter} "
                f"jump_url={self.jump_url} "
                f"magnet={self.magnet} "
                f"file_name={self.file_name} "
                f"status={self.status} "
                f"item_id={self.item_id} "
                )


storage_path = 'D:\\animate'
db_file_name = 'db.txt'
base_url = 'https://www.comicat.org'
magnet_prefix = 'magnet:?xt=urn:btih:'


def read_property(db_path) -> List[Animate]:
    l = []
    with open(db_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for i in range(0, len(lines)):
            line = lines[i].strip()
            if line:
                vals = line.split('-')
                real_name = vals[0]
                search_name = vals[1]
                fuzzy_name = vals[2]
                current_chapter = vals[3]
                update_date = vals[4]
                fansub_name = None
                if len(vals) > 5:
                    fansub_name = vals[5]
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                l.append(
                    Animate(search_name, fuzzy_name, real_name, current_chapter, None, None, None, days[int(update_date) - 1], fansub_name))
    print('read property success')
    return l


def save_property(l, db_path):
    days = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}
    with open(db_path, 'w', encoding='utf-8') as file:
        for obj in l:
            s = f"{obj.real_name}-{obj.search_name}-{obj.fuzzy_name}-{obj.current_chapter}-{days[obj.update_date]}-"
            if obj.fansub_name is not None:
                s += f"{obj.fansub_name}"
            file.write(s + " \n")


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


def get_links(animate_list):
    print('start to get link')
    for animate in animate_list:
        time.sleep(1)
        animate = get_link(animate)
        #     row_data = []
        #     for td_tag in td_tags:
        #         row_data.append(td_tag.text)
        #     result_list.append(row_data)
        # print(result_list)
    for animate in animate_list:
        if animate.magnet == '' or animate.magnet is None:
            print(f'{animate.real_name} link not found')

def get_link(animate):
    url = f"{base_url}/search.php?keyword={animate.search_name}"

    payload = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Cookie': 'visitor_test=human',
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
        if html_animate_size[-2:].lower() == "es" or html_animate_size[-2:].lower() == "gb" or float(
                html_animate_size[:-2]) > 900:
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
    return animate

def check(animate: Animate, html_animate_name: str) -> bool:
    # 集数在名字的后面，并且集数的数字前后不能有其他数字。文件值不能超过900m。
    fuzzy_name_index = None
    fuzzy_name_list = animate.fuzzy_name.split(',')
    for f in fuzzy_name_list:
        index = html_animate_name.find(f)
        if index != -1:
            fuzzy_name_index = index
    if fuzzy_name_index is None:
        print('animate fuzzy name not found: ' + animate.real_name)
        return False

    if animate.fansub_name != '' and f'[{animate.fansub_name}]' not in html_animate_name:
        return False

    for i in range(fuzzy_name_index, len(html_animate_name) - 1):
        pair = html_animate_name[i] + html_animate_name[i + 1]
        if (pair == str(animate.current_chapter)
                and not html_animate_name[i - 1].isdigit()
                and i + 2 < len(html_animate_name)
                and not html_animate_name[i + 2].isdigit()):
            return True

    return False


def download_magnet(animate):
    if animate.magnet is None or animate.magnet == '':
        return
    initial_files = get_all_files(storage_path)
    call_bitcomet(animate.magnet)
    cnt = 0
    for cnt in range(0, 20):
        print("wait")
        time.sleep(6)
        cnt += 1
        new_files = get_all_files(storage_path)
        added_files = [file for file in new_files if file not in initial_files]
        if added_files is not None and len(added_files) > 0:
            animate.file_name = added_files[0]
            break
    animate.status = DownloadStatus.START_DOWNLOAD


def check_all_task_success(animate_list):
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
                if file_name in file:
                    if file.endswith('.bc!'):
                        if cnt % 10 == 0:
                            print(f'wait for {file}')
                        all_completed = False
                    else:
                        animate.status = DownloadStatus.DOWNLOAD_DONE
        if all_completed:
            return True
    return False


def move_success_animate(animate_list):
    print("start to move animate")
    for animate in animate_list:
        if animate.file_name is None:
            continue
        file_name = os.path.basename(animate.file_name)[:-4]
        for file in get_all_files(storage_path):
            if file_name in file and '.bc' not in file:
                move_file(storage_path, os.path.join(storage_path, animate.real_name), file_name)
        animate.status = DownloadStatus.MOVED


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


# read_property()
# get_links()
# download_magnet()
# check_all_task_success()
# move_success_animate()
# save_property()
# for animate in animate_list:
#     print(animate)