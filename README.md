# Bluecloud Datacache
REST APIs for BlueCloud Data Cache

To start with this very simple Proof of Concept:

1. install docker
2. install python
3. install pip
4. clone this repository
5. install rapydo (`sudo pip3 install git+https://github.com/rapydo/do.git@1.0`)
6. initialize the instance (`rapydo init`). This command also create a .projectrc with default options
7. pull docker images (`rapydo pull`)
8. start the stack (`rapydo start`)
9. start the REST service, not automatically started in DEV mode (`rapydo shell backend --default`)

Now you can use any http client (curl, httpie, python requests) to call the endpoints on port 8080

A .projectrc file is created by the rapydo init command and random credentials are configured. You can use it to authenticate your self:

```
# get the random credentials from the .projectrc file
grep AUTH_ .projectrc

# authenticate yourself to get a jwt token:
http POST localhost:8080/auth/login username=yourusername password=yourpassword

# use the token to call the endpoints, for example to request for download urls:
http POST localhost:8080/api/order Authorization:'Bearer eyJ0eXAi.....your...token....nxUGlUfOjA049Tfw'
HTTP/1.0 400 BAD REQUEST
Content-Length: 121
Content-Type: application/json
Date: Tue, 02 Feb 2021 14:06:12 GMT
Server: Werkzeug/1.0.1 Python/3.9.0+
Version: 0.1
_RV: 1.0

{
    "marine_id": [
        "Missing data for required field."
    ],
    "urls": [
        "Missing data for required field."
    ]
}

# Get swagger spec:
http GET localhost:8080/api/specs
```


