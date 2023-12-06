from flask import Flask, request, render_template
from multiprocessing import Process
import requests
import threading
import json
import os
import time
import shutil
from asgiref.wsgi import WsgiToAsgi

from send_feishu import (get_token, get_app_token, get_user_login, refresh_access_token, query_feishu_sheet_value,
                         get_sheet_info, get_old_token)
from tools.utils import get_sheet_token_id, get_dict_by_dot

import configparser
from tools.data_model import create_client
from qt_data.plot_fn import PlotMain
from tools.score_for_google_index import gen_plot_data
from tools.utils import pull_code
import subprocess
import uvicorn




def save_user(result):
    try:
        config = configparser.ConfigParser()
        # 添加或修改配置项
        config['INFO'] = result
        # 或者使用 set 方法
        # config.set('section_name', 'key3', 'value3')
        with open('userinfo.ini', 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print('本地保存失败', e)

    # 你的查询条件，这里使用文档的唯一标识字段 _id
    query = {"user_name": result['user_name']}
    # 你要插入的数据
    update_data = {
        "$set": result
    }
    db_client = create_client()  # 正式
    # return client['feishudb']['StaffAdmin'].insert_one(result)
    return db_client['feishudb']['StaffAdmin'].update_one(query, update_data, upsert=True)


# 创建Flask应用程序
app = Flask(__name__, template_folder='vue_temp', static_folder='vue_static')


# 定义一个路由和视图函数
@app.route('/')
def index():
    # return "欢迎进入小程序后台"
    return render_template('index.html')


@app.route('/version')
def version():
    resp = query_feishu_sheet_value()
    print('version', resp)
    return {"version": resp['data']['valueRange']['values'][0][0]}


@app.route('/ooo')
def ooo():
    # return "欢迎进入小程序后台"
    return {"msg": "sssss123123"}


@app.route('/local/data', methods=['POST'])
def get_post_data():
    data = request.get_json()  # 获取JSON数据

    keywords = '"red light therapy" "hair"'
    resp = gen_plot_data([keywords])
    plot_image = PlotMain(keywords=keywords, plot_data=resp['data'], plot_size=resp['size'],
                          plot_keys=resp['keys'])

    return {"message": f'Successfully received data!:type:{type(data)},data:{data}', "data": plot_image.image_base64}


@app.route('/local/chart', methods=['POST'])
def get_post_chart():
    data = request.get_json()  # 获取JSON数据
    # uri = data['uri']
    # keywords = '"red light therapy" "hair"'
    keywords = data['keywords']
    # col = data['col']
    # sheet_id = data['sheet_id']
    sheet_values = data['sheet_values']
    # keywords = '"red light therapy" "hair"'

    # sheet_token_key, sheet_id_key = get_sheet_token_id(uri)
    # print('sheet_token_key, sheet_id_key', sheet_token_key, sheet_id_key)

    # sheet_token_key = 'KmjzssTC2hzenct8pJKcfDxwnhs'
    # start_index = 0
    # sheet_list = [sheet_id]
    # demographics_keywords_arr, sheet_id_list = get_feishu_score_keywords(sheet_token=sheet_token_key,
    #                                                                      start_index=0,
    #                                                                      start_col=1,
    #                                                                      sheet_list=sheet_list)
    resp = gen_plot_data([keywords], sheet_values)

    return {"message": f'Successfully received data!:type:{type(data)},data:{data}', "data": resp}

@app.route('/local/token', methods=['GET'])
def query_user_token():
    return {"token": get_token()}
    # return {"token": None}

@app.route('/local/sheet_values', methods=['GET'])
def query_sheet_values():
    sheet_token = request.args.get('sheet_token')
    sheet_id = request.args.get('sheet_id')
    col = request.args.get('col')
    col = col.upper()
    resp = query_feishu_sheet_value(sheet_token=sheet_token, sheet_id=sheet_id, range_value=f'{col}:{col}')
    return {"message": '', "data": resp}


@app.route('/local/sheet_table_values', methods=['GET'])
def query_table():
    # uri = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{sheet_token}/values_batch_get?ranges={sheet_ranges}&valueRenderOption=ToString&dateTimeRenderOption=FormattedString',
    sheet_token = request.args.get('sheet_token')
    sheet_id = request.args.get('sheet_id')
    headers = {
        'Authorization': f'Bearer {get_token()}',
    }
    res = requests.get(
        f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{sheet_token}/values_batch_get?ranges={sheet_id}&valueRenderOption=ToString&dateTimeRenderOption=FormattedString',
        headers=headers)
    return res.json()

@app.route('/local/sheet_list', methods=['GET'])
def query_sheet_list():
    start_index = 0
    sheet_token = request.args.get('sheet_token')
    sheet_list_info = get_sheet_info(sheet_token, start_index)
    return {"message": '', "data": sheet_list_info}


@app.route('/local/translation_detect', methods=['POST'])
def translation_detect():
    # txt = request.args.get('txt')
    data = request.get_json()  # 获取JSON数据
    txt = data['txt']
    uri = 'https://open.feishu.cn/open-apis/translation/v1/text/detect'
    payload = json.dumps({
        "text": txt
    })
    req_token = get_old_token()
    headers = {
        'Authorization': f'Bearer {req_token}',
    }
    response = requests.post(uri, headers=headers, data=payload)
    print(response.text)
    return {"data": response.json(), "token": req_token}

@app.route('/local/translate', methods=['POST'])
def translate():
    # s_lang = request.args.get('s_lang') or 'en'
    # t_lang = request.args.get('t_lang') or 'zh'
    # txt = request.args.get('txt')
    data = request.get_json()  # 获取JSON数据
    s_lang = data['s_lang'] or 'en'
    t_lang = data['t_lang'] or 'zh'
    txt = data['txt']

    uri = 'https://open.feishu.cn/open-apis/translation/v1/text/translate'
    payload = json.dumps({
        # "glossary": [
        # 	{
        # 		"from": "Lark",
        # 		"to": "飞书"
        # 	}
        # ],
        "source_language": s_lang,
        "target_language": t_lang,
        "text": txt
    })

    headers = {
        'Authorization': f'Bearer {get_old_token()}',
    }

    response = requests.post(uri, headers=headers, data=payload)
    return response.json()


def stop_serve():
    # Get the list of processes with 'ps aux' command
    processes = subprocess.check_output(['ps', 'aux']).decode('utf-8')
    # Find the processes that contain 'gunicorn' and 'app_serve'
    for line in processes.splitlines():
        if 'app_serve' in line:
            # Extract the process ID (PID) using split and get the second element
            pid = int(line.split()[1])
            # Kill the process using os.kill with the SIGKILL signal
            os.kill(pid, signal.SIGKILL)
@app.route('/pull')
def pull_app():
    # return "欢迎进入小程序后台"
    # https://github.com/wxjbnu/hot-python.git
    pull_code('main', 'https://github.com/wxjbnu/hot-python.git')

    source_folder = 'tmp'
    dest_folder = ''
    for file_name in os.listdir(source_folder):
        if not file_name.startswith('.'):
            source = os.path.join(source_folder, file_name)
            destination = os.path.join(dest_folder, file_name)
            shutil.move(source, destination)

    # subprocess.run(["sh", "app_restart.sh"])
    stop_serve()
    start_web()

    return {"msg": "success"}


# 定义一个路由和视图函数
@app.route('/login')
def login():
    user_name = request.args.get('state')
    code = request.args.get('code')
    if user_name and code:
        app_access_token = get_app_token()
        if app_access_token is not None:
            try:
                user_data = get_user_login(app_access_token, code)
                if user_data.get('code') == 0:
                    user_info = user_data['data']
                    user_info['user_name'] = user_name
                    user_info['app_access_token'] = app_access_token

                    token_expire = user_info['expires_in']
                    user_info['token_expire'] = int(time.time()) + token_expire - 300

                    save_user(user_info)
            except Exception as e:
                print('err', e)
        return f'[{user_name}]登录成功'
        # return f'{user_name}-{code}'
    return "Hello, login!"

# @app.route('/restart')
# def serve_restart():
#     ss = subprocess.run(["sh", "app_restart.sh"])
#     return ss

@app.route('/restart')
def sh_restart():
    # command = "kill -9 $(ps aux | grep 'gunicorn' | grep 'app_serve' | awk '{print $2}')"
    # process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    # output, error = process.communicate()
    # if output:
    #     return f'Script output: {output}'
    # else:
    #     return f'Script error: {error}'
    stop_serve()
    start_web()

@app.route('/stop')
def serve_stop():
    ss = subprocess.run(["sh", "app_stop.sh"])
    return ss


@app.route('/mmm')
def hhh():
    return {"msg": "mmm"}

# @app.route('/nnn')
# def nnn():
#     return {"msg": "nnn"}

def run_flask():
    # app.run(port=7777)
    # app.run(host='0.0.0.0', port=7777, debug=True)
    # app.run(host='0.0.0.0', port=7777, debug=True)
    asgi_app = WsgiToAsgi(app)
    uvicorn.run(asgi_app, host="0.0.0.0", port=7777, ) #reload=True

def start_web():
    serve_thread = threading.Thread(target=run_flask)
    # thread2 = threading.Thread(target=start_app)
    # 启动线程
    serve_thread.start()

if __name__ == '__main__':
    run_flask()
    pass
