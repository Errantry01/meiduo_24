import re

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ChangePwdView(APIView):
    """修改密码视图"""
    # 权限设置  登录用户
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        user = request.user
        mobile = request.user.mobile
        old_password = request.data.get('old_password')
        # if old_password != user.password:
        if not user.check_password(old_password):
            return Response({'message': '密码输入错误'}, status=status.HTTP_400_BAD_REQUEST)
        password = request.data.get('password')
        password2 = request.data.get('password')
        if password == mobile:
            return Response({'message': '不能使用手机号作为密码'}, status=status.HTTP_400_BAD_REQUEST)
        if password == old_password:
            return Response({'message': '不能使用近期使用过的密码'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.match(r'\w{8,20}', password):
            return Response({'message': '密码不符合规范'}, status=status.HTTP_400_BAD_REQUEST)
        if password != password2:
            return Response({'message': '二次输入密码不一致'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save()
        return Response({'message': '密码修改成功'}, status=status.HTTP_201_CREATED)


