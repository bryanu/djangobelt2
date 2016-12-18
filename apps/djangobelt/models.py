from __future__ import unicode_literals
from django.contrib import messages
from django.db.models import Count
from django.db import models
import re
import bcrypt
import pickle
import datetime

class UserManager(models.Manager):

  def login(self, request, email, password):
    if 'formdata' in request.session:
      request.session.pop('formdata')
    try:
      user = User.objects.get(username=email)
    except self.model.DoesNotExist:
      messages.error(request, "email/password combination is incorrect!", extra_tags="login")
      return False
    pwcheck = bcrypt.hashpw(password.encode('utf-8'), user.password.encode('utf-8'))
    if pwcheck != user.password:
      request.session['loggedin'] = False
      request.session['userid']   = 0
      request.session['username'] = ""
      return False
    request.session['loggedin'] = True
    request.session['userid']   = user.id
    request.session['username'] = user.name
    return True


  def logout(self, request):
    if not 'loggedin' in request.session:
      return False
    request.session.pop('loggedin')
    request.session.pop('userid')
    request.session.pop('username')
    return True

  
  def register(self, request, reg_info):
    errors = False
    if not re.match(r"[a-zA-Z]{2,}",reg_info['name']): # Alpha ONLY and 2 characters min.
      messages.error(request, "Name: Must be at least 2 characters long.", extra_tags="register")
      errors = True
    if not re.match(r"[a-zA-Z]{2,}",reg_info['alias']): # Alpha ONLY and 2 characters min.
      messages.error(request, "Alias: Must be at least 2 characters long.", extra_tags="register")
      errors = True
    if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)",reg_info['email']): # Valid email address
      messages.error(request, "Email: Must be a valid email address.", extra_tags="register")
      errors = True
    if not re.match(r"[a-zA-Z0-9]{8,}",reg_info['password']): # Alpha-Numberic - 8 characters min.
      messages.error(request, "Password: Must be at least 8 characters long, and only alpha-numberic characters.", extra_tags="register")
      errors = True
    if reg_info['password'] != reg_info['password2']: # Passwords must match
      messages.error(request, "Confirmation Password: Must match password entered.", extra_tags="register")
      errors = True
    if not re.match(r"[1,2]\d\d\d[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",reg_info['birthdate']): # Valid Date
      messages.error(request, "Please enter a valid Birthday (mm/dd/yyyy)", extra_tags="register")
      errors = True
    if errors:
      return False
    securepass = bcrypt.hashpw(reg_info['password'].encode('utf-8'), bcrypt.gensalt())
    user = User.objects.create(
      name      = reg_info['name'],
      alias     = reg_info['alias'],
      username  = reg_info['email'],
      birthdate = reg_info['birthdate'],
      password  = securepass
    )
    user.save()
    if user.id != None:
      request.session['loggedin'] = True
      request.session['userid']   = user.id
      request.session['username'] = reg_info['name']
      return True
    else:
      return False

class User(models.Model):
  name       = models.CharField(max_length=45)
  alias      = models.CharField(max_length=45)
  username   = models.CharField(max_length=60)
  password   = models.CharField(max_length=100)
  birthdate  = models.DateTimeField(auto_now_add=False)
  created_at = models.DateTimeField(auto_now_add = True)
  updated_at = models.DateTimeField(auto_now = True)
  objects    = UserManager()

class PokeManager(models.Manager):
  
  def poke(self, user_id, poked_id):
    user       = User.objects.get(id = user_id)
    poked_user = User.objects.get(id = poked_id)
    self.create(PokedUser=poked_user, PokedBy=user)
    return True
  
  def pokeinfo(self, request, user_id):

      ## Get object of logged-in user
      # SQL = "SELECT * FROM User WHERE id = %id%;"
    user = User.objects.get(id=user_id)

      ## List all users who logged-in user can poke, exclude logged-in user
      # SQL = "SELECT * FROM User WHERE id != %id%;"
    otherusers = User.objects.all()
    otherusers = otherusers.exclude(id=user_id)  
    
      # SELECT *, COUNT(djangobelt_poke.id) AS total_pokes FROM djangobelt_user 
      # LEFT OUTER JOIN djangobelt_poke ON (djangobelt_user.id = djangobelt_poke.PokedUser_id) 
      # WHERE NOT (djangobelt_user.id = %id%) GROUP BY djangobelt_user.id
    pokes = otherusers.annotate(total_pokes=Count('poked_user'))

      # SQL = "SELECT * FROM Poke WHERE poked_user = %id%;"
    mypokes = Poke.objects.filter(PokedUser = user)
      
      ## Count the number of people who poked you
      # SQL = "SELECT count(*) FROM User WHERE PokedBy in (SELECT id FROM Poke WHERE poked_user = %id%) GROUP BY name;"
    mypokes_count = otherusers.filter(poked_by__in=mypokes)
    mypokes_count = mypokes_count.count()
    
      ## Show list of users who poked you and how many times they poked you, order by poke count (Descending)
      # SELECT *, COUNT(djangobelt_user.id) AS total_pokes FROM djangobelt_user 
      # INNER JOIN djangobelt_poke ON (djangobelt_user.id = djangobelt_poke.PokedBy_id) 
      # WHERE (NOT (djangobelt_user.id = %id%) AND djangobelt_poke.id IN (SELECT djangobelt_poke.id FROM djangobelt_poke WHERE djangobelt_poke.PokedUser_id = %id%)) 
      # GROUP BY djangobelt_user.id ORDER BY total_pokes DESC
    mypokes_userlist = otherusers.filter(poked_by__in=mypokes)
    mypokes_userlist = mypokes_userlist.annotate(total_pokes=Count('id'))
    mypokes_userlist = mypokes_userlist.order_by('-total_pokes')
    
    context={
      'users'           : pokes, 
      'mypokes_count'   : mypokes_count, 
      'mypokes_userlist': mypokes_userlist
    }
    
    request.session['pokeinfo'] = pickle.dumps(context)
    
    return True
  
class Poke(models.Model):
  PokedBy      = models.ForeignKey(User, related_name='poked_by')
  PokedUser    = models.ForeignKey(User, related_name='poked_user')
  created_at   = models.DateField(auto_now_add=True)
  updated_at   = models.DateTimeField(auto_now=True)
  objects = PokeManager()
  