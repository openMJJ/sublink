from flask import Blueprint,request,jsonify,render_template
from .model import *
import base64,yaml,urllib.parse,os,re
from flask_jwt_extended import jwt_required,get_jwt_identity,create_access_token,create_refresh_token
blue = Blueprint('blue',__name__)
path = os.path.dirname(os.path.abspath(__file__))
def clash_encode(subs): #clash编码
    clash_config = {
            'proxies':[],
            'proxy-groups': []
        }
    proxy_name_list = []
    # 解析节点信息并添加到 Clash 配置中
    for sub in subs:
        def decode_base64_if_possible(text):  # 判断是base64解码
            try:
                name = ''
                decoded_text = text
                if '#' in decoded_text:
                    name = '#' + decoded_text.split('#')[1]
                    decoded_text = decoded_text.split('#')[0]
                # print(text)
                # text = text.replace('-', '+').replace('_', '/') # 去除链接中的特殊字符和填充
                padding = 4 - (len(decoded_text) % 4)
                # 添加填充字符
                decoded_text += "=" * padding
                decoded_text = base64.b64decode(decoded_text).decode('utf-8')
                return decoded_text + name
            except:
                # 如果无法解码为Base64，则返回原始文本
                # print('不是base64')
                return text

        proxy_type = sub.node.split('://')[0]  # 节点类型
        proxy_test = sub.node.split('://')[1]  # 节点信息
        # print(proxy_type,proxy_test)
        if proxy_type == 'vless':
            url = urllib.parse.urlparse(proxy_test)
            query = urllib.parse.parse_qs(url.query)

            test = decode_base64_if_possible(url.path)  # 判断base64解码
            # print('原始数据'+str(url), '解码后'+str(test))
            proxy_name = urllib.parse.unquote(url.fragment)  # url解码
            print(test.split('@')[1])
            server_port = test.split('@')[1]
            # print('服务器端口:'+ str(server_port))
            server = server_port.split(':')[0]
            port_matches = re.findall(r':(\d+)', server_port)
            if port_matches:
                port = int(port_matches[-1])
            else:
                port = 0
            proxy = {
                'name': proxy_name,
                'type': proxy_type,
                'uuid': decode_base64_if_possible(test.split('@')[0]),
                'server': server,
                'client-fingerprint': 'chrome',
                'port': int(port),
                'network': query.get('type')[0],
                'udp':True,
                'skip-cert-verify': True,
                'tfo': False,
                'tls': True if query.get('sni') else False,
            }
            if query.get('fp'):
                proxy['client-fingerprint'] = query.get('fp')[0]
            if query.get('sni'):
                proxy['servername'] = query.get('sni')[0]
            if query.get('flow'):
                proxy['flow'] = query.get('flow')[0]
            if query.get('security')[0] == 'reality':
                proxy['reality-opts'] = {
                    'public-key': query.get('pbk')[0]
                }
                sid = query.get('sid')
                if sid:
                    proxy['reality-opts']['short-id'] = sid
            if query.get('type')[0] == 'ws':
                proxy['ws-opts'] = {
                    'path':query.get('path')[0]
                }
                host = query.get('host')
                if host:
                    proxy['ws-opts']['headers'] = {'Host': host[0]}
            clash_config['proxies'].append(proxy)
            proxy_name_list.append(proxy_name)
        if proxy_type == 'vmess':
            proxy_test = decode_base64_if_possible(proxy_test)  # 判断base64解码
            print(urllib.parse.urlparse(proxy_test))
            proxy = eval(proxy_test)
            proxys = {
                'name': proxy['ps'],
                'type': proxy_type,
                'uuid': proxy['id'],
                'server': proxy['add'],
                'port': int(proxy['port']),
                'client-fingerprint': 'chrome',
                'tfo': False,  # 是否启用 TCP Fast Open
                'udp': True,
                'skip-cert-verify': True,  # 是否跳过证书验证
                'alterId': proxy['aid'],
                'cipher': 'auto',
                'network': proxy['net'],  # 代理的网络类型
                'tls': True if proxy['tls'] == 'tls' else False
            }
            if proxy['net'] == 'ws':
                proxys.update(
                    {
                        'ws-opts': {
                            'path': proxy['path'],
                            'headers': {
                                'Host': proxy['add']
                            }
                        },
                    }
                )
            clash_config['proxies'].append(proxys)
            proxy_name_list.append(proxy['ps'])
        if proxy_type == 'ss':
            print(proxy_test.find('@'))
            if proxy_test.find('@') != -1:
                proxy_test = decode_base64_if_possible(proxy_test.split('@')[0]) + '@' + proxy_test.split('@')[1]
                # print('找到@')
            else:
                # print('没找到@')
                proxy_test = decode_base64_if_possible(proxy_test)  # 判断base64解码
            # print(proxy_test)

            name = proxy_test.split('#')[1]
            name = urllib.parse.unquote(name)
            proxy_test = proxy_test.split('#')[0]
            server_port = proxy_test.split('@')[1]
            server = ':'.join(server_port.split(':')[0:-1])
            print(server_port)
            port_matches = re.findall(r':(\d+)', server_port)
            if port_matches:
                port = int(port_matches[-1])
            else:
                port = 0
            test = decode_base64_if_possible(proxy_test.split('@')[0])
            print('混淆和密码：'+test)
            # 混淆和密码
            cipher = test.split(':')[0]
            password = test.split(':',maxsplit=1)[-1]
            proxy = {
                'name': name,
                'type': proxy_type,
                'server': server,
                'port': port,
                'cipher': cipher,
                'password': password,
                'client-fingerprint':'chrome',
                'tfo':False,
                'udp': True,
                'skip-cert-verify': True
            }
            clash_config['proxies'].append(proxy)
            proxy_name_list.append(name)
        if proxy_type == 'ssr':
            proxy_test = decode_base64_if_possible(proxy_test.replace('-', '+').replace('_', '/'))  # 判断base64解码
            url = urllib.parse.urlparse(proxy_test)
            # print(url)
            query = urllib.parse.parse_qs(url.query)
            name = query.get('remarks')[0]
            # print(name)
            name = decode_base64_if_possible(name)
            list = url.path.split(':')
            proxy = {
                'name': name,
                'type': proxy_type,
                'server': url.scheme,
                'port': int(list[0]),
                'protocol': list[1],
                'obfs': list[3],
                'password': decode_base64_if_possible(list[4].replace('/', '')),
                'udp': True,
                'skip-cert-verify': True
            }
            clash_config['proxies'].append(proxy)
            proxy_name_list.append(name)
        if proxy_type == 'trojan':
            name = urllib.parse.unquote(proxy_test.split('#')[1])
            proxy_test = proxy_test.split('#')[0]
            parurl = urllib.parse.urlparse(proxy_test)
            print(parurl)
            query = urllib.parse.parse_qs(parurl.query)
            print(proxy_test)
            print(query)
            password = proxy_test.split('@')[0]
            server_port = proxy_test.split('@')[1]
            server = server_port.split(':')[0]
            port_matches = re.findall(r':(\d+)', server_port)
            if port_matches:
                port = int(port_matches[-1])
            else:
                port = None
            proxy = {
                'name':name,
                'type':proxy_type,
                'server':server,
                'port':port,
                'password':password,
                'client-fingerprint': 'chrome',
                'udp':True,
                'skip-cert-verify': True
            }
            if query.get('fp'):
                proxy['client-fingerprint'] = query.get('fp')[0]
            if query.get('sni'):
                proxy['sni'] = query.get('sni')[0]
            if query.get('flow'):
                proxy['flow'] = query.get('flow')[0]
            if query.get('type'):
                proxy['network'] = query.get('type')[0]
                if query.get('type')[0] == 'ws':
                    proxy['ws-opts'] = {
                        'path': query.get('path')[0]
                    }
                    host = query.get('host')
                    if host:
                        proxy['ws-opts']['headers'] = {'Host': host[0]}

            clash_config['proxies'].append(proxy)
            proxy_name_list.append(name)
    # 将 Clash 配置转为 YAML 格式
    with open(path + '/db/clash.yaml', 'r') as file:
        # data = file.read()
        # print(file.read())
        data = yaml.safe_load(file)
        data['proxies'] = clash_config['proxies']
        proxy_groups = data.get('proxy-groups')

        for proxy_group in proxy_groups:
            for proxies in proxy_group['proxies']:
                if proxies == 'auto':  # 判断是否包含auto字符串
                    proxy_group['proxies'].remove('auto')
                    for name_list in proxy_name_list:
                        proxy_group['proxies'].append(name_list)
            # print(proxy_group['proxies'])
        # print(data)
        clash_config_yaml = yaml.dump(data, sort_keys=False, allow_unicode=True)
        return clash_config_yaml
@blue.route('/clash_config',methods=['POST']) #clash配置修改
@jwt_required()
def clash_config():
    if request.method == 'POST':
        data = request.get_json()
        index = data.get('index')
        # print(index)
        if index == 'read':
            with open(path + '/db/clash.yaml', 'r') as file:
                return jsonify({
                    'code':200,
                    'msg':file.read()
                })
        if index == 'save':
            text = data.get('text')
            if text == '':
                return jsonify({
                    'code': 400,
                    'msg': '不能为空'
                })
            with open(path + '/db/clash.yaml', 'w') as file:
                file.write(text)
                return jsonify({
                    'code':200,
                    'msg':'保存成功'
                })
@blue.route('/') #前台程序
def get_index():
    return render_template('index.html')
@blue.route('/login',methods=['POST'])
def get_login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'code': 404,
                'msg': '账号不存在'
            })
        if user.username == username and user.password == password:
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)
            return jsonify({
                'code': 200,
                'token':access_token,
                'refresh':refresh_token,
                'msg': '登录成功'
            })
        else:
            return jsonify({
                'code':404,
                'msg':'账号或者密码错误'
            })
@blue.route('/refresh' ,methods=['POST']) #刷新令牌
@jwt_required(refresh=True)
def get_refresh():
    if request.method == 'POST':
        current_user = get_jwt_identity()
        if current_user:
            token = create_access_token(current_user)
            return token
        else:
            return '没获取到'
