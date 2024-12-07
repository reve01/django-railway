import json
from django.shortcuts import render
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.db import IntegrityError

from .models import User, Owner, Pet, Appointment, Comment, Galeria, Notification
from .forms import PetForm, AppointmentForm
from .utilities import load_preview_dict
from django.http import JsonResponse

from django.utils.timezone import now
from booking.models import Notification
from datetime import timedelta
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import redirect
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST

from celery import shared_task

from django.views.decorators.csrf import csrf_exempt

from django.core.paginator import Paginator



def inicio(request):
        # Only show comments that are approved by staff and get 10 of them randomly (if there are more than 10)
    comments = Comment.objects.filter(
        approved=True).order_by('?')[:10]

    # Add new comment
    if request.method == "POST":
        data = json.loads(request.body)
        comment = data["comment"]
        username = data["username"]
        user = User.objects.get(username=username)

        if user is None:
            return JsonResponse({
                "message": "Login Required"
            }, status=403)

        Comment.objects.create(user=user, content=comment)
        return JsonResponse({
            "message": "Thank you for your comment!"
        }, status=200)

    else:
        return render(request, 'booking/inicio.html', {"comments": comments})

# Vista para la página de contacto
def contacto(request):
    return render(request, 'booking/contacto.html')  # Rendeiza la plantilla 'contacto.html'

# Vista para la página de servicios
def servicios(request):
    return render(request, 'booking/servicios.html')  # Rendeiza la plantilla 'servicios.html'

# Vista para procesar el formulario de contacto (vacío en este caso)
def enviar_contacto(request):
    if request.method == 'POST':  # Si la solicitud es POST, procesar los datos del formulario
        pass  # Aquí iría la lógica para procesar el formulario
    return render(request, 'booking/contacto.html')  # Rendeiza de nuevo la plantilla 'contacto.html'

def galeria(request):
    galerias = Galeria.objects.all()
    paginator = Paginator(galerias, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "booking/galeria.html", {"page_obj": page_obj})
   

# Create your views here.



def services(request):
    return render(request, 'booking/services.html')


