from django.urls import path
from . import views

urlpatterns = [
    # Main pages

    path('',views.land, name='land'),
    path('home/', views.home, name='home'),
    path('autocomplete-suggestions/', views.autocomplete_suggestions, name='autocomplete_suggestions'),
    path('smart-autocomplete/', views.smart_autocomplete, name='smart_autocomplete'),
    path('user-search-history/', views.user_search_history, name='user_search_history'),
    path('search/', views.home, name='search'), 
    path('browse/', views.home, name='browse'),
    path('about/', views.home, name='about'),
    path('profile/', views.home, name='profile'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # path('firebase-login/', views.firebase_login, name='firebase_login'),
    path('bookmark-lists/', views.view_bookmark_lists, name='view_bookmark_lists'),
    path('bookmark-lists/create/', views.create_bookmark_list, name='create_bookmark_list'),
    path('bookmark-lists/<int:list_id>/add/', views.add_bookmark, name='add_bookmark'),
]