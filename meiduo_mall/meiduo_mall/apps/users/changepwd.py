import re

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# from django_redis import get_redis_connection
# from users.serializer import ChangePwdSerializer


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


#
# class ChangePwdViews(APIView):
#     # 权限设置  登录用户
#     permission_classes = [IsAuthenticated]
#     # 指定序列化器
#     serializer_class = ChangePwdSerializer
#
#     def put(self, request, *args, **kwargs):
#         serializer = ChangePwdSerializer(data=request.data)
#         old_password = request.data.get('old_password')
#         password = request.data.get('password')
#         # 查询用户
#         user = self.request.user
#
#         # 创建redis连接
#         redis_conn = get_redis_connection('verify_codes')
#         error_count = redis_conn.get("error_count_%s" % user.mobile)
#         if error_count:
#             error_count = int(error_count)
#             if error_count >= 3:
#                 return Response({'message': '忘记原密码? 马上去找回吧.'}, status=status.HTTP_400_BAD_REQUEST)
#         else:
#             error_count = 0
#
#         if not user.check_password(old_password):
#             remain = 3
#             error_count += 1
#             remain -= error_count
#             if remain < 0:
#                 return Response({'message': '忘记原密码? 去找回密码吧.'}, status=status.HTTP_400_BAD_REQUEST)
#             redis_conn.setex("error_count_%s" % user.mobile, 300, error_count)
#             return Response({'message': '原密码错误, 您还有%s次修改机会,好好想想吧' % remain}, status=status.HTTP_400_BAD_REQUEST)
#         mobile = request.user.mobile
#         if password == mobile:
#             return Response({'message': '不能使用手机号作为密码'}, status=status.HTTP_400_BAD_REQUEST)
#         serializer.is_valid(raise_exception=True)
#         user.set_password(password)
#         user.save()
#         return Response({
#             'message': '修改密码成功'
#         }, status=status.HTTP_201_CREATED)