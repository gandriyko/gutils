# -*- coding: utf-8 -*-

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.translation import ugettext as _


def is_superuser(user):
    return user.is_superuser and user.is_authenticated


def is_staff(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_active:
        return False
    return user.is_staff


def is_user(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_active


def get_user(user):
    if not user or not user.is_authenticated:
        return None
    return user


def login_user(request, username, password, warning=True):
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            if user.force_logout:
                user.force_logout = False
                user.save()
            return user
        elif warning:
            messages.error(request, _('Your account has been disabled. Contact the manager for activation.'))
    return None


def logout_user(request):
    logout(request)
