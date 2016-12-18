from django.shortcuts import render, redirect
from .models import *
import pickle

def index(request):
  if 'loggedin' in request.session:
    return redirect("/dashboard")
  else:
    return render(request, "djangobelt/index.html")
  
def login(request):
  if request.POST:
    loggedin = User.objects.login(request, request.POST["email"], request.POST["password"])
  return redirect(index)

def logout(request):
  User.objects.logout(request)
  return redirect(index)

def register(request):
  if not request.POST:
    return redirect(index)
  success = User.objects.register(request, request.POST)
  if not success:
    formdata = request.POST.copy()
    formdata.pop("password")
    formdata.pop("password2")
    request.session["formdata"] = formdata
    return redirect(index)
  return redirect("/dashboard")

def dashboard(request):
  return render(request, "djangobelt/dashboard.html")

def pokes(request):
  if 'loggedin' not in request.session:
    return redirect(index)
  Poke.objects.pokeinfo(request, request.session['userid'])
  return render(request, 'djangobelt/dashboard.html', pickle.loads(request.session['pokeinfo']))

def pokeUser(request, id):
  Poke.objects.poke(request.session['userid'], id)
  return redirect('/dashboard')
