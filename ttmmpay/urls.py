"""
URL configuration for ttmmpay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from bill import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.login_view, name='home'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.login_view, name='logout'),  # temp

    path('dashboard/', views.dashboard, name='dashboard'),

    path('bill/<int:id>/', views.bill_detail, name='bill_detail'),

    path('ttmmpage/', views.ttmmpage, name='ttmmpage'),

    path("save-bill/", views.save_bill, name="save_bill"),
    path('summary/<int:bill_id>/', views.summary_page, name='summary_bill'),
    path('delete_bill/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    
    ]