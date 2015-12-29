from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.api.mail import InvalidEmailError

import webapp2_extras.appengine.auth.models
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError

from Utilities import *

 
class User(webapp2_extras.appengine.auth.models.User):

	#sets the password for the current user to the given raw_password
	#def set_password(self, newRawPassword):
		#self.password = security.generate_password_hash(newRawPassword, length=12)

	#returns a user object based on a user ID and token.
	#used for resetting passwords
	"""
	@classmethod
	def get_by_auth_token(cls, user_id, token, subject='auth'):
	"""
	"""
	:param user_id:
		The user_id of the requesting user.
	:param token:
		The token string to be verified.
	:returns:
		A tuple ``(User, timestamp)``, with a user object and
		the token timestamp, or ``(None, None)`` if both were not found.
	"""	"""
	token_key = cls.token_model.get_key(user_id, subject, token)
	user_key = ndb.Key(cls, user_id)
	# Use get_multi() to save a RPC call.
	valid_token, user = ndb.get_multi([token_key, user_key])
	if valid_token and user:
		timestamp = int(time.mktime(valid_token.created.timetuple()))
		return user, timestamp

	return None, None
	"""

	@classmethod
	def sendVerificationEmail(cls, emailAddress, userId = -1):
		#sanity check
		if (emailAddress == "" or "@" not in emailAddress or "." not in emailAddress):
			return false

		userOb = None
		#gets user object for authId and returns false if user doesn't exist in database
		if (userId == -1):
			userOb = cls.get_by_auth_id("own:" + emailAddress)
			if not userOb:
				return False
			userId = userOb.get_id();
		else:
			userOb = cls.get_by_id(userId)

		#create a token that will be used to verify emails
		signupToken = cls.create_signup_token(userId)

		try:
			mailSender = "Caf Buddy <noreply@cafbuddy.appspotmail.com>"
			mailTo = userOb.firstName + " " + userOb.lastName + " <" + emailAddress + ">"
			mailSubject = "Welcome To Caf Buddy - Verify Your Account"
			mailBody = "Dear " + userOb.firstName + ",\n\n Welcome to Caf buddy!"
			mailBody += "\n\n We just need to make sure you are part of the St. Olaf community, so you just need to quickly verify your account."
			mailBody += " Click the following link or copy and paste it into your favorite browser and you will be all set to meet tons of new people and never eat alone again."
			mailBody += "\n\n http://cafbuddy.appspot.com/?email=" + emailAddress + "&signupTok=" + signupToken
			mailBody += "\n\n If you did not sign up for Caf buddy or were not expecting this email then you can safely ignore it."
			mail.send_mail(
				sender = mailSender,
				to = mailTo,
				subject = mailSubject,
				body = mailBody
			)
			return True

		except InvalidEmailError:
			return False


	"""
	Creates a user model and returns a tuple
	On Success: [True, AuthToken] -- authtoken should be saved and used for validating the user is logged in later
	On Error: [False, errorNumber] -- error number is as perscribed in the UserApi
	"""
	@classmethod
	def signUp(cls, firstName, lastName, emailAddress, rawPassword):
		#first, clean up the first and last name by capitalizing the first letter of each word
		#and making the rest lowercase
		firstName = cleanUpName(firstName)
		lastName = cleanUpName(lastName)

		#create a new user to put in the database
		#first argument is auth_id - these are unique identifiers that can be used to get the user from the database
		#for people created using our own sign up the auth_id is "own:email_adress"
		#for facebook it might be "facebook:emailaddress", etc.
		#we want the email address to be unique so set that
		#assign all the other properties that we want the user to have after that
		user_data = cls.create_user(
			"own:" + emailAddress,
			unique_properties = ['emailAddress'],
			password_raw = rawPassword,
			emailAddress = emailAddress,
			firstName = firstName,
			lastName = lastName,
			emailVerified = False
		)
		
		#if email is already registered, send back error message
		if not user_data[0]:
			return [False, -2];
		
		#gets user id in order to get the user object
		userId = user_data[1].get_id()
		userOb = cls.get_by_id(userId)

		cls.sendVerificationEmail(emailAddress)
		
		#creates auth token - this, along with an auth_id - is what is used to verify a user
		#is logged in later
		authToken = cls.create_auth_token(userId)
		return [True, authToken]


	"""
	Logs a user in based on their authId and password
	On Sucess: Returns authToken used to validate the log in in future times
	On Failure: Returns appropriate error message
	"""
	@classmethod
	def logIn(cls, emailAddress, rawPassword):
		try:
			#Logs in a user (identified by AuthId) by validating their password
			userOb = cls.get_by_auth_password("own:" + emailAddress, rawPassword)
			
			#generates new auth token to be used in future validations until logged out
			authToken = userOb.create_auth_token(userOb.key.id())
			return [True, authToken]
			
		except (InvalidAuthIdError, InvalidPasswordError):
			return [False, -1]
	
	""" 
	Logs a user out by deleting the authToken associated with its current logged in state from the database 
	Returns false if the user doesn't exist
	Returns true otherwise since if authtoken is invalid and can't be deleted then it wont work for login anyways
	""" 
	@classmethod
	def logOut(cls, emailAddress, authToken):
		#gets user object for authId and returns false if user doesn't exist in database
		userOb = cls.get_by_auth_id("own:" + emailAddress)
		if not userOb:
			return False

		#deletes token from database
		userOb.delete_auth_token(userOb.key.id(), authToken)
		return True
	
	"""
	Determines if a given user exists in the database and is logged in 
	Returns false if the user doesn't exist or the authentication token is bad (user isn't logged in)
	Returns the userKey of the user object if the user is logged in
	"""
	@classmethod     
	def validateLogIn(cls, emailAddress, authToken):    
		#gets user object for authId and returns false if user doesn't exist in database
		userOb = cls.get_by_auth_id("own:" + emailAddress)
		if not userOb:
			return False
		
		#validates authentication token and returns userKey if user is logged in and false if not
		userTokenOb = userOb.validate_token(userOb.key.id(), 'auth', authToken)
		if userTokenOb:
			return userOb.key.urlsafe()
		return False
	