@blue.route('/create_sub',methods=['POST']) # 新建节点
@jwt_required()
def get_create_sub():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        nodes = data.get('node')
        print(name,nodes)
        if Sub.query.filter_by(name=name).first():
            return jsonify({
                'code':400,
                'msg':'订阅名字已经存在'
            })
        for i in nodes:
            if len(i.split('|')) >= 2:
                node = i.split('|')[0]
                remarks = i.split('|')[1]
            else:
                node = i
                remarks = ''
            if node != '':
                sub = Sub(name=name, node=node, remarks=remarks)
                try:
                    db.session.add(sub)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    db.session.flush()
                    return jsonify({
                        'code':400,
                        'msg':'错误信息：' + str(e)
                    })
        return jsonify({
            'code':200,
            'msg':'创建成功'
        })
            # print('节点：' + node)
            # print('备注：' + remarks)
@blue.route('/get_subs',methods=['POST']) #获取所有的订阅
@jwt_required()
def get_subs():
    if request.method == 'POST':
        subs = Sub.query.all()
        data = []
        for sub in subs:
            item = {
                'name':sub.name,
                'node':sub.node,
                'remarks':sub.remarks
            }
            data.append(item)
        return jsonify(data)
@blue.route('/sub/<string:target>/<string:name>',methods=['GET']) #获取指定订阅
def get_sub(target,name):
    if request.method == 'GET':
        # print(name)
        name = base64.b64decode(name).decode('utf-8')
        # print(name)
        subs = Sub.query.filter_by(name=name).all()
        # print(target, name)
        if not subs:
            return jsonify({
                'code':400,
                'msg':'订阅不存在'
            })

        if target == 'clash':
            data = clash_encode(subs)
            return data
        if target == 'v2ray':
            data = []
            for sub in subs:
                data.append(sub.node)
            encoded_node = base64.b64encode('\n'.join(data).encode('utf-8')).decode('utf-8')
            return encoded_node
@blue.route('/del_sub/<string:name>',methods=['POST']) #删除指定订阅
@jwt_required()
def del_sub(name):
    if request.method == 'POST':
        subs =  Sub.query.filter_by(name=name).all()
        print(name,subs)
        if not subs:
            return jsonify({
                'code': 400,
                'msg': '不存在'
            })
        for sub in subs:
            try:
                db.session.delete(sub)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                db.session.flush()
                return jsonify({
                    'code': 400,
                    'msg': '错误信息:'+str(e)
                })
        return jsonify({
            'code': 200,
            'msg': '删除成功'
        })
@blue.route('/set_sub',methods=['POST']) # 修改节点
@jwt_required()
def get_set_sub():
    remarks = ''
    newNode = ''
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        newNodes = data.get('newNode')
        subs = Sub.query.filter_by(name=name).all()
        for sub in subs: # 删除表
            try:
                db.session.delete(sub)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                db.session.flush()
                return jsonify({
                    'code': 400,
                    'msg': '错误信息：' + str(e)
                })
        for i in newNodes: #创立表
            if len(i.split('|')) >= 2:
                newNode = i.split('|')[0]
                remarks = i.split('|')[1]
            else:
                newNode = i
                remarks = ''
            if newNode != '':
                sub = Sub(name=name, node=newNode, remarks=remarks)
                try:
                    db.session.add(sub)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    db.session.flush()
                    return jsonify({
                        'code':400,
                        'msg':'错误信息：' + str(e)
                    })
        return jsonify({
            'code':200,
            'msg':'修改成功'
        })
@blue.route('/set_user',methods=['POST']) # 修改账号信息
@jwt_required()
def get_set_user():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        newUserName = data.get('newUserName')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'code':400,
                'msg':'账号不正确'
            })
        user.username = newUserName
        user.password = password
        try:
            db.session.commit()
            return jsonify({
                'code': 200,
                'msg': '修改成功'
            })
        except Exception as e:
            db.session.rollback()
            db.session.flush()
            return jsonify({
                'code': 400,
                'msg': '错误信息:'+str(e)
            })