import json
from django.shortcuts import redirect
from django.views.generic.base import View
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Avg, Max, Min, Q
from django.utils import timezone
from django.template import Template, Context
from django.core.exceptions import ObjectDoesNotExist
from social_django.models import UserSocialAuth

import datetime

from drchrono.endpoints import DoctorEndpoint, PatientEndpoint, AppointmentEndpoint, ExamRoomEndpoint
from . import models

def get_token():
    oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
    return oauth_provider.extra_data['access_token']

class SetupView(TemplateView):
    """
    The beginning of the OAuth sign-in flow. Logs a user into the kiosk, and saves the token.
    """
    template_name = 'kiosk_setup.html'

class KioskView(TemplateView):
    template_name = 'kiosk.html'
    """
    Website: /kiosk/ . Get appointments from api and save them into appointment table
    """
    def get_context_data(self, **kwargs):
        token=get_token()
        #kwargs = super(DoctorWelcome, self).get_context_data(**kwargs)

        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        self.apt_db_save(get_token())
        doctor_details = DoctorEndpoint(token)
        kwargs['doctor'] = doctor_details
        return kwargs

    def apt_db_save(self,token):
        apt_api = AppointmentEndpoint(token)
        # Sometimes, this api cannot return all the appointments from start time to end time.
        for p in apt_api.list(start='2019-11-2', end='2019-11-10'):
            p_start_time = datetime.datetime.strptime(p[u'scheduled_time'], '%Y-%m-%dT%H:%M:%S')
            p_end_time = p_start_time + datetime.timedelta(minutes=int(p[u'duration']))
            appointment = models.Appointment(apt_id=p[u'id'], doctor_id=p[u'doctor'], patient_id=p[u'patient'], \
                                             scheduled_time=p[u'scheduled_time'], duration=p[u'duration'], end_time=p_end_time,\
                                             status=p[u'status'], reason=p[u'reason'])
            appointment.save()
        return


class DoctorSetup(TemplateView):

    template_name = 'doctor_setup.html'


class DoctorWelcome(TemplateView):
    """
    Get patients and doctor info from api and save to realted tables. The doctor can choose from kiosk mode and doctor mode
    """
    template_name = 'doctor_welcome.html'

    def get_token(self):
        """
        Social Auth module is configured to store our access tokens. This dark magic will fetch it for us if we've
        already signed in.
        """
        oauth_provider = UserSocialAuth.objects.get(provider='drchrono')
        access_token = oauth_provider.extra_data['access_token']
        return access_token

    def make_api_request(self):
        """
        Use the token we have stored in the DB to make an API request and get doctor details. If this succeeds, we've
        proved that the OAuth setup is working
        """
        # We can create an instance of an endpoint resource class, and use it to fetch details
        access_token = self.get_token()
        self.patient_db_save(access_token)
        self.doc_db_save(access_token)

        api = DoctorEndpoint(access_token)
        # Grab the first doctor from the list; normally this would be the whole practice group, but your hackathon
        # account probably only has one doctor in it.
        return next(api.list())

    def get_context_data(self, **kwargs):
        kwargs = super(DoctorWelcome, self).get_context_data(**kwargs)

        # Hit the API using one of the endpoints just to prove that we can
        # If this works, then your oAuth setup is working correctly.
        #self.apt_db_save(self.get_token())
        doctor_details = self.make_api_request()
        kwargs['doctor'] = doctor_details
        return kwargs

    def patient_db_save(self, token):
        """
        Save patients info to patient table
        """

        patient_api = PatientEndpoint(token)

        for p in patient_api.list():
            patient = models.Patient(patient_id=p[u'id'], first_name=p[u'first_name'], last_name=p[u'last_name'], \
                                     date_of_birth=p[u'date_of_birth'], gender=p[u'gender'], address=p[u'address'], \
                                     ssn=p[u'social_security_number'], cell_phone=p[u'cell_phone'], email=p[u'email'], \
                                     city=p[u'city'], state=p[u'state'])
            patient.save()
        return

    def doc_db_save(self,token):
        """
        Save doctor info to doctor table
        """
        doc_api = DoctorEndpoint(token)
        for p in doc_api.list():
            doctor = models.Doctor(doctor_id=p[u'id'], first_name=p[u'first_name'], last_name=p[u'last_name'], \
                                   specialty=p[u'specialty'], cell_phone=p[u'cell_phone'], email=p[u'email'])
            doctor.save()
        return





