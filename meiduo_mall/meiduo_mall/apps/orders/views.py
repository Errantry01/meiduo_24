from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, ListAPIView

from goods.models import SKU
from orders.models import OrderGoods, OrderInfo
from .serializers import OrderSettlementSerializer, CommitOrderSerializer, UnCommentOrderSerializer, CommentOrderSerializer, OrderInfoSerializer



# Create your views here.

class OrderSettlementView(APIView):
    """去结算"""

    permission_classes = [IsAuthenticated]  # 指定权限,必须是登录用户才能访问此视图中的接口

    def get(self, request):

        # 创建redis连接对象
        redis_conn = get_redis_connection('cart')
        # 获取user对象
        user = request.user

        # 获取redis中hash和set两个数据
        cart_dict_redis = redis_conn.hgetall('cart_%d' % user.id)
        selected_ids = redis_conn.smembers('selected_%d' % user.id)

        # 定义一个字典用来保存勾选的商品及count
        cart_dict = {}  # {1: 2, 16: 1}
        # 把hash中那些勾选商品的sku_id和count取出来包装到一个新字典中
        for sku_id_bytes in selected_ids:
            cart_dict[int(sku_id_bytes)] = int(cart_dict_redis[sku_id_bytes])

        # 把勾选商品的sku模型再获取出来
        skus = SKU.objects.filter(id__in=cart_dict.keys())

        # 遍历skus 查询集取出一个一个的sku模型
        for sku in skus:
            # 给每个sku模型多定义一个count属性
            sku.count = cart_dict[sku.id]

        # 定义一运费
        freight = Decimal('10.00')

        data_dict = {'freight': freight, 'skus': skus}  # 序列化时,可以对 单个模型/查询集/列表/字典 都可以进行序列化器()
        # 创建序列化器进行序列化
        serializer = OrderSettlementSerializer(data_dict)

        return Response(serializer.data)


class CommitOrderView(CreateAPIView, ListAPIView):
    """保存订单"""

    # serializer_class = CommitOrderSerializer

    # 指定权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """重写指定查询集"""
        user = self.request.user
        orders = OrderInfo.objects.filter(user=user)
        return orders

    def get_serializer_class(self):
        """重写指定序列化器"""
        if self.request.method == 'POST':
            return CommitOrderSerializer
        else:
            return OrderInfoSerializer


class UnCommentOrderView(APIView):
    """待评论订单商品展示"""
    permission_classes = [IsAuthenticated]


    def get(self, request, order_id):

        user = request.user
        username = user.username

        try:
            order = OrderInfo.objects.filter(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM["UNCOMMENT"])
        except OrderInfo.DoesNotExist:
            return Response({'message':'订单信息有误'}, status=status.HTTP_400_BAD_REQUEST)


        order_goods = OrderGoods.objects.filter(is_commented=False, order=order)

        skus = []
        for order_good in order_goods:
            sku = order_good.sku
            skus.append(sku)

        # 创建序列化器进行序列化
        serializer = UnCommentOrderSerializer(data=skus, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data)

class CommentOrderView(APIView):
    """评论"""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        # 获取订单商品
        sku_id = request.data['sku']
        try:
            order_good = OrderGoods.objects.get(order_id=order_id, is_commented=False, sku_id=sku_id)
        except OrderGoods.DoesNotExist:
            return Response({'message':'订单信息有误'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建序列化器反序列化
        serializer = CommentOrderSerializer(instance=order_good,data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        # 更新模型
        order_good.comment = data['comment']
        order_good.score = data['score']
        order_good.is_anonymous = data['is_anonymous']
        order_good.sku_id = data['sku']
        order_good.is_comment = 1
        order_good.save()

        # 更新保存订单状态
        order = order_good.order
        order.status = OrderInfo.ORDER_STATUS_ENUM['FINISHED']
        order.save()
        return Response({'message': 'ok'}, status=status.HTTP_201_CREATED)
