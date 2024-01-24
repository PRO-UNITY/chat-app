from django.urls import path
from authen.views import (
    UserSignUp,
    UserSignIn,
    UserProfile,
    change_password,
    RequestPasswordRestEmail,
    SetNewPasswordView,

)

urlpatterns = [
    path('signup', UserSignUp.as_view()),
    path('sigin', UserSignIn.as_view()),
    path('user', UserProfile.as_view()),
    path('password_change', change_password),
    path('password/reset', RequestPasswordRestEmail.as_view()),
    path('password/confirm', SetNewPasswordView.as_view()),
]