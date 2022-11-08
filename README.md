# aio-apisession

Extends `aiohttp.ClientSession` making common API client development scenarios easier to manage.

## Features

- Support for relative URLs, given an API's base URL
- Middleware support for extending the client's behavior
- Debouncer middleware to make client back off when specific statuses are received
- Throttle middleware to make control request rate of the client
- TokenAuthenticator middleware to make client refresh authentication tokens periodically