class PatientCheckin(TemplateView):
    """
    Patients choose if they have appointments or not
    """
    template_name= 'patient_checkin.html'



class NewAppointment(TemplateView):

    template_name= 'checkin_without_appointment.html'


class DoctorCalendar(TemplateView):
    """
    Doctor can see his appointments here
    """
    template_name = 'doctor_calendar.html'

    def get(self, request):
        ret = dict()
        token = get_token()
        apt_all = models.Appointment.objects.all()
        ret['apt_all'] = apt_all

        received_apt_all = models.Appointment.objects.filter(wait_time__isnull=False)
        if len(received_apt_all) == 0:
            ret['avg_time'] = 0
        else:
            total_wait_time = 0
            for apt in received_apt_all:
                total_wait_time += apt.wait_time
            ret['avg_time'] = total_wait_time / len(received_apt_all)

        return render(request, 'doctor_calendar.html', ret)

    def post(self, request):
        res = dict()
        apt_id = request.POST['apt_id']
        appointment = models.Appointment.objects.get(apt_id=apt_id)
        appointment.status = request.POST['status']
        appointment.receive_time = timezone.now()

        wait_seconds = appointment.receive_time - appointment.checkin_time
        wait_time  =wait_seconds.seconds / 60
        appointment.wait_time = wait_time
        appointment.save()

        received_apt_all = models.Appointment.objects.filter(wait_time__isnull=False)
        if len(received_apt_all) == 0:
            res['result'] = 0
        else:
            total_wait_time = 0
            for apt in received_apt_all:
                total_wait_time += apt.wait_time
            res['result'] = total_wait_time / len(received_apt_all)

        return HttpResponse(json.dumps(res), content_type='application/json')


class AptEventView(View):
    """
    floating window above the calandar
    """
    def get(self, request):
        ret = dict()
        if 'id' in request.GET and request.GET['id']:
            apt_id = request.GET['id']
            appointment = models.Appointment.objects.get(apt_id=apt_id)
            patient = models.Patient.objects.get(patient_id=appointment.patient_id)
            ret['apt'] = appointment
            ret['patient'] = patient
            return render(request, 'appointment_event.html', ret)


def check_in(request):
    """
    After patient input appointment id, they will get response. If it is not valid, they will be warned
    """
    if request.GET.has_key("goback"):
        return render(request, 'doctor_welcome.html', {})

    elif request.GET.has_key("next"):
        #patient_id = request.GET['patient_id']
        apt_id = request.GET['apt_id']
        validStatus = {"","Confirmed"}
        checkInStatus = {"Arrived","Checked In","In Room","In Session"}

        try:
            appointment = models.Appointment.objects.get(apt_id=apt_id)
            now = datetime.datetime.now()
            if appointment.scheduled_time.date() != now.date():
                return HttpResponse('Appointment is not today, please come later or reschedule')
            if appointment.status in checkInStatus:
                return HttpResponse("Your appointment is in process, please wait")
            if appointment.status not in validStatus:
                return HttpResponse("Your appointment is not valid")
            patient_id = appointment.patient_id
            patient = models.Patient.objects.get(patient_id=patient_id)

        except ObjectDoesNotExist:
            return HttpResponse('Appointment does not exist, please input again!')
        #appointment.status = "Checked In"
        #appointment.save()
        return render(request, 'patient_identity.html', {'patient':patient, 'apt':appointment})