def login_view(request):
    if request.method == "POST":
        next = request.POST['next']
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        
        # Check if authentication successful
        if user is not None:
            login(request, user)
            if next == "":
                return HttpResponseRedirect(reverse('profile'))
            else:
                return HttpResponseRedirect(next)

        else:
            messages.error(request, "Invalid username and/or password.")
            return render(request, "booking/login.html", {
                'next': next,
            })
    else:
        return render(request, 'booking/login.html')


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("inicio"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        phone = request.POST["phone"]
        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            messages.error(request, "Passwords do not match.")
            return HttpResponseRedirect(reverse("register"))
            
        elif first_name == "" or last_name == "":
            messages.error(request, "Please fill in your name.")
            return HttpResponseRedirect(reverse("register"))
        
        elif password == "":
            messages.error(request, "Please input a password.")
            return HttpResponseRedirect(reverse("register"))

        elif len(password) < 6:
            messages.error(
                request, "Password must contain at least 6 characters.")
            return HttpResponseRedirect(reverse("register"))

        if phone and (len(phone) != 10 or not phone.isnumeric()):
            messages.error(
                request, "Phone number invalid. Must be 10 digits and in format: 9051234567")
            return HttpResponseRedirect(reverse("register"))

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            Owner.objects.create(user=user, phone=phone)

        except IntegrityError:
            messages.error(
                request, "Username already taken.")
            return HttpResponseRedirect(reverse("register"))
        login(request, user)
        return HttpResponseRedirect(reverse("profile"))
    else:
        return render(request, 'booking/register.html')



@login_required(login_url='/login')
def profile(request):
    today = datetime.today()

    owner = Owner.objects.get(user=request.user)
    pets = Pet.objects.filter(owner=owner)
    booking = Appointment.objects.filter(user=owner, date__gte=today).exclude(
        date=today, time__lt=today.now().hour).order_by('date', 'time')

    # Obtener las notificaciones no leídas
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')

    if request.method == "POST":
        form = PetForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            size = form.cleaned_data["size"]
            date_of_birth = form.cleaned_data["date_of_birth"]
            breed = form.cleaned_data["breed"].title()
            Pet.objects.create(owner=owner, name=name, size=size,
                               date_of_birth=date_of_birth, breed=breed)
            return HttpResponseRedirect(reverse("profile"))
        else:
            return render(request, "booking/profile.html", {
                "petform": form,
                "owner": owner,
                "pets": pets,
                "booking": booking,
                "notifications": notifications,
                "today": today
            })

    elif request.method == "DELETE":
        data = json.loads(request.body)
        pet_id = data["pet"]
        pet = Pet.objects.filter(owner=owner, id=pet_id)
        pet.delete()
        return HttpResponse(status=204)

    elif request.method == 'PUT':
        data = json.loads(request.body)
        field = data['field']
        value = data['value']
        if field == 'phone':
            if len(value) == 10 and value.isnumeric():
                owner.phone = value
                owner.save()
                return HttpResponse(status=204)
            else:
                return JsonResponse({"message": "Phone number should have 10 digits and numbers only."}, status=400)
        elif field == 'email':
            if '@' in value:
                user = User.objects.get(username=request.user)
                user.email = value
                user.save()
                return HttpResponse(status=204)
            else:
                return JsonResponse({"message": "Please input a valid email"}, status=400)

    else:
        bookform = AppointmentForm()
        bookform.fields["dog"].queryset = Pet.objects.filter(owner=owner)

        return render(request, "booking/profile.html", {
            "petform": PetForm(),
            "owner": owner,
            "pets": pets,
            "booking": booking,
            "notifications": notifications,
            "today": today,
            "bookform": bookform,
        })



@login_required(login_url='/login')
def change_password(request):

    if request.method == "POST":
        old_password = request.POST["old_password"]
        new_password = request.POST["new_password"]
        confirmation = request.POST["confirmation"]
        user_record = User.objects.get(username=request.user)
        if len(new_password) < 6:
            messages.error(
                request, 'Password must contain at least 6 characters.')
            return HttpResponseRedirect(reverse('changepassword'))
        elif new_password != confirmation:
            messages.error(
                request, 'New password and confirmation do not match.')
            return HttpResponseRedirect(reverse('changepassword'))

        elif old_password == new_password:
            messages.error(
                request, 'Old and new passwords cannot be the same.')
            return HttpResponseRedirect(reverse('changepassword'))

        if old_password and new_password and (new_password == confirmation) and (old_password != new_password):
            if user_record.check_password(old_password):
                user_record.set_password(new_password)
                user_record.save()
                messages.success(request, 'Password has been updated, please login with your new password.')
                return HttpResponseRedirect(reverse('login'))
            else:
                messages.error(
                    request, 'Old password is incorrect.')
                return HttpResponseRedirect(reverse('changepassword'))

    else:
        return render(request, 'booking/changepassword.html')



@login_required(login_url='/login')
def booking(request):
    # Obtener notificaciones no leídas
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    
    # preview slot table
    today = datetime.today().date()
    # Obtiene la fecha actual del sistema.

    date_list = [today + timedelta(days=x) for x in range(7)]
    # Crea una lista de las fechas para los próximos 7 días a partir de hoy.

    appointments = Appointment.objects.filter(
        date__range=[date_list[0], date_list[-1]])
    # Filtra las citas que estén en el rango de fechas creado anteriormente (próximos 7 días).

    slot_dict = {}
    # Inicializa un diccionario para almacenar los horarios disponibles para cada día.

    for date in date_list:
        if date.weekday() == 7:
            slot_dict[date] = 'Closed'
        else:
            time_list = [10, 13, 15]
            # Define una lista con los posibles horarios para las citas (10 AM, 1 PM, 3 PM).

            time_slot_list = list(Appointment.objects.filter(
                date=date).values_list('time', flat=True))
            # Obtiene una lista de todas las horas ya reservadas para ese día.

            for i in range(len(time_list)):
                # Verifica si la hora ya está ocupada o si ha pasado en el día actual
                if time_list[i] in time_slot_list or (date == today and datetime.now().hour >= time_list[i]):
                    time_list[i] = None
                # Marca la hora como 'None' si está ocupada o si ha pasado en el día actual.

            slot_dict[date] = [t for t in time_list if t is not None]
           
            # Asigna los horarios disponibles para cada fecha, eliminando los que están ocupados o pasados.

    # users should only be able to choose the pets they own
    bookform = AppointmentForm()
    # Crea una instancia del formulario de cita.

    owner = Owner.objects.get(user__username=request.user)
    # Obtiene el objeto `Owner` correspondiente al usuario actual.

    bookform.fields["dog"].queryset = Pet.objects.filter(owner=owner)
    # Filtra el queryset del campo "dog" del formulario para que solo muestre las mascotas del propietario.

    if request.method == "POST":
        owner = Owner.objects.get(user=request.user)
        # Obtiene nuevamente al propietario, ya que se utilizará en varias partes del bloque `POST`.

        if request.POST.get("book"):
            bookform = AppointmentForm(request.POST)
            # Crea una nueva instancia del formulario con los datos del formulario enviado.

            if bookform.is_valid():
                date = bookform.cleaned_data["date"]
                time = bookform.cleaned_data["time"]
                available = Appointment.objects.filter(date=date, time=time)
                # Verifica si ya existe una cita para el día y hora solicitados.

                if available.count() == 0:
                    dog = bookform.cleaned_data["dog"]
                    service = bookform.cleaned_data["service"]
                    add_ons = bookform.cleaned_data["add_ons"]
                    # Obtiene los datos del formulario para crear una nueva cita.

                    Appointment.objects.create(
                        user=owner, dog=dog, date=date, time=time, service=service, add_ons=add_ons
                    )
                    # Crea la nueva cita en la base de datos.

                    return HttpResponseRedirect(reverse('profile'))
                    # Redirige al perfil del usuario después de realizar la reserva.

            else:  # Si el formulario de reserva no es válido
                bookform.fields["dog"].queryset = Pet.objects.filter(owner=owner)
                # Si el formulario es inválido, recarga el formulario y los datos de las mascotas disponibles.

                return render(request, 'booking/booking.html', {
                    "form": bookform,
                    "petform": PetForm(),
                    "date_list": slot_dict,
                    "notifications": notifications,  # Añade las notificaciones aquí
                })
                # Renderiza la plantilla de reservas con el formulario de citas, el formulario de mascotas y las fechas disponibles.

        elif request.POST.get('add_pet'):
            petform = PetForm(request.POST)
            # Crea una instancia del formulario de mascota con los datos del formulario enviado.

            if petform.is_valid():
                name = petform.cleaned_data["name"]
                size = petform.cleaned_data["size"]
                date_of_birth = petform.cleaned_data["date_of_birth"]
                breed = petform.cleaned_data["breed"].title()
                # Obtiene los datos del formulario de mascota y los procesa.

                Pet.objects.create(owner=owner, name=name, size=size,
                                   date_of_birth=date_of_birth, breed=breed)
                # Crea una nueva mascota en la base de datos.

                messages.success(request, f"{name} is added successfully")
                # Muestra un mensaje de éxito informando que la mascota se ha añadido correctamente.

                return render(request, 'booking/booking.html', {
                    "form": bookform,
                    "petform": PetForm(),
                    "date_list": slot_dict,
                    "notifications": notifications,  # Añade las notificaciones aquí
                })
                # Renderiza la plantilla de reservas después de agregar la mascota.

            else:
                return render(request, "booking/booking.html", {
                    "form": bookform,
                    "petform": petform,
                    "date_list": slot_dict,
                    "notifications": notifications,  # Añade las notificaciones aquí
                })
                # Renderiza la plantilla con el formulario de citas, el formulario de mascotas y las fechas disponibles, pero con errores en el formulario de mascota.

    else:  # Si la solicitud es un GET (cuando se carga la página inicialmente)
        return render(request, 'booking/booking.html', {
            "form": bookform,
            "petform": PetForm(),
            "date_list": slot_dict,
            "notifications": notifications,  # Añade las notificaciones aquí
        })
        # Renderiza la plantilla de reservas con los formularios de cita y mascota vacíos y las fechas disponibles.




@login_required(login_url='/login')
# Decora la vista para asegurar que solo los usuarios autenticados puedan acceder a ella. Si no están logueados, serán redirigidos a la página de login.

def appointment(request, id):
    try:
        appointment = Appointment.objects.get(pk=id)
        # Intenta obtener la cita con el ID especificado. Si no existe, se lanza una excepción.
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Record not found."}, status=404)
        # Si no se encuentra la cita, devuelve un error 404 (no encontrado) con un mensaje de error.

    owner = Owner.objects.get(user=request.user)
    # Obtiene el objeto 'Owner' correspondiente al usuario actual, que es el dueño de una mascota o de la cita.

    if owner.id == appointment.user.id:
        # Verifica si el usuario que hace la solicitud es el propietario de la cita. Si no es así, devuelve un error 403 (prohibido).

        # Si el método de la solicitud es DELETE, se desea cancelar la cita.
        if request.method == "DELETE":
            if owner.id == appointment.user.id:
                # Verifica nuevamente que el usuario es el propietario de la cita antes de eliminarla.
                data = json.loads(request.body)
                # Carga el cuerpo de la solicitud para obtener los datos en formato JSON.
                id = data["id"]
                # Extrae el ID de la cita desde los datos cargados.

                appointment.delete()
                # Elimina la cita de la base de datos.
                return HttpResponse(status=204)
                # Devuelve una respuesta vacía con el código de estado 204, que indica que la operación fue exitosa pero no hay contenido.
            else:
                return JsonResponse({'error': 'You can only delete your own appointments'}, status=403)
                # Si el usuario no es el propietario de la cita, se devuelve un error 403 (prohibido).

        # Si el método de la solicitud es PUT, se desea editar la cita.
        elif request.method == 'PUT':
            data = json.loads(request.body)
            # Carga el cuerpo de la solicitud para obtener los datos en formato JSON.
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            # Convierte la fecha de la cita (que se recibe como string) en un objeto de tipo fecha (datetime.date).
            time = data["time"]
            # Extrae la hora de la cita desde los datos.
            dog = data["dog"]
            # Extrae el ID del perro asociado a la cita.

            if date < datetime.today().date() or (date == datetime.today().date() and time < str(datetime.now().hour)):
                return JsonResponse({'error': 'Cannot change to a time slot in the past'}, status=400)
                # Verifica que la nueva fecha y hora no sean en el pasado. Si lo son, devuelve un error 400 (solicitud incorrecta).

            elif date.weekday() == 0:
                return JsonResponse({'error': 'Sorry, we are closed on Monday'}, status=400)
                # Verifica si la cita es para un lunes (día 0 de la semana), ya que la tienda está cerrada ese día. Devuelve un error si es el caso.

            # Verifica si el cliente está intentando cambiar la fecha y hora de la cita
            available = Appointment.objects.filter(
                date=date, time=time).exclude(id=id)
            # Consulta si ya existe una cita en la misma fecha y hora, excluyendo la cita actual (si la está editando).

            if available.count() == 0:
                # Si no hay citas en la misma fecha y hora, se puede proceder con la actualización.
                appointment.dog = Pet.objects.get(pk=dog)
                # Asocia el perro correspondiente a la cita.
                appointment.service = data["service"]
                # Actualiza el servicio solicitado en la cita.
                appointment.add_ons = data["add_ons"]
                # Actualiza los complementos de la cita.
                appointment.date = date
                # Actualiza la fecha de la cita.
                appointment.time = time
                # Actualiza la hora de la cita.
                appointment.save()
                # Guarda los cambios en la base de datos.

                return HttpResponse(status=200)
                # Devuelve una respuesta vacía con el código de estado 200, que indica que la operación fue exitosa.

            else:
                return JsonResponse({'error': 'Time slot taken'}, status=400)
                # Si ya existe una cita en la misma fecha y hora, devuelve un error 400 (solicitud incorrecta).

        # Si el método de la solicitud es GET, se desea obtener los detalles de la cita.
        else:
            return JsonResponse(appointment.serialize())
            # Devuelve los detalles de la cita en formato JSON usando el método `serialize` del modelo `Appointment`.

    else:
        return JsonResponse({'error': 'This is not your appointment'}, status=403)
        # Si el usuario que realiza la solicitud no es el propietario de la cita, devuelve un error 403 (prohibido).




@login_required(login_url='/login')
# Decora la vista para asegurar que solo los usuarios autenticados puedan acceder a ella.
def schedule(request, start, move):
    today = datetime.today().date()
    # Obtiene la fecha actual del sistema.

    if move == 'next':
        # Si el parámetro `move` es 'next', quiere avanzar una semana.
        if (start + timedelta(days=7) - today).days / 7 >= 5:
            # Verifica si la nueva fecha está más allá de 5 semanas desde hoy.
            return JsonResponse({"message": "La vista previa y la reserva solo están disponibles para fechas dentro de 5 semanas."}, status=400)
            # Si está fuera de las 5 semanas, devuelve un error con un mensaje.
        else:
            start = start + timedelta(days=7)
            # Si la fecha es válida, suma 7 días a la fecha de inicio.
            slot_dict = load_preview_dict(start)
            # Carga un diccionario con los slots disponibles a partir de la nueva fecha.
            return JsonResponse({"slot_dict": slot_dict}, status=200)
            # Devuelve los slots disponibles como una respuesta JSON.

    elif move == 'prev':
        # Si el parámetro `move` es 'prev', quiere retroceder una semana.
        if start <= today:
            # Si la fecha de inicio es hoy o en el pasado, no se puede mostrar.
            return JsonResponse({"message": "No se puede ver una fecha pasada."}, status=400)
            # Devuelve un error si se intenta retroceder a una fecha pasada.
        else:
            start = start - timedelta(days=7)
            # Si es válido, resta 7 días a la fecha de inicio.
            slot_dict = load_preview_dict(start)
            # Carga los slots disponibles a partir de la nueva fecha.
            return JsonResponse({"slot_dict": slot_dict}, status=200)
            # Devuelve los slots disponibles como una respuesta JSON.

    else:
        return JsonResponse({"message": "Solicitud inválida"}, status=400)
        # Si el parámetro `move` no es ni 'next' ni 'prev', devuelve un error indicando solicitud inválida.


    

@csrf_exempt
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({"message": "Notification marked as read.", "reload": True}, status=200)
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Notification not found."}, status=404)









