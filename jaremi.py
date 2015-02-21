import sys,os
import re
import json
from xml.dom import minidom

outputFile = open('jaremi.html', 'w')	#todo move output filename to config file

json_data = open('jaremi.json')
config = json.load(json_data)

supportedHttpMethods = ['GET', 'POST', 'PUT', 'DELETE']

def appendHeader():		#move content of that method to template file
	outputFile.write("""<!DOCTYPE html>
		<html lang="en">
		<head>
		<meta charset="UTF-8">
		<title>Test execution report</title>
		<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap.min.css">
		<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap-theme.min.css">
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.2/jquery.min.js"></script>
		<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/js/bootstrap.min.js"></script>
		</head>
		<body>
			<div>
			<table class="table">
	""")

def appendFooter():	#move content of that method to template file
	outputFile.write('</table></div></body></html>')

def appendRow(endpoint):
	print(str(endpoint))
	outputFile.write('<tr class="')
	cssClass = ''
	if endpoint.tested and endpoint.testClassResult != None:
		cssClass = endpoint.testClassResult.getOveralStatus()

	outputFile.write(cssClass + '"><td>' + endpoint.path + '</td><td>' + endpoint.method + '</td><td>' + str(endpoint.getTestClass()) + '</td><td>'  + endpoint.project + '</td></tr>')	


def appendStats(totalEndpoints, testedEndpoints, endpointsByProject, testedEndpointsByProjectCount):
	outputFile.write('<div><ul><li>Total endpoints: ' + str(totalEndpoints) + '<ul>')
	for project in endpointsByProject:
		outputFile.write('<li>'+ project + ':' + str(endpointsByProject[project]) + '</li>')	
	outputFile.write('</ul></li><li>Tested endpoints: ' + str(testedEndpoints) + '</li><ul>')
	for project in endpointsByProject:
		outputFile.write('<li>'+ project + ':' + str(testedEndpointsByProjectCount[project]) + '</li>')	
	outputFile.write('</ul></div>')	

class Endpoint:
	def __init__(self, path, method):
		self.path = path
		self.method = method
		self.tested = None
		self.project = None
		self.testClass = None
		self.testClassResult = None

	def setProject(self, project):
		self.project = project	

	def setTested(self, tested):
		self.tested = tested

	def getTestClass(self):
		if self.testClass == None:
			return ''
		else:
			return self.testClass	

	def __str__(self):
		return 'path: '+self.path+' method: '+self.method+' tested: '+str(self.tested)+' project: '+str(self.project) 	


#pattern = re.compile("((@\\w+)([\[\],.\\w\\s\\d{}():/@\"=<>-]+)public)")	#to jest poprawne
h = "(@\\w+)([\[\],.\\w\\s\\d{}():/@\"=<>-]+)"
pattern = re.compile(h + '?public' )	#pattern for parsing all annotations for single public method

helpPattern = re.compile("@("+'|'.join(supportedHttpMethods)+")")
pathPattern = re.compile("@Path\(\"([/:{},\[\].\\d\\w-]*)\"")
mainPathPattern = re.compile("@Path\(\"([/:{},.\\d\\w-]*)\"")	#path on class level



paths = {}

#parse singlw wndpoint return values of @Path and @GET, @POST etc. annotations, annoatationsGroupMatch contains all annotation for some public method
def parseEndpoint(mainPath, annotationsGroupMatch):
	print('parseEndpoint ' + str(annotationsGroupMatch))
	method = None
	path = None
	for methodMatch in re.finditer(helpPattern, str(annotationsGroupMatch)):
		method = methodMatch.group(1)
		print('METHOD: ' + method)

	for pathMatch in re.finditer(pathPattern, str(annotationsGroupMatch)):
		path = pathMatch.group(1) 
		print('PATH: ' + path)
		if not path.startswith('/'):
			path = '/' + path

	fullPath = mainPath
	if path != None:
		fullPath += path	
	return Endpoint(fullPath, method)	

#return value of class level @Path annoatation
def getClassLevelPathAnnotationValue(data):	
	rootPath = None	
	for classPath in re.finditer(mainPathPattern, data):
		rootPath = classPath.group(1)
		break
	return rootPath		

