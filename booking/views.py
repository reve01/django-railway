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
    # Mostrar solo comentarios aprobados por el staff y obtener 10 aleatoriamente (si hay más de 10)
    comments = Comment.objects.filter(
        approved=True).order_by('?')[:10]

    # Agregar un nuevo comentario
    if request.method == "POST":
        data = json.loads(request.body)
        comment = data["comment"]
        username = data["username"]
        user = User.objects.get(username=username)

        if user is None:
            return JsonResponse({
                "message": "Inicio de sesión requerido"
            }, status=403)

        Comment.objects.create(user=user, content=comment)
        return JsonResponse({
            "message": "¡Gracias por tu comentario!"
        }, status=200)

    else:
        return render(request, 'booking/inicio.html', {"comments": comments})

# Vista para la página de contacto
def contacto(request):
    return render(request, 'booking/contacto.html')  # Renderiza la plantilla 'contacto.html'

# Vista para la página de servicios
def servicios(request):
    return render(request, 'booking/servicios.html')  # Renderiza la plantilla 'servicios.html'

# Vista para procesar el formulario de contacto (vacío en este caso)
def enviar_contacto(request):
    if request.method == 'POST':  # Si la solicitud es POST, procesar los datos del formulario
        pass  # Aquí iría la lógica para procesar el formulario
    return render(request, 'booking/contacto.html')  # Renderiza de nuevo la plantilla 'contacto.html'

def galeria(request):
    galerias = Galeria.objects.all()
    paginator = Paginator(galerias, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "booking/galeria.html", {"page_obj": page_obj})




def services(request):
    return render(request, 'booking/services.html')


def login_view(request):
    if request.method == "POST":
        next = request.POST['next']
        # Intentar iniciar sesión del usuario
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        
        # Verificar si la autenticación fue exitosa
        if user is not None:
            login(request, user)
            if next == "":
                return HttpResponseRedirect(reverse('profile'))
            else:
                return HttpResponseRedirect(next)

        else:
            messages.error(request, "Nombre de usuario y/o contraseña inválidos.")
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
        # Asegurarse de que las contraseñas coincidan
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            messages.error(request, "Las contraseñas no coinciden.")
            return HttpResponseRedirect(reverse("register"))
            
        elif first_name == "" or last_name == "":
            messages.error(request, "Por favor, completa tu nombre.")
            return HttpResponseRedirect(reverse("register"))
        
        elif password == "":
            messages.error(request, "Por favor, ingresa una contraseña.")
            return HttpResponseRedirect(reverse("register"))

        elif len(password) < 6:
            messages.error(
                request, "La contraseña debe contener al menos 6 caracteres.")
            return HttpResponseRedirect(reverse("register"))

        if phone and (len(phone) != 11 or not phone.isnumeric()):
            messages.error(
                request, "Número de teléfono inválido. Debe tener 11 dígitos y estar en el formato: 9051234567")
            return HttpResponseRedirect(reverse("register"))

        # Intentar crear un nuevo usuario
        try:
            user = User.objects.create_user(username, email, password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            Owner.objects.create(user=user, phone=phone)

        except IntegrityError:
            messages.error(
                request, "El nombre de usuario ya está en uso.")
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
                return JsonResponse({"message": "El número de teléfono debe tener 10 dígitos y solo números."}, status=400)
        elif field == 'email':
            if '@' in value:
                user = User.objects.get(username=request.user)
                user.email = value
                user.save()
                return HttpResponse(status=204)
            else:
                return JsonResponse({"message": "Por favor, introduce un correo electrónico válido."}, status=400)

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
                request, 'La contraseña debe contener al menos 6 caracteres.')
            return HttpResponseRedirect(reverse('changepassword'))
        elif new_password != confirmation:
            messages.error(
                request, 'La nueva contraseña y la confirmación no coinciden.')
            return HttpResponseRedirect(reverse('changepassword'))

        elif old_password == new_password:
            messages.error(
                request, 'La contraseña antigua y la nueva no pueden ser iguales.')
            return HttpResponseRedirect(reverse('changepassword'))

        if old_password and new_password and (new_password == confirmation) and (old_password != new_password):
            if user_record.check_password(old_password):
                user_record.set_password(new_password)
                user_record.save()
                messages.success(request, 'La contraseña se ha actualizado, por favor inicia sesión con tu nueva contraseña.')
                return HttpResponseRedirect(reverse('login'))
            else:
                messages.error(
                    request, 'La contraseña antigua es incorrecta.')
                return HttpResponseRedirect(reverse('changepassword'))

    else:
        return render(request, 'booking/changepassword.html')



