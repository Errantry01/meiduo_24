from django.conf.urls import urlfrom oauth import viewsurlpatterns = [    # 拼接QQ登录url    url(r'^qq/authorization/$', views.QQOauthURLView.as_view()),    # QQ登录后的回调    url(r'^qq/user/$', views.QQAuthUserView.as_view()),    #拼接sina登录url    url(r'^sina/authorization/$', views.SinaURLView.as_view()),    #login sian call back    url(r'^', views.SinaOauthUserView.as_view()),]