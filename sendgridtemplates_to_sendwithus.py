import requests
import pprint
import re
import json
import os.path

class TemplateInfo(object):
    sendgrid_id = 0
    template_name = ""
    version_name = ""
    html_content = ""
    plain_content = ""
    subject = ""
    is_active = 1
    sendwithus_id = ""
    locale = ""

    # The class "constructor" - It's actually an initializer 
    def __init__(self, sendgrid_id, template_name, version_name, html_content, plain_content, subject, is_active, locale):
        self.sendgrid_id = sendgrid_id
        self.template_name = template_name
        self.version_name = version_name
        self.html_content = html_content
        self.plain_content = plain_content
        self.subject = subject
        self.is_active = is_active
        self.locale = locale

def make_templateInfo(sendgrid_id, template_name, version_name, html_content, plain_content, subject, is_active, locale):
    templateInfo = TemplateInfo(sendgrid_id, template_name, version_name, html_content, plain_content, subject, is_active, locale)
    return templateInfo

class SendwithusTemplateRequest(object):
    html = ""
    name = ""
    subject = ""
    text = ""
    locale = ""

    # The class "constructor" - It's actually an initializer 
    def __init__(self, html, name, subject, text, locale):
    	self.html = html
        self.name = name
        self.subject = subject
        self.text = text
        self.locale = locale

def make_sendwithustemplaterequest(html, name, subject, text, locale):
    sendwithusTemplateRequest = SendwithusTemplateRequest(html, name, subject, text, locale)
    return sendwithusTemplateRequest

#The locale is in the Sendgrid template name at the end (e.g. Template Name Example En Us)
#This will get the locale from this name.
def getLocaleFromTemplateName(templateName):
	localeString = templateName[-5:]
	if localeString is not None:
		splitLocale = localeString.replace('_', ' ').split(' ')
		if len(splitLocale) == 2:
			return splitLocale[0].lower() + "-" + splitLocale[1].upper()
		else:
			print "Defaulting locale to english."
	return "en-US"

#Take an entire string and for each word check if it is camel case and split the word up.
#This is to normalize SendGrid template names to Sendwithus
def convertCamelCaseToSpaces(name):
	#localeValue = name[-5:]
	strings = name.split(' ')
	result = ''
	for string in strings:
		val = re.sub('((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', string)
		if result is None or result == '':
			result = val
		else:
			result = result + " " + val

	return result

#Check if the Sendwithus template already exists.  If it does return True
def checkIfTemplateExists(template, sendwithusTemplatesResponse):
	templateName = template.template_name[:-5]
	existingTemplate = [temp for temp in sendwithusTemplatesResponse if temp['name'].strip().lower() == templateName.strip().lower() and temp['locale'] == template.locale]
	if existingTemplate is not None and len(existingTemplate) > 0:
		print "This template already exists. Template: " + templateName + "; Locale: " + template.locale
		return True
	return False

#Get all of the current Sendwithus templates that exist
def getTemplatesFromSendwithus():
	sendwithusTemplatesRequest = requests.get(sendwithus_createTemplateApi, auth=(sendwithus_apikey, ""), timeout=10)
	sendwithusTemplatesResponse = sendwithusTemplatesRequest.json()
	return sendwithusTemplatesResponse

#Get all of the templates from SendGrid to process and send to Sendwithus
def getSendGridTemplates():
	if shouldUseSendGridTemplateFile and os.path.exists(file_sendgrid_templates):
		with open(file_sendgrid_templates) as json_file:
			sendGridTemplates = json.load(json_file)
			print "Finished getting all sendgrid templates from file."
			return sendGridTemplates;

	sendGridTemplatesResponse = requests.get(sendgrid_getTemplatesURL, auth=(sendgrid_username, sendgrid_pw), timeout=10);
	if(sendGridTemplatesResponse.status_code >= 400):
		print("Error getting templates for SendGrid.  StatusCode: " + sendGridTemplatesResponse.status_code)
		return null;
	jsonResponse = sendGridTemplatesResponse.json();
	response = jsonResponse['templates'];
	with open(file_sendgrid_templates, 'w') as json_file:
		json.dump(response, json_file)
	print "Finished getting all sendgrid templates."
	return response;

#Take all of the SendGrid templates and convert SendGrid specific things about the templates to Sendwithus format.
def convertSendGridTemplatesToSendwithusFormat(sendgridJsonTemplates):
	convertedSendGridTemplates = [];
	if shouldUseSendGridConvertedFile and os.path.exists(file_sendgrid_converted):
		print "Getting converted templates from Json file: " + file_sendgrid_converted
		with open(file_sendgrid_converted) as json_file:
			convertedSendGridTemplates = json.load(json_file)
			print "Finished getting all converted sendgrid templates from file."

			result = []
			for template in convertedSendGridTemplates:
				templateInfo = make_templateInfo(template['sendgrid_id'], template['template_name'], template['version_name'], template['html_content'], template['plain_content'], template['subject'], template['is_active'], template['locale']);
				result.append(templateInfo)

			return result;

	amountProcessed = 0
	for template in sendgridJsonTemplates:
		if shouldLimitAmountProcessed and amountProcessed >= 30:
			print "limit for amount to process reached."
			break
		templateId = template['id'];
		print "Processing templateId: " + templateId + ", templateName: " + template['name'];
		try:
			individualTemplateRequest = requests.get(sendgrid_getTemplatesURL + "/" + templateId, auth=(sendgrid_username, sendgrid_pw), timeout=10);
		except:
			print "error processiong request"
			continue
		templateJson = individualTemplateRequest.json();
		templateVersion = templateJson['versions']
		if templateVersion is None or len(templateVersion) <= 0:
			print "skipping template"
			continue
		template = templateJson['versions'][0];

		locale = getLocaleFromTemplateName(templateJson['name'])
		print locale

		templateName = convertCamelCaseToSpaces(templateJson['name'].replace('_', ' '))
		templateVersionName = convertCamelCaseToSpaces(template['name'].replace('_', ' '))

		print "Template Name: " + templateName
		print "Version Name: " + templateVersionName
		templateInfo = make_templateInfo(templateJson['id'], templateName, templateVersionName, template['html_content'], template['plain_content'], template['subject'], template['active'], locale);
	
		substitutions = re.findall('-(\S*)-', templateInfo.plain_content);
		subjectSubstitutions = re.findall('-(\S*)-', templateInfo.subject);
		
		subjectReplace = "<%subject%>"
		subjectReplaceWithSpace = "<%subject%> "
		#Remove <%subject%> from subject
		templateInfo.subject = templateInfo.subject.replace(subjectReplaceWithSpace, "").replace(subjectReplace, "")

		bodyReplace = "<%body%>"
		bodyReplaceHtml = "<p><%body%></p>"
		#Remove <%subject%> from subject
		templateInfo.html_content = templateInfo.html_content.replace(bodyReplaceHtml, "")
		templateInfo.plain_content = templateInfo.plain_content.replace(bodyReplace, "")

		for substitution in subjectSubstitutions:
			valueToBeReplaced = "-" + substitution + "-"
			updatedValue = "{{ " + substitution + " }}"
			templateInfo.subject = templateInfo.subject.replace(valueToBeReplaced, updatedValue)

		for substitution in substitutions:
			valueToBeReplaced = "-" + substitution + "-"
			updatedValue = "{{ " + substitution + " }}"
			templateInfo.plain_content = templateInfo.plain_content.replace(valueToBeReplaced, updatedValue)
			templateInfo.html_content = templateInfo.html_content.replace(valueToBeReplaced, updatedValue)
		
		amountProcessed = amountProcessed + 1
		convertedSendGridTemplates.append(templateInfo);

	templateCount = len(convertedSendGridTemplates)
	currentCount = 1
	file = open(file_sendgrid_converted, 'w')
	file.write("[")
	for convertedTemplate in convertedSendGridTemplates :
		if(currentCount == templateCount):
			file.write(json.dumps(convertedTemplate.__dict__) + '\n')
		else:
			file.write(json.dumps(convertedTemplate.__dict__) + ',\n')
		currentCount = currentCount + 1
	file.write("]")

	print "Finished getting all converted sendgrid templates."
	return convertedSendGridTemplates;

#We want to create the english version of the templates first as this will then be set as the 'default' template in Sendwithus.  
#We will then get the id of this template to create the locale versions.
def createEnglishTemplates(listOfTemplates):
	updatedListOfTemplates = []
	englishTemplates = [template for template in listOfTemplates if template.locale == "en-US"]

	for template in englishTemplates:
		sendwithusTemplatesResponse = getTemplatesFromSendwithus()

		if checkIfTemplateExists(template, sendwithusTemplatesResponse):
			continue

		sendwithusRequestData = make_sendwithustemplaterequest(template.html_content, template.template_name[:-5].strip(), template.subject, template.plain_content, template.locale)
		json_data = json.dumps(sendwithusRequestData.__dict__)
		createTemplateRequest = requests.post(sendwithus_createTemplateApi, auth=(sendwithus_apikey, ""), data=json_data, timeout=10);
		print createTemplateRequest.status_code

		if createTemplateRequest.status_code >= 400:
			print "error creating template in sendwithus.  statusCode: " + str(createTemplateRequest.status_code) + "; templateId: " + template.sendgrid_id + "; templateName: " + template.template_name
			print createTemplateRequest.text
			continue
		createTemplateResponse = createTemplateRequest.json();
		template.sendwithus_id = createTemplateResponse['id']
		updatedListOfTemplates.append(template);

	print "Finished creating English version of the email templates.  AmountCreated: " + str(len(updatedListOfTemplates))
	return updatedListOfTemplates;

#Create a locale version of a template based upon the english version of the template
def createLocaleVersionsForTemplate(listOfTemplates, updatedListOfTemplates):
	updatedListOfTemplates = []
	sendwithusTemplatesResponse = getTemplatesFromSendwithus()
	nonEnglishTemplates = [template for template in listOfTemplates if template.locale != "en-US"]

	print "Non english templates to create locale version for count: " + str(len(nonEnglishTemplates))
	for template in nonEnglishTemplates:
		if checkIfTemplateExists(template, sendwithusTemplatesResponse):
			continue
		templateName = template.template_name[:-5]
		print "template name: " + templateName

		sendwithus_templateIds = [temp for temp in sendwithusTemplatesResponse if temp['name'].strip().lower() == templateName.strip().lower()]
		if sendwithus_templateIds is not None and len(sendwithus_templateIds) > 0:
			print "Attempting to create locale template.  Locale: " + template.locale
			sendwithus_template = sendwithus_templateIds[0]
			template.sendwithus_id = sendwithus_template['id']
			sendwithusRequestData = make_sendwithustemplaterequest(template.html_content.replace("\t", "").replace("\r", "").replace("\n", ""), template.version_name, template.subject, template.plain_content, template.locale)
			json_data = json.dumps(sendwithusRequestData.__dict__)
			createLocaleTemplateUrl = sendwithus_createTemplateApi + "/" + template.sendwithus_id + "/locales"
			print createLocaleTemplateUrl
			createTemplateRequest = requests.post(createLocaleTemplateUrl, auth=(sendwithus_apikey, ""), data=json_data, timeout=10);
			if createTemplateRequest.status_code >= 400:
				print "error creating template in sendwithus.  statusCode: " + str(createTemplateRequest.status_code) + "; templateId: " + template.sendgrid_id + "; templateName: " + template.template_name
				print createTemplateRequest.text
				continue
			else:
				print "Locale template created!"
				updatedListOfTemplates.append(template)
		else:
			print "Couldn't find a matching English version of template. Template: " + templateName + ";  Locale: " + template.locale
			continue
	return updatedListOfTemplates

#Create liquibase changescript to update existint sendgrid id to new sendwithus id.
#liquibase is a database migration tool
def createChangeScript(listOfTemplates):
	file = open(file_sendwithus_update_script, 'w')
	if listOfTemplates is None or len(listOfTemplates) <= 0:
		print "No templates to create changescript for."
		return
	for template in listOfTemplates:
		val = '<changeSet author="tommy.harke" id="update_emailtemplate_' + template.sendgrid_id + '_TO_' + template.sendwithus_id + '">\n'
		val += '	<update tableName="email_template">\n'
		val += '        <column name="template_id" value="' + template.sendwithus_id + '" />\n'
		val += '        <where>template_id = ' + template.sendgrid_id + '</where>\n'
		val += '	</update>\n'
		val += '</changeSet>\n\n'
		file.write(val)
	print "Finished creating change script."


def main():
	sendGridTemplates = getSendGridTemplates();
	sendGridTemplatesInSendwithusFormat = convertSendGridTemplatesToSendwithusFormat(sendGridTemplates);
	createdEnglishSendwithusTemplates = createEnglishTemplates(sendGridTemplatesInSendwithusFormat)
	createdLocaleSendwithusTemplates = createLocaleVersionsForTemplate(sendGridTemplatesInSendwithusFormat, createEnglishTemplates)
	createdSendwithusTemplates = createdEnglishSendwithusTemplates + createdLocaleSendwithusTemplates
	createChangeScript(createdSendwithusTemplates);

sendgrid_username = "{SENDGRID_USERNAME}";
sendgrid_pw = "{SENDGRID_PASSWORD}";
sendgrid_getTemplatesURL = "https://api.sendgrid.com/v3/templates"
sendwithus_createTemplateApi = "https://api.sendwithus.com/api/v1/templates"
sendwithus_apikey = "{SENDWITHUS_APIKEY}"

file_sendgrid_templates = "sendgrid_templates.json"
file_sendgrid_converted = "sendgrid_templates_converted_sendwithus.json"
file_sendwithus_update_script = "update_email_templates_with_sendwithus_ids.txt"

#determine if we should make the call to sendgrid to get the templates, or use a local json file.
shouldUseSendGridTemplateFile = False
#determine if we should call SendGrid for each template and get the template info and convert the data to Sendwithus format.
shouldUseSendGridConvertedFile = False
#If you want to debug and only process a few at a time
shouldLimitAmountProcessed = False 

main()


