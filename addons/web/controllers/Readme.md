#Api create account:

- new_user={
    'user_name': 'lee_ann_wu',
    'first_name':'wu',
    'last_name':'le',
    'role': 1
  }
- user = AuthSsoApi.create_user(self,request.session.access_token,'en',new_user)

#Api get role:

- role  = AuthSsoApi.get(self,request.session.access_token,'vi',"/user/" + username+ "/role")

#Api login:
- data = AuthSsoApi.login_sso(self,username, password)
- request.session.access_token = json.loads(data.decode("utf-8"))['access_token']

#Api reset password:

- user = AuthSsoApi.reset_password(self,request.session.access_token,'en',username)

#Api active:

- user = AuthSsoApi.active(self,request.session.access_token,'en',username)

#Api deactive:

- user = AuthSsoApi.deactive(self,request.session.access_token,'en',username)

#Api update infomation:

