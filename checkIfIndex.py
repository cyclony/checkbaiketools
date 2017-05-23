from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import sys
import os

xl_files = [file for file in os.listdir() if (file.endswith('xlsx') or file.endswith('xls')) and file.find('result_')< 0]


url_prex = 'https://www.sogou.com/web?query='
query_newform = 'http://baike.sogou.com/v{id}.htm?fromTitle={name}'
query_oldform = 'http://baike.sogou.com/v{id}.htm'
prg_size = 0  # init size
prg_i = 0

def progress_print_decorator(func):
    def func_wrapper(row):
        result = func(row)
        global prg_i
        global prg_size
        prg_i += 1
        print('{:.2%} 词条:{词条名}, 结果:{result}'.format(prg_i/prg_size, 词条名=row['词条名'], result=result))
        return result
    return func_wrapper


#  这是一个decorator方法定义，为业务逻辑加上重试的逻辑
def retry(max_retry_times, sleep_secs):
    def retry_decorator(func):
        def func_wrapper(*args):
            retry_times = 0
            while retry_times < max_retry_times:
                try:
                    return func(*args) #业务执行的核心逻辑
                    break
                except Exception as e:
                    retry_times =+ 1
                    print("encounter error: ", e)
                    time.sleep(sleep_secs)#停一段时间再发送数据
                    if retry_times == max_retry_times:
                        raise e;#达到最大重复尝试次数，放弃尝试，将异常抛出，由顶层逻辑处理（将已经抓取的数据保存下来）
        return func_wrapper
    return retry_decorator


# 判断网页是否被大搜索引
@retry(3, 5)
def checkIfIndex_byurl(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text)
    results = soup.select('div.linkhead')
    return not any(result.text.find('未收录？点击此处提交') >= 0 for result in results)  # 如果没有“未收录”信息，返回TRUE（收录）


def encode_url_new(row):
    encode_query = requests.utils.quote(query_newform.format(id=row.ID, name=requests.utils.quote(str(row.词条名))), safe='')
    return url_prex + encode_query


def encode_url_old(row):
    encode_query = requests.utils.quote(query_oldform.format(id=row.ID), safe='')
    return url_prex + encode_query


@progress_print_decorator
def check_if_index(row):
    return any((checkIfIndex_byurl(encode_url_new(row)), checkIfIndex_byurl(encode_url_old(row))))


for file in xl_files:
    xl = pd.read_excel(file)
    prg_size = len(xl)
    prg_i = 0
    xl['result'] = xl.apply(check_if_index, axis=1)
    xl.to_excel('result_'+file)
