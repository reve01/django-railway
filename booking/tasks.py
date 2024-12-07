from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from .models import Appointment, Notification

@shared_task
def send_appointment_reminders():
    try:
        today = now().date()

        # Filtra las citas que aún no han pasado
        appointments = Appointment.objects.filter(date__gte=today)

        for appointment in appointments:
            # Calcula el número de días restantes hasta la cita
            days_until_appointment = (appointment.date - today).days

            # Enviar recordatorio solo si la cita es dentro de 7 días
            if 1 <= days_until_appointment <= 7:
                # Verifica si ya se ha enviado un recordatorio ese día
                if not Notification.objects.filter(appointment=appointment, is_read=False).exists():
                    Notification.objects.create(
                        user=appointment.user.user,
                        message=(
                            f"Recordatorio: Tienes una cita para {appointment.dog.name} "
                            f"el {appointment.date} a las {appointment.get_time_display()}."
                        ),
                        appointment=appointment
                    )
                    print(f"Notificación creada para cita ID: {appointment.id}")
                else:
                    print(f"Ya se envió un recordatorio para la cita ID: {appointment.id} en este rango.")
            else:
                print(f"No se enviará recordatorio hoy para la cita ID: {appointment.id}.")
    except Exception as e:
        print(f"Error en la tarea: {e}")