def parseFile(path, name, projectName):
	rootPath = ''     		
	with open(os.path.join(path, name), 'r') as myfile:
		data = myfile.read().replace('\n',' ')

	mainPath = getClassLevelPathAnnotationValue(data)	
	endpointsForFile = []

	if mainPath != None:	
		for match in re.finditer(pattern, data):
			if any(substring in str(match.groups()) for substring in supportedHttpMethods):
				parsedEndpoint = parseEndpoint(mainPath, match.groups())
				print('PARSED ENDPOINT ' + str(parsedEndpoint))
				parsedEndpoint.setProject(projectName)
				endpointsForFile.append(parsedEndpoint)
	return endpointsForFile			

def getEndpointsForProject(project):
	root = project['path']	
	endpointsForProject = []
	for path, subdirs, files in os.walk(root):
		for name in files:
			if name.endswith('.java'):
				endpointsForProject.extend(parseFile(path, name, project['name']))		
	return endpointsForProject				

#warning all endpoints in all projects must by unique by path and http method
def getEndpointsForProjects():
	endpointsForProjects = []
	endpointsByProject = {}
	for project in config['projectsWithEndpoints']:
		res = getEndpointsForProject(project)
		endpointsForProjects.extend(res)
		endpointsByProject[project['name']] = len(res)
		    		
	return {'endpoints' : endpointsForProjects, 'endpointByProject' : endpointsByProject}

getEndpointsForProjectsResult = getEndpointsForProjects()	
paths = getEndpointsForProjectsResult['endpoints']		     
print(len(paths))

#--------------------------------------------------------------
#Search of @TestedEndpoint annotations and bind test class to specific endpoint
#many endpoints can be bind to same test class by using @TestedEndpoint many times

#testedEndpointPattern = re.compile("@TestedEndpoint\(\\s*path\\s*=\\s*\"([/:{},.\\d\\w-]*)\"\\s*,\\s*method\\s*=\\s*\"(GET|POST|PUT|DELETE)\"")
#pathRegexp = '\\s*path\\s*=\\s*\"([/:{},.\\d\\w-]*)\"\\s*'
#methodRegexp = '\\s*method\\s*=\\s*\"(GET|POST|PUT|DELETE)\"'	
pathRegexp = '\\s*path\\s*=\\s*\"([/:{},.\[\]\\d\\w-]*)\"\\s*'
methodRegexp = '\\s*method\\s*=\\s*\"('+ '|'.join(supportedHttpMethods) +')\"'
tepStr = "@TestedEndpoint\(("+pathRegexp+","+methodRegexp+')|('+methodRegexp+","+pathRegexp+')'
#tepStr = pathRegexp+","+methodRegexp + '|' + methodRegexp+","+pathRegexp
testedEndpointPattern = re.compile(tepStr)
print('################')
testedEndpoints = {}

def getTestedEndpointAnnotationData(testedEndpointMatch):
	if testedEndpointMatch.group(1) == None:
		return (testedEndpointMatch.group(5), testedEndpointMatch.group(6))	
	else:
		return  (testedEndpointMatch.group(3), testedEndpointMatch.group(2))		        				

def parseClassPackage(data):
	packageMatch = re.search('\\s*package\\s+([.\\w\\d]+)\\s*;', data)
	return packageMatch.group(1)	

def parseTestedEndointsAnnotationsFromClass(fileName, data):	
	testedEndpoints = {}	
	for testedEndpointMatch in re.finditer(testedEndpointPattern, data):		        		
		package = parseClassPackage(data)
		t = getTestedEndpointAnnotationData(testedEndpointMatch)  
		testedEndpoints[t] = package + '.' + fileName		
		print(testedEndpointMatch.groups())	
	return testedEndpoints	

def parseTestedEndointsAnnotationsFromProject(root):
	testedEndpoints = {}
	for path, subdirs, files in os.walk(root):
	    for name in files:
	    	if name.endswith('.java'): 		
	        	with open(os.path.join(path, name), 'r') as myfile:
	        		data = myfile.read().replace('\n',' ')
	        		testedEndpoints.update(parseTestedEndointsAnnotationsFromClass(name, data))	
	return testedEndpoints        		



