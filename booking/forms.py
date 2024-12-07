from django import forms
from .models import Pet, Appointment
from datetime import datetime, timedelta
from .utilities import check_free_time


class PetForm (forms.ModelForm):
    class Meta:
        model = Pet
        fields = ('name','size','date_of_birth','breed')
        widgets = {
            'date_of_birth': forms.DateInput(format=('%Y/%m/%d'), attrs={'type': 'date'}),
        }

    def clean(self):
        if self.cleaned_data["date_of_birth"] is None:
            raise forms.ValidationError("Please input a date")
        elif self.cleaned_data["date_of_birth"] > datetime.today().date():
            raise forms.ValidationError("The date cannot be in the future")
       
        return self.cleaned_data

TIME_CHOICES = [
        (10, "10:00 AM"),
        (13, "2:00 PM"),
        (15, "3:00 PM")
    ]

class AppointmentForm(forms.ModelForm):
    # Define una clase de formulario basada en el modelo `Appointment`.

    class Meta:
        # Especifica los metadatos para el formulario.
        model = Appointment
        # Asocia este formulario al modelo `Appointment`.
        fields = ('dog', 'date', 'time', 'service', 'add_ons')
        # Define los campos que estarán disponibles en el formulario.
        
        widgets = {
            'date': forms.DateInput(format=('%Y/%m/%d'), attrs={'type': 'date'}),
            # Personaliza el widget para el campo `date` con un input tipo "date" y formato específico.
        }

    def clean(self):
        # Método para realizar la validación personalizada del formulario.
        date = self.cleaned_data["date"]
        # Obtiene la fecha de la cita desde los datos limpiados.
        time = self.cleaned_data["time"]
        # Obtiene la hora de la cita desde los datos limpiados.
        today = datetime.today().date()
        # Obtiene la fecha actual del sistema.
        
        # Validación para asegurarse de que la fecha y hora no sean en el pasado.
        if date < today or (date == today and time < datetime.now().hour):
            raise forms.ValidationError("The date or time cannot be in the past")
            # Si la fecha o hora es en el pasado, se lanza un error de validación.

        # Validación para verificar que no se pueda reservar una cita un lunes (día cerrado).
        elif date.weekday() == 7:
            raise forms.ValidationError("Lo sentimos, no trabajamos los domingos")
            # Si el día es lunes (weekday 7), se lanza un error de validación.

        # Validación para asegurarse de que la reserva no sea para una fecha fuera del rango de 5 semanas.
        elif (date - today).days / 7 >= 5:
            raise forms.ValidationError("Appointment booking is only available for dates within 5 weeks.")
            # Si la fecha está a más de 5 semanas en el futuro, se lanza un error de validación.

        # Validación para verificar si ya existe una cita en la misma fecha y hora.
        elif Appointment.objects.filter(date=date, time=time).exists():
            time_slot_list = list(Appointment.objects.filter(
                date=date).values_list('time', flat=True))
            # Obtiene todas las citas para ese día y extrae las horas ya reservadas.

            all_time_slot = [10, 13, 15]
            # Define los posibles horarios disponibles para ese día (10 AM, 1 PM, 3 PM).

            # Si la fecha es hoy, solo se consideran las horas futuras.
            if date == date.today():
                for hour in all_time_slot:
                    if hour < datetime.now().hour:
                        all_time_slot.remove(hour)
                # Elimina de `all_time_slot` las horas pasadas, si la fecha es hoy.

            # Llama a la función `check_free_time` para comprobar si el horario solicitado está disponible.
            available_slot = check_free_time(all_time_slot, time_slot_list)
            # La función `check_free_time` devuelve los horarios disponibles.

            if available_slot:
                # Si hay horarios disponibles, muestra un mensaje con las opciones disponibles.
                raise forms.ValidationError(
                    f"Requested slot is already booked, the following time slot is still available: {', '.join(str(f'{hr}:00') for hr in available_slot)}.")
            else:
                # Si no hay horarios disponibles para esa fecha, muestra un error.
                raise forms.ValidationError(
                    "There are no available slots for the selected date.")
        # Si todo es válido, devuelve los datos limpiados.
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        # Constructor del formulario para modificar etiquetas y otros atributos dinámicamente.
        user = kwargs.pop('username', None)
        # Se extrae el valor de `username` de los argumentos, si existe.

        super(AppointmentForm, self).__init__(*args, **kwargs)
        # Llama al constructor de la clase base `ModelForm`.

        self.fields['dog'].label = "Pet Name"
        # Cambia la etiqueta del campo `dog` a "Pet Name".
        self.fields['time'].label = "Time Slot"
        # Cambia la etiqueta del campo `time` a "Time Slot".
        self.fields['add_ons'].label = "Add-on Services"
        # Cambia la etiqueta del campo `add_ons` a "Add-on Services".

        
