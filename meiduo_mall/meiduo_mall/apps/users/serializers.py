from rest_framework import serializersimport refrom django_redis import get_redis_connectionfrom rest_framework_jwt.settings import api_settings# from users.utils import check_access_tokenfrom .models import User, Addressfrom celery_tasks.email.tasks import send_verify_emailfrom goods.models import SKU# from orders.models import OrderInfoclass CreateUserSerializer(serializers.ModelSerializer):    """注册序列化器"""    # 序列化器的所有字段: ['id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow']    # 需要校验的字段: ['username', 'password', 'password2', 'mobile', 'sms_code', 'allow']    # 模型中已存在的字段: ['id', 'username', 'password', 'mobile']    # 需要序列化的字段: ['id', 'username', 'mobile', 'token']    # 需要反序列化的字段: ['username', 'password', 'password2', 'mobile', 'sms_code', 'allow']    password2 = serializers.CharField(label='确认密码', write_only=True)    sms_code = serializers.CharField(label='验证码', write_only=True)    allow = serializers.CharField(label='同意协议', write_only=True)  # 'true'    token = serializers.CharField(label='token', read_only=True)    class Meta:        model = User  # 从User模型中映射序列化器字段        # fields = '__all__'        fields = ['id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow', 'token']        extra_kwargs = {  # 修改字段选项            'username': {                'min_length': 5,                'max_length': 20,                'error_messages': {  # 自定义校验出错后的错误信息提示                    'min_length': '仅允许5-20个字符的用户名',                    'max_length': '仅允许5-20个字符的用户名',                }            },            'password': {                'write_only': True,                'min_length': 8,                'max_length': 20,                'error_messages': {                    'min_length': '仅允许8-20个字符的密码',                    'max_length': '仅允许8-20个字符的密码',                }            }        }    def validate_mobile(self, value):        """单独校验手机号"""        if not re.match(r'1[3-9]\d{9}$', value):            raise serializers.ValidationError('手机号格式有误')        return value    def validate_allow(self, value):        """是否同意协议校验"""        if value != 'true':            raise serializers.ValidationError('请同意用户协议')        return value    def validate(self, attrs):        """校验密码两个是否相同"""        if attrs['password'] != attrs['password2']:            raise serializers.ValidationError('两个密码不一致')        # 校验验证码        redis_conn = get_redis_connection('verify_codes')        mobile = attrs['mobile']        real_sms_code = redis_conn.get('sms_%s' % mobile)        # 向redis存储数据时都是以字条串进行存储的,取出来后都是bytes类型 [bytes]        if real_sms_code is None or attrs['sms_code'] != real_sms_code.decode():            raise serializers.ValidationError('验证码错误')        return attrs    def create(self, validated_data):        # 把不需要存储的 password2, sms_code, allow 从字段中移除        del validated_data['password2']        del validated_data['sms_code']        del validated_data['allow']        # 把密码先取出来        password = validated_data.pop('password')        # 创建用户模型对象, 给模型中的 username和mobile属性赋值        user = User(**validated_data)        user.set_password(password)  # 把密码加密后再赋值给user的password属性        user.save()  # 存储到数据库        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER  # 引用jwt中的叫jwt_payload_handler函数(生成payload)        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 函数引用 生成jwt        payload = jwt_payload_handler(user)  # 根据user生成用户相关的载荷        token = jwt_encode_handler(payload)  # 传入载荷生成完整的jwt        user.token = token        return userclass UserDetailSerializer(serializers.ModelSerializer):    """用户详情序列化器"""    class Meta:        model = User        fields = ['id', 'username', 'mobile', 'email', 'email_active']class EmailSerializer(serializers.ModelSerializer):    """更新邮箱序列化器"""    class Meta:        model = User        fields = ['id', 'email']        extra_kwargs = {            'email': {                'required': True            }        }    def update(self, instance, validated_data):        """重写此方法目录不是为了修改,而是借用此时机 发激活邮箱"""        instance.email = validated_data.get('email')        instance.save()        # 将来需要在此继续写发邮箱的功能        # send_mail()        # http://www.meiduo.site:8080/success_verify_email.html?token=1        verify_url = instance.generate_email_verify_url()        send_verify_email.delay(instance.email, verify_url=verify_url)        return instanceclass UserAddressSerializer(serializers.ModelSerializer):    """    用户地址序列化器    """    province = serializers.StringRelatedField(read_only=True)    city = serializers.StringRelatedField(read_only=True)    district = serializers.StringRelatedField(read_only=True)    province_id = serializers.IntegerField(label='省ID', required=True)    city_id = serializers.IntegerField(label='市ID', required=True)    district_id = serializers.IntegerField(label='区ID', required=True)    class Meta:        model = Address        exclude = ('user', 'is_deleted', 'create_time', 'update_time')    def validate_mobile(self, value):        """        验证手机号        """        if not re.match(r'^1[3-9]\d{9}$', value):            raise serializers.ValidationError('手机号格式错误')        return value    def create(self, validated_data):        user = self.context['request'].user  # 获取用户模型对象        validated_data['user'] = user  # 将用户模型保存到字典中        return Address.objects.create(**validated_data)class AddressTitleSerializer(serializers.ModelSerializer):    """    地址标题    """    class Meta:        model = Address        fields = ('title',)class UserBrowserHistorySerializer(serializers.Serializer):    """保存商品浏览记录序列化器"""    sku_id = serializers.IntegerField(label='商品sku_id', min_value=1)    def validate_sku_id(self, value):        """单独对sku_id进行校验"""        try:            SKU.objects.get(id=value)        except SKU.DoesNotExist:            raise serializers.ValidationError('sku_id 不存在')        return value    def create(self, validated_data):        sku_id = validated_data.get('sku_id')        # 获取当前的用户模型对象        user = self.context['request'].user        # 创建redis连接对象        redis_conn = get_redis_connection('history')        # 创建redis 管道        pl = redis_conn.pipeline()        # 先去重        pl.lrem('history_%d' % user.id, 0, sku_id)        # 再添加到列表的开头        pl.lpush('history_%d' % user.id, sku_id)        # 再截取列表中前5个元素        pl.ltrim('history_%d' % user.id, 0, 4)        # 执行管道        pl.execute()        return validated_dataclass SKUSerializer(serializers.ModelSerializer):    """sku商品序列化器"""    class Meta:        model = SKU        fields = ['id', 'name', 'price', 'default_image_url', 'comments']# class UpdatePasswordSerializer(serializers.Serializer):#     """设置密码序列化器"""#     access_token = serializers.CharField(label='操作凭证', write_only=True)#     password2 = serializers.CharField(label='重复密码', write_only=True)#     password = serializers.CharField(label='密码')##     class Meta:#         model = User#         fields = ['password', 'password2', 'access_token']##         # 对字段进行额外校验#         extra_kwargs = {#             'password': {#                 'write_only': True,#                 'max_length': 20,#                 'min_length': 8,#                 'error_messages': {#                     'max_length': '密码须为8到20位',#                     'min_length': '密码须为8到20位'#                 }#             }#         }##     def validate(self, attrs):#         # 验证两次密码是否一致#         if attrs['password'] != attrs['password2']:#             raise serializers.ValidationError('两次密码不一致')##         # 验证access_token是否有效#         result = check_access_token(attrs.get('access_token'))#         if not result:#             raise serializers.ValidationError('操作超时')##         return attrs