@login_required(login_url='/login')
def booking(request):
    # Obtener notificaciones no leídas
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    
    # Vista previa de la tabla de horarios
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
            slot_dict[date] = 'Cerrado'
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

    # Los usuarios solo pueden elegir las mascotas que poseen
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
                    "notifications": notifications,
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

                messages.success(request, f"{name} se añadió correctamente.")
                # Muestra un mensaje de éxito informando que la mascota se ha añadido correctamente.

                return render(request, 'booking/booking.html', {
                    "form": bookform,
                    "petform": PetForm(),
                    "date_list": slot_dict,
                    "notifications": notifications,
                })
                # Renderiza la plantilla de reservas después de agregar la mascota.

            else:
                return render(request, "booking/booking.html", {
                    "form": bookform,
                    "petform": petform,
                    "date_list": slot_dict,
                    "notifications": notifications,
                })
                # Renderiza la plantilla con el formulario de citas, el formulario de mascotas y las fechas disponibles, pero con errores en el formulario de mascota.

    else:  # Si la solicitud es un GET (cuando se carga la página inicialmente)
        return render(request, 'booking/booking.html', {
            "form": bookform,
            "petform": PetForm(),
            "date_list": slot_dict,
            "notifications": notifications,
        })
        # Renderiza la plantilla de reservas con los formularios de cita y mascota vacíos y las fechas disponibles.





# Asegura que solo los usuarios autenticados puedan acceder a la vista. Redirige al usuario no autenticado a la página de inicio de sesión.
@login_required(login_url='/login')  
def appointment(request, id):
    try:
        # Intenta obtener la cita con el ID proporcionado.
        appointment = Appointment.objects.get(pk=id)
    except Appointment.DoesNotExist:
        # Si la cita no existe, devuelve un error 404 con un mensaje.
        return JsonResponse({"error": "Registro no encontrado."}, status=404)

    # Obtiene el objeto Owner relacionado con el usuario autenticado.
    owner = Owner.objects.get(user=request.user)

    # Comprueba si el usuario actual es el propietario de la cita.
    if owner.id == appointment.user.id:
        if request.method == "DELETE":  # Comprueba si la solicitud es un intento de eliminar la cita.
            if owner.id == appointment.user.id:  # Verifica nuevamente la autorización.
                # Convierte el cuerpo de la solicitud en un objeto JSON.
                data = json.loads(request.body)  
                id = data["id"]
                # Elimina la cita de la base de datos.
                appointment.delete()
                # Devuelve un código de estado 204 para indicar que la operación fue exitosa pero sin contenido.
                return HttpResponse(status=204)
            else:
                # Devuelve un error si el usuario no tiene permiso para eliminar la cita.
                return JsonResponse({'error': 'Solo puedes eliminar tus propias citas'}, status=403)

        elif request.method == 'PUT':  # Comprueba si la solicitud es para actualizar la cita.
            # Convierte el cuerpo de la solicitud en un objeto JSON.
            data = json.loads(request.body)  
            # Convierte la fecha recibida en una fecha válida.
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            # Obtiene la hora de la solicitud.
            time = data["time"]
            # Obtiene el ID del perro relacionado con la cita.
            dog = data["dog"]

            # Comprueba si la fecha y hora son en el pasado.
            if date < datetime.today().date() or (date == datetime.today().date() and time < str(datetime.now().hour)):
                return JsonResponse({'error': 'No se puede cambiar a un horario pasado'}, status=400)

            # Comprueba si el día es lunes (cerrado).
            elif date.weekday() == 0:
                return JsonResponse({'error': 'Lo sentimos, estamos cerrados los lunes'}, status=400)

            # Comprueba si ya existe una cita para la misma fecha y hora.
            available = Appointment.objects.filter(
                date=date, time=time).exclude(id=id)

            if available.count() == 0:  # Si no hay conflictos de horario, se procede a actualizar la cita.
                appointment.dog = Pet.objects.get(pk=dog)  # Asigna el nuevo perro a la cita.
                appointment.service = data["service"]  # Actualiza el servicio de la cita.
                appointment.add_ons = data["add_ons"]  # Actualiza los complementos.
                appointment.date = date  # Actualiza la fecha.
                appointment.time = time  # Actualiza la hora.
                appointment.save()  # Guarda los cambios en la base de datos.
                # Devuelve un código de estado 200 para indicar que la operación fue exitosa.
                return HttpResponse(status=200)
            else:
                # Devuelve un error si el horario ya está ocupado.
                return JsonResponse({'error': 'Horario ya ocupado'}, status=400)

        else:
            # Si la solicitud no es DELETE ni PUT, devuelve los detalles de la cita.
            return JsonResponse(appointment.serialize())
    else:
        # Si el usuario no es el propietario de la cita, devuelve un error.
        return JsonResponse({'error': 'Esta no es tu cita'}, status=403)



