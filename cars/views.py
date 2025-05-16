from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Car, CarImage, CarFeature, CarAvailability
from .forms import CarForm, CarImageForm, CarFeatureForm, CarAvailabilityForm

@login_required
def car_list(request):
    cars = Car.objects.filter(owner=request.user)
    return render(request, 'cars/car_list.html', {'cars': cars})

@login_required
def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    return render(request, 'cars/car_detail.html', {'car': car})

@login_required
def car_create(request):
    if request.method == 'POST':
        form = CarForm(request.POST)
        if form.is_valid():
            car = form.save(commit=False)
            car.owner = request.user
            car.save()
            messages.success(request, 'Car listing created successfully!')
            return redirect('car_detail', pk=car.pk)
    else:
        form = CarForm()
    
    return render(request, 'cars/car_form.html', {'form': form})

@login_required
def car_update(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = CarForm(request.POST, instance=car)
        if form.is_valid():
            form.save()
            messages.success(request, 'Car listing updated successfully!')
            return redirect('car_detail', pk=car.pk)
    else:
        form = CarForm(instance=car)
    
    return render(request, 'cars/car_form.html', {'form': form})

@login_required
def car_delete(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        car.delete()
        messages.success(request, 'Car listing deleted successfully!')
        return redirect('car_list')
    
    return render(request, 'cars/car_confirm_delete.html', {'car': car})
