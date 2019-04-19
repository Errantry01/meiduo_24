from rest_framework import serializers
import re

class ChangePwdSerializer(serializers.Serializer):
    """修改密码序列化器"""

    old_password = serializers.CharField(label='旧密码', min_length=8, max_length=20, write_only=True)
    password = serializers.CharField(label='密码1', min_length=8, max_length=20, write_only=True)
    password2 = serializers.CharField(label='密码2', min_length=8, max_length=20, write_only=True)

    def validate_password(self, value):
        if not re.match(r'\w{8,20}', value):
            raise serializers.ValidationError('密码输入不符合规则')
        return value

    def validate(self, attrs):
        password = attrs['password']
        password2 = attrs['password2']
        old_password = attrs['old_password']

        if password != password2:
            raise serializers.ValidationError('两次输入密码不一致')
        if password == old_password:
            raise serializers.ValidationError('不能使用原来的密码')
        return attrs