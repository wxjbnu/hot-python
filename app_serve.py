from flask import Flask, request, render_template
from multiprocessing import Process
import requests
import threading
import os
import time
import shutil
from send_feishu import get_token, get_app_token, get_user_login, refresh_access_token, query_feishu_sheet_value
from tools.utils import get_sheet_token_id, get_dict_by_dot

import configparser
from tools.data_model import create_client
from qt_data.plot_fn import PlotMain
from tools.score_for_google_index import gen_plot_data
from tools.utils import pull_code
import subprocess




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
    return {"version": resp['data']['valueRange']['values'][0][0]}


@app.route('/ooo')
def ooo():
    # return "欢迎进入小程序后台"
    return {"msg": "sssss"}


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
    uri = data['uri']
    keywords = data['keywords']
    col = data['col']
    # keywords = '"red light therapy" "hair"'
    resp = gen_plot_data([keywords])

    sheet_token_key, sheet_id_key = get_sheet_token_id(uri)
    print('sheet_token_key, sheet_id_key', sheet_token_key, sheet_id_key)

    sheet_token_key = 'KmjzssTC2hzenct8pJKcfDxwnhs'
    start_index = 0
    sheet_list = ['b1c868']
    demographics_keywords_arr, sheet_id_list = get_feishu_score_keywords(sheet_token=sheet_token_key,
                                                                         start_index=0,
                                                                         start_col=1,
                                                                         sheet_list=sheet_list)

    return {"message": f'Successfully received data!:type:{type(data)},data:{data}', "data": resp}

@app.route('/local/sheet_list', methods=['GET'])
def query_sheet_list():
    start_index = 0
    sheet_token = request.args.get('sheet_token')
    sheet_list_info = get_sheet_info(sheet_token, start_index)
    return {"message": '', "data": sheet_list_info}


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

    subprocess.run(["sh", "app_restart.sh"])

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


def run_flask():
    # app.run(port=7777)
    # app.run(host='0.0.0.0', port=7777, debug=True)
    app.run(host='0.0.0.0', port=7777, )


if __name__ == '__main__':
    # run_flask()
    pass