# Asegura que solo los usuarios autenticados puedan acceder a la vista.
@login_required(login_url='/login')
def schedule(request, start, move):
    today = datetime.today().date()  # Obtiene la fecha de hoy.

    if move == 'next':  # Si el usuario intenta avanzar una semana.
        if (start + timedelta(days=7) - today).days / 7 >= 5:
            # Si la fecha está más allá de 5 semanas, devuelve un error.
            return JsonResponse({"message": "La vista previa y la reserva solo están disponibles para fechas dentro de 5 semanas."}, status=400)
        else:
            # Avanza la fecha en 7 días.
            start = start + timedelta(days=7)
            # Carga los horarios disponibles.
            slot_dict = load_preview_dict(start)
            # Devuelve los horarios en formato JSON.
            return JsonResponse({"slot_dict": slot_dict}, status=200)

    elif move == 'prev':  # Si el usuario intenta retroceder una semana.
        if start <= today:
            # No se permite ver fechas pasadas.
            return JsonResponse({"message": "No se puede ver una fecha pasada."}, status=400)
        else:
            # Retrocede la fecha en 7 días.
            start = start - timedelta(days=7)
            # Carga los horarios disponibles.
            slot_dict = load_preview_dict(start)
            # Devuelve los horarios en formato JSON.
            return JsonResponse({"slot_dict": slot_dict}, status=200)

    else:
        # Si la solicitud no es válida, devuelve un error.
        return JsonResponse({"message": "Solicitud inválida"}, status=400)


# Permite marcar una notificación como leída. No requiere autenticación CSRF.
@csrf_exempt
def mark_notification_read(request, notification_id):
    try:
        # Intenta obtener la notificación relacionada con el usuario.
        notification = Notification.objects.get(id=notification_id, user=request.user)
        # Marca la notificación como leída.
        notification.is_read = True
        # Guarda los cambios en la base de datos.
        notification.save()
        # Devuelve una respuesta exitosa.
        return JsonResponse({"message": "Notificación marcada como leída.", "reload": True}, status=200)
    except Notification.DoesNotExist:
        # Devuelve un error si no se encuentra la notificación.
        return JsonResponse({"error": "Notificación no encontrada."}, status=404)










