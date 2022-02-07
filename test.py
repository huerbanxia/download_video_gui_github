import requests

if __name__ == '__main__':
    session = requests.session()

    # session.cookies['show_adult'] = '1'

    data = {
        'name': '877368420@qq.com',
        'pass': 'Z877368420',
        'form_id': 'user_login',
        'form_build_id': 'form-ZZ6KGg8LNw3Gkwl3ikNDKt8quKvULW6nBoK9c7_E6eA',
        'antibot_key': '13ac4273dc853636a2413f2d70b438ff',
    }

    body = session.post('https://www.iwara.tv/user/login?language=zh-hans', data)

    # print(body.text)

    video_list_html = session.get('https://ecchi.iwara.tv/subscriptions')

    print(video_list_html.text)

    # resp = session.get('https://ecchi.iwara.tv/subscriptions')
    #
    # print(resp.text)



