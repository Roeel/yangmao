import requests
import time
import datetime
import threading

################################ 配置区开始 ################################
# 使用 www.pushplus.plus 进行消息推送
PUSH_PLUS_TOKEN = '01558469ed7a41fb9d11111c97eae71f'

# 多账号配置
# mobile 手机号
# refreshToken 登录后获取的refresh_token
config_list = [
    {"mobile": "12345678910", "refreshToken": "7807f3d8-1111-4ea5-b9bf-6bb17b8ea6bc"},
    {"mobile": "12345678911", "refreshToken": "1111f3d8-1111-4ea5-b9bf-6bb17b1111bc"},
]

################################ 配置区结束 ################################


headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; M2011K2C Build/SKQ1.211006.001)"}
msg_list = []

def pushplus(title, content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSH_PLUS_TOKEN,
        "title": title,
        "content": content
    }
    print(requests.post(url=url, json=data).json())


def format_msg():
    str1 = ''
    for item in msg_list:
        str1 += str(item) + "\r\n"
    return str1


def get(url, data):
    print(data)
    ret = requests.get(url=url, params=data, headers=headers).json()
    print(ret)
    return ret


def post(url, data, token=None):
    print(data)
    ret = requests.post(url=url, params=data, headers={"Authorization": token, **headers}).json()
    print(ret)
    return ret


def refresh(refresh_token):
    url = 'https://account.bol.wo.cn/cuuser/cuauth/token'
    data = {
        "clientSecret": "ybdkqwvi5hulnckjm255gvxqsb8elygo",
        "clientId": "woportal",
        "grantType": "refresh_token",
        "refreshToken": refresh_token,
    }
    return get(url, data)


def user_info(access_token):
    url = 'https://wo.cn/woportalapi/cuuser/auth/userinfo'
    data = {
        "accessToken": access_token,
        "channelId": "202"
    }
    return get(url, data)

def get_all_page(token):
    url = 'https://w2ol.wo.cn/woportalapi/woportal/rewarding/getAllPage'
    data = {
        "pageId": "092adcce-fc3e-463f-8cc2-96b516b045c7",
        "channel": "Android",
        "appName": ""
    }
    return post(url, data, token)


def sign(policy_id, trail_id, task_id, rewarding_task_id, token):
    url = 'https://w2ol.wo.cn/woportalapi/woportal/rewarding/sign'
    data = {
        "policyId": policy_id,
        "trailId": trail_id,
        "taskId": task_id,
        "rewardingTaskId": rewarding_task_id,
        "disposable": "true",
    }
    return post(url, data, token)


def gift_list(token):
    url = 'https://w2ol.wo.cn/woportalapi/woportal/gift/giftList'
    data = {
        "pageNum": "1",
        "pageSize": "20",
        "consumptionStatus": ""
    }
    return post(url, data, token)


def get_prize(history_id, token):
    url = 'https://w2ol.wo.cn/woportalapi/woportal/gift/getPrize'
    data = {
        "historyId": history_id,
        "disposable": "true"
    }
    return post(url, data, token)


# 与当前相差天数
def get_diff_days_2_now(date_str):
    now_time = time.localtime(time.time())
    compare_time = time.strptime(date_str, "%Y-%m-%d")
    # 比较日期
    date1 = datetime.datetime(compare_time[0], compare_time[1], compare_time[2])
    date2 = datetime.datetime(now_time[0], now_time[1], now_time[2])
    diff_days = (date2 - date1).days
    return diff_days


def task(config):
    mobile = config['mobile']
    refresh_token = config['refreshToken']
    msg = ['开始执行: ' + mobile]
    ret = refresh(refresh_token)
    if ret['code'] != 200:
        msg.append('token失效')
        msg.append("----------------------------------------------")
        msg_list.extend(msg)
        return
    access_token = ret['data']['access_token']
    ret = user_info(access_token)
    token = ret['data']['authToken']
    ret = get_all_page(token)
    policy_id = ret['data']['continuationRewardingTask']['rewardingTaskInfo']['policyId']
    print("policyId: " + policy_id)
    for item in ret['data']['creditPolicies']:
        if item['policyId'] == policy_id:
            rewarding_task_id = item['creditRewardingTaskId']
            print("rewardingTaskId: " + rewarding_task_id)
            first_sign = item['tasks'][0]['effectiveFrom']
            print(first_sign)
            days = get_diff_days_2_now(first_sign.split(' ')[0])
            print("相差天数: " + str(days))
            msg.append("第 " + str(days + 1) + " 天")
            for item in ret['data']['getRewardingTask']['rewardingTaskInfos']:
                if item['policyId'] == policy_id:
                    rewarding_trails = item['rewardingTrails']
                    trail_id = rewarding_trails[days]['trailId']
                    task_id = rewarding_trails[days]['taskId']
                    print("trailId: " + trail_id)
                    print("taskId: " + task_id)
                    sign_ret = sign(policy_id, trail_id, task_id, rewarding_task_id, token)
                    msg.append(sign_ret['msg'])
    # 兑换奖品
    ret = gift_list(token)
    for item in ret['data']:
        if item['consumptionStatus'] == 0:
            result = get_prize(item['historyId'], token)
            msg.append(result['msg'])
    msg.append("----------------------------------------------")
    msg_list.extend(msg)


def main_handler(event, context):
    l = []
    for config in config_list:
        p = threading.Thread(target=task, args=(config,))
        l.append(p)
        p.start()
    for i in l:
        i.join()
    content = format_msg()
    if PUSH_PLUS_TOKEN != '':
        count = 0
        error_count = 0
        for item in msg_list:
            if '----------------------------------------------' == item:
                count = count + 1
            if 'token失效' == item:
                error_count = error_count + 1
        if error_count > 0:
            pushplus('沃门户任务Token失效请及时更新, 成功执行 ' + str(count), content)
        else:
            pushplus('沃门户任务, 成功执行 ' + str(count), content)
    print(content)
    return content


if __name__ == '__main__':
    main_handler('', '')
