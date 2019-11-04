from django.db import models
from django.utils import timezone

# Models to store data. To simplify, I just put related data into corresponding table.
# Patient and doctor are connected with appointment. The reason I did not use foreign key
# was it sometimes cause mistakes and hard to test.
class Patient(models.Model):
	patient_id = models.IntegerField(primary_key=True)
	first_name = models.CharField(max_length=20)
	last_name = models.CharField(max_length=20)
	date_of_birth = models.DateField(null=True)
	gender = models.CharField(max_length=10)
	city = models.CharField(max_length=40,null=True)
	state = models.CharField(max_length=40,null=True)
	address = models.CharField(max_length=40, null=True)
	ssn = models.CharField(max_length=20, null=True)
	cell_phone = models.CharField(max_length=40, null=True)
	email = models.CharField(max_length=20, null=True)


class Doctor(models.Model):
	"""docstring for Doctor"""
	doctor_id = models.IntegerField(primary_key=True)
	first_name = models.CharField(max_length=20)
	last_name = models.CharField(max_length=20)
	specialty = models.CharField(max_length=50)
	cell_phone = models.CharField(max_length=20, null=True)
	email = models.CharField(max_length=20, null=True)


class Appointment(models.Model):
	"""docstring for Appointment"""
	apt_id = models.IntegerField(primary_key=True)
	doctor_id = models.IntegerField()
	patient_id = models.IntegerField()
	scheduled_time = models.DateTimeField()
	duration = models.IntegerField()
	wait_time = models.IntegerField(null=True)
	end_time = models.DateTimeField()
	status = models.CharField(max_length=20, null=True)
	reason = models.CharField(max_length=50, null=True)
	checkin_time = models.DateTimeField(null=True, blank=True)
	receive_time = models.DateTimeField(null=True, blank=True)


# class Checkin(models.Model):
# 	apt_id = models.IntegerField()
# 	patient_id = models.IntegerField()
# 	doctor_id = models.IntegerField()
# 	checkin_time = models.DateTimeField(null=True, blank=True)
# 	receive_time = models.DateTimeField(null=True, blank=True)



# class ExamRoom(models.Model):
# 	exam_room_id = models.IntegerField(primary_key=True)
# 	office_id = models.IntegerField()
# 	name = models.CharField(max_length=20)
#
#