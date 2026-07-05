from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required

def room(request,room_name):
    return render(request,'chatie/room.html',{
        'room_name':room_name
    })

def login(request):
    if request.method == 'POST':
        username=request.POST['username']
        password=request.POST['password']
        user=authenticate(request,username=username,password=password)
        if user is not None:
            login(request,user)
            return redirect('inbox')
        else:
            return render(request,'chatie/login.html',{'error':'Invalid Credentials'})
        
    return render(request,'chatie/login.html')    

def logout_view(request):
    logout(request)
    return redirect('login')    


