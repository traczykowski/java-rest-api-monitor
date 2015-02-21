# java-rest-api-monitor

This project is a very simple tool for generating some basic report about java rest api projects.

Collected data:
- list of all endpoints (parsed values of @Path annotations),
- http method of endpoint,
- test class for endpoint (script in project with tests search for @TestedEndpoint annotations and tries match them to already parsed endpoints. @TestEndpoint is considered as matched when there is a endpoint with equal path (class + method level @Path) and http method (@GET, @POST etc.) ),
- project name for endpoint,
- information about endpoint test status (parsing xml files with test results, match them with test classes and then they are indirectly connected with endpoints).

## Possible issues
When @TestedEndpoint annotation will be used more than once in a class (test class tests more than one endpoint) then that test class will be connected with more than one endpoints. So if one @TestEndpoint is connected with endpoints A and B then if we found tests result for that class and in reality A is failing but B is ok problem with accuracy will occur. Beacuse in target table both A and B will be marked as not working.


## @TestedEndpoint
You own annotation with two parameters: method and path. Example usage: 
@TestedEndpoint(method = "POST", path = "/exanple/path/{someId}")