def confirm_information(request):
    """
    Patients need to confirm their demographics, they can goback, modify and confirm their info.
    """
    patient_id = request.GET['patient_id']
    apt_id = request.GET['apt_id']
    try:
        patient = models.Patient.objects.get(patient_id=patient_id)
        try:
            appointment = models.Appointment.objects.get(apt_id=apt_id)
            if appointment.patient_id != patient.patient_id:
                return HttpResponse('Patient does not have this appointment, please input again!')
        except ObjectDoesNotExist:
            return HttpResponse('appointment does not exist')
    except ObjectDoesNotExist:
        return HttpResponse('Patient ID is invalid, please input again!')

    if request.GET.has_key("goback"):
        return render(request, 'patient_checkin.html', {})
    elif request.GET.has_key("confirm"):
        appointment.status = "Arrived"
        appointment.checkin_time = timezone.now()
        appointment.save()

        return render(request, 'kiosk.html', {'patient':patient, 'apt':appointment})
    elif request.GET.has_key("reschedule"):
        apt_all = models.Appointment.objects.all()
        return render(request, 'doctor_calendar.html', {'apt_all': apt_all})
    elif request.GET.has_key("update"):
        flag = "update_information"
        return render(request, 'update_patient_information.html', {'patient':patient, 'apt':appointment, 'flag':flag})


def post_patientInfo(token, data, id):
    """
    This is a helper function that once patient update their info, it can post update data to Patient API.
    """
    patient_api = PatientEndpoint(token)
    try:
        response=patient_api.update(id,data)
    except:
        return HttpResponse('Please make sure your info is input correctly')


def update_information(request):
    """
    Once a patient click submit, it will update patient info through patient API, and then store the patient info in patient table
    """
    if request.GET.has_key('goback'):
        return render(request, 'patient_identity.html', {'patient':patient, 'apt':appointment})

    patient_id = request.GET['patient_id']
    apt_id = request.GET['apt_id']

    first_name = request.GET['firstname']
    last_name = request.GET['lastname']
    date_of_birth = datetime.datetime.strptime(request.GET['date_of_birth'],'%Y-%m-%d')
    gender = request.GET['gender']
    address = request.GET['address']
    city = request.GET['city']
    state = request.GET['state']
    ssn = request.GET['ssn']
    cell_phone = request.GET['cell_phone']
    email = request.GET['email']


    if request.GET.has_key('submit'):
        data = {
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': date_of_birth,
            'gender': gender,
            'address': address,
            'city': city,
            'state': state,
            'ssn': ssn,
            'cell_phone': cell_phone,
            'email': email,
        }
        token = get_token()
        post_patientInfo(token, data, patient_id)

        if request.GET['flag'] == "make_appointment":
            max_patient_id = models.Patient.objects.all().aggregate(Max('patient_id'))['patient_id__max']
            patient_id = max_patient_id + 1
            patient = models.Patient(patient_id=patient_id, first_name=first_name, last_name=last_name, \
                                     date_of_birth=date_of_birth, gender=gender, address=address, \
                                     ssn=ssn, cell_phone=cell_phone, email=email, city=city, state=state)
            patient.save()
            return render(request, 'checkin_without_appointment.html', {'patient':patient})

        elif request.GET['flag'] == "update_information":
            try:
                patient = models.Patient.objects.get(patient_id=patient_id)
                try:
                    appointment = models.Appointment.objects.get(apt_id=apt_id)
                    if appointment.patient_id != patient.patient_id:
                        return HttpResponse('Patient does not have this appointment, please input again!')
                except ObjectDoesNotExist:
                    return HttpResponse('appointment does not exist')

            except ObjectDoesNotExist:
                return HttpResponse('Patient ID is invalid, please input again!')

            patient.first_name = first_name
            patient.last_name = last_name
            patient.date_of_birth = date_of_birth
            patient.gender = gender
            patient.address = address
            patient.city = city
            patient.state = state
            patient.ssn = ssn
            patient.cell_phone = cell_phone
            patient.email = email
            patient.save()
            return render(request, 'patient_identity.html', {'patient':patient, 'apt':appointment})


def make_appointment(request):
    """
    This function allow users to make new appointment, due to time limits, it will be implemented soon
    """
    if request.GET.has_key('goback'):
        return render(request, 'doctor_welcome.html', {})
    elif request.GET.has_key('next'):
        doctors = models.Doctor.objects.all()
        return render(request, 'search_doctor.html', {'doctors':doctors})
    elif request.GET.has_key('register'):
        flag = "make_appointment"
        return render(request, 'update_patient_information.html', {'flag':flag})




