from bs4 import BeautifulSoup
import urllib
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
        print('%.1f%%' %(100*prg_i/prg_size), ' check 词条:',row['词条名'], 'result is ', result)
        return result
    return func_wrapper


#这是一个decorator方法定义，为业务逻辑加上重试的逻辑
def retry(max_retry_times, sleep_secs):
    def retry_decorator(func):
        def func_wrapper(*args):
            retry_times = 0;
            while retry_times < max_retry_times:
                try:
                    return func(*args);#业务执行的核心逻辑
                    break;
                except Exception as e:
                    retry_times =+ 1;
                    print("encount error: ", e)
                    time.sleep(sleep_secs)#停一段时间再发送数据
                    if retry_times == max_retry_times:
                        raise e;#达到最大重复尝试次数，放弃尝试，将异常抛出，由顶层逻辑处理（将已经抓取的数据保存下来）

        return func_wrapper
    return retry_decorator


# 判断网页是否被大搜索引
@retry(3, 5)
def checkIfIndex_byurl(url):
    raw = urllib.request.urlopen(url)
    soup = BeautifulSoup(raw)
    results = soup.select('div.linkhead')
    for result in results:
        if result.text.find('未收录？点击此处提交')>=0:
            return False
    return True


def encodeURL_newform(row):
    encode_query = urllib.parse.quote_plus(query_newform.format(id = row.ID, name = urllib.parse.quote(str(row.词条名))))
    return url_prex + encode_query

def encodeURL_oldform(row):
    encode_query = urllib.parse.quote_plus(query_oldform.format(id = row.ID))
    return url_prex + encode_query


@progress_print_decorator
def checkIndex(row):
    if checkIfIndex_byurl(encodeURL_newform(row)) or checkIfIndex_byurl(encodeURL_oldform(row)):
        return True
    else:
        return False

for file in xl_files:
    xl = pd.read_excel(file)
    prg_size = len(xl)
    prg_i = 0
    xl['result'] = xl.apply(checkIndex, axis=1)
    xl.to_excel('result_'+file)