testedEndpoints = {}
for root in config['testProjects']:
	testedEndpoints.update(parseTestedEndointsAnnotationsFromProject(root))
#--------------------------------------	      
#PArse test execution reports and create basic statustucs for test results                          		                                						

FAILED = 'danger'
SUCCESS = 'success'
SKIPPED = 'warning'

class TestCaseResult:
	def __init__(self, name, result):
		self.name = name
		self.result = result


class TestClassResult:
	def __init__(self):
		self.results = {FAILED : 0, SKIPPED : 0, SUCCESS : 0}
		self.overalResult = None

	def update(self, testCaseResult):
		self.results[testCaseResult.result] += 1

	def getOveralStatus(self):
		if self.results[FAILED] > 0:
			return FAILED
		elif self.results[SKIPPED] > 0:
			return SKIPPED
		else:			
			return SUCCESS

def buildTestCaseResult(testCase):
	testCaseClass = testCase.getAttribute("classname")
	testCaseName = testCase.getAttribute("name")
	result = None
	failureNodes = testCase.getElementsByTagName("failure")
	skippedNodes = testCase.getElementsByTagName("skipped")

	if failureNodes:
		result = FAILED
	elif skippedNodes:
		result = SKIPPED
	else:
		result = SUCCESS	

	return TestCaseResult(testCaseName, result)		


def parseTestClassResult(f):
	DOMTree = minidom.parse(f)
	cNodes = DOMTree.childNodes
	testClassResult = {}
		
	for node in cNodes:
		testCases = node.getElementsByTagName('testcase')
		for testCase in testCases:
			testCaseClass = testCase.getAttribute("classname")

			if not testCaseClass in testClassResult:
				testClassResult[testCaseClass] = [buildTestCaseResult(testCase)]
			else:
				testClassResult[testCaseClass].append(buildTestCaseResult(testCase))	
	return testClassResult			


def parseTestClassesResults(testResultDirecory):
	testClasses = {}
	files = os.listdir(testResultDirecory)
	for f in files:
		if f.endswith(".xml"):
			testClasses.update(parseTestClassResult(testResultDirecory  + '/' + f))
	return testClasses		
	
testClasses = parseTestClassesResults(config['testResultDirecory'] )		

print(testClasses)


#---------------------------------------
#a) try to bind test class (found by @TestedEndpoint) to specific endpoint
#b) try to bind test class execution result (by full class name) to specific test class
#it can produce inaccurate results if many endpoints are tested in one test class. If just one test fail all endpoints will be marked as failing

def tryBindTestClassResultToEndpoint(testClasses, endpoint):
	if endpoint.testClass in testClasses:
		testClassResult = TestClassResult()
		for tcr in testClasses[endpoint.testClass]:
			testClassResult.update(tcr)
		endpoint.testClassResult = testClassResult		

def isEndpointTested(testedEndpoints, endpoint):		
	return (endpoint.method, endpoint.path) in testedEndpoints.keys()

def getTestClassForEndpoint(testedEndpoints, endpoint):	
	return os.path.splitext(testedEndpoints[(endpoint.method, endpoint.path)])[0]

testedEndpointsCount = 0
testedEndpointsByProjectCount = {i['name'] : 0 for i in config['projectsWithEndpoints']}
result = []
for endpoint in paths:
	if isEndpointTested(testedEndpoints, endpoint):
		endpoint.setTested(True)	
		endpoint.testClass = getTestClassForEndpoint(testedEndpoints, endpoint)
		testedEndpointsCount += 1
		testedEndpointsByProjectCount[endpoint.project] += 1

		tryBindTestClassResultToEndpoint(testClasses, endpoint)


		print(testedEndpoints[(endpoint.method, endpoint.path)])
	else:
		endpoint.setTested(False)
	result.append(endpoint)


appendHeader()
appendStats(len(result), testedEndpointsCount, getEndpointsForProjectsResult['endpointByProject'], testedEndpointsByProjectCount)
for enddpoint in result:
	appendRow(enddpoint)
appendFooter()	

			        		  		

