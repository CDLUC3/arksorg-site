# Testing an ARK resolver instance

Testing an ARK resolver instance operation involves verifying the resolver has correct configuration information and exercising the resolver services with requests and verifying the responses are as expected. 

There are basically two types of requests that are issued to the resolver service: 1) resolving an identifier, and 2) retrieving metadata about the identifier.

Resolve requests take the form `https://resolver.service/BASE/PID`, where BASE is the base path to the resolver endpoint on the service with DNS entry "resolver.service", and PID is the requested identifier. The `arks.org` resolver DNS entry is "arks.org" and the base path is empty, so an ARK resolve request would be:

```
https://arks.org/PID
```

Metadata about the identifier can be retrieved from ARK resolvers by adding `?info` to the end of the resolve URL. Services based on the CDLUC3 resolver service also support metadata requests by prepending the resolve request with `.info/`. For example, an identifier metadata request to the `arks.org` resolver would be of the form:

```
https://arks.org/PID?info
```

or

```
https://arks.org/.info/PID
```

The response of the resolver is dependent on the configuration information. The `arks.org` resolver is configured with the information in the NAAN registry, the public view of which is located at: https://cdluc3.github.io/naan_reg_priv/. 


## Test Cases

Test case records are described in JSON of the following structure:

```
{
	"pid":"identifier being evaluated",
	"resolve": {
		"location":"Target presented by a resolve response",
		"status": "http status code from resolve response"
	},
	"info": {
		"scheme": "ark",
		"content": "The content part of the identifier",
		"prefix": "Prefix or NAAN of identifier",
		"value":"Value or remainder of identifier minus prefix/",
		"suffix": "Remaining part of identifier not matching configuration",
		"definition": {
			"uniq": "Key of entry in configuration that matched the identifier"
			"target": "The target URL template",
			"http_code": "Response code to return"
		}
	}
}
```

Values in the `definition` part must match the corresponding entry in the NAAN registry. 

Given the PID `ark:/99166/w6sr6tn8` first locate the NAAN record by looking for the prefix (NAAN) "99166". Note that there are five entries in the registry with that prefix, one NAAN, and four "shoulders" `p3`, `p5`, `p9`, and `w6`. The test identifier uses the shoulder `w6`, and so the configuration for `99166/w6` contains the intended target. When this configuration is loaded in the resolver, a unique key is created that is composed of the scheme, prefix, and shoulder (if present). Thus, the unique configuration key for this NAAN record would be "`ark:99166/w6`".

The full test case for `ark:/99166/w6sr6tn8` is:

```json
{
	"pid":"ark:/99166/w6sr6tn8",
	"resolve": {
		"location":"http://socialarchive.iath.virginia.edu/ark:/99166/w6sr6tn8",
		"status": 303
	},
	"info": {
		"scheme": "ark",
		"content": "99166/w6sr6tn8",
		"prefix": "99166",
		"value":"w6sr6tn8",
		"suffix": "sr6tn8",
		"definition": {
			"uniq": "ark:99166/w6",
			"target": "http://socialarchive.iath.virginia.edu/ark:/${content}",
			"http_code": 303
		}
	}
}
```

To evaluate this test case:

1. Verify "`info.definition.target`" and "`info.definition.http_code`" match the entry in the NAAN registry.
2. Verify the response location header and status code matches the location and status of the test "`resolve`" section.
3. Verify the `?info` response entries match the values in the test "`info`" section.

Additional test cases are provided below:

PID: `ark:/65665/3f9748e2c-affd-44ee-9c14-4eb966e2955c`

This NAAN ultimately resolves to the Smithsonian Institute, however an intermediate resolver operated by EZID is the registered target for this NAAN.

```json
{
	"pid":"ark:/65665/3f9748e2c-affd-44ee-9c14-4eb966e2955c",
	"resolve": {
		"url":"https://ezid.cdlib.org/ark:/65665/3f9748e2caffd44ee9c144eb966e2955c",
		"status": 302
	},
	"info": {
		"scheme": "ark",
		"content": "65665/3f9748e2caffd44ee9c144eb966e2955c",
		"prefix": "65665",
		"value":"3f9748e2caffd44ee9c144eb966e2955c",
		"suffix": "3f9748e2caffd44ee9c144eb966e2955c",
		"definition": {
            "uniq": "ark:65665",
			"target": "https://ezid.cdlib.org/ark:/${content}",
			"http_code": 302
		}
	}
}
```


PID: `ark:27023/829db79be004882891dd7b88c2ea6236`

```json
{
	"pid":"ark:27023/829db79be004882891dd7b88c2ea6236",
	"resolve": {
		"url":"https://id.colonialcollections.nl/ark:/27023/829db79be004882891dd7b88c2ea6236",
		"status": 302
	},
	"info": {
		"scheme": "ark",
		"content": "27023/829db79be004882891dd7b88c2ea6236",
		"prefix": "27023",
		"value":"829db79be004882891dd7b88c2ea6236",
		"suffix": "829db79be004882891dd7b88c2ea6236",
		"definition": {
            "uniq": "ark:27023",
			"target": "https://id.colonialcollections.nl/ark:/${content}",
			"http_code": 302
		}
	}
}
```

PID: `ark:67531/metadc3211`

```json
{
	"pid":"ark:67531/metadc3211",
	"resolve": {
		"url":"http://digital.library.unt.edu/ark:/67531/metadc3211",
		"status": 302
	},
	"info": {
		"scheme": "ark",
		"content": "67531/metadc3211",
		"prefix": "67531",
		"value":"metadc3211",
		"suffix": "metadc3211",
		"definition": {
            "uniq": "ark:67531",
			"target": "http://digital.library.unt.edu/ark:/${content}",
			"http_code": 302
		}
	}
}
```

PID: `ark:69774/rgm2020`

This configuration is different from most in that the target URL is constructed from the value portion of the PID, i.e. the string "rgm2020" that follows the `scheme + ":" + prefix + "/"`.

```json
{
	"pid": "ark:69774/rgm2020",
	"resolve": {
		"url":"https://hdlab.space/ark/rgm2020",
		"status": 302
	},
	"info": {
		"scheme": "ark",
		"content": "69774/rgm2020",
		"prefix": "69774",
		"value":"rgm2020",
		"suffix": "rgm2020",
		"definition": {
            "uniq": "ark:69774",
			"target": "https://hdlab.space/ark/${value}",
			"http_code": 302
		}
	}
}
```

PID: `ark:19156/tkt42/03n01`

This configuration is different from most in that the target URL is constructed from the suffix portion of the PID, i.e. the string "/03n01" that follows the `scheme + ":" + prefix + "/" + value`.

```json
{
	"pid": "ark:69774/rgm2020",
	"resolve": {
		"url":"https://vocab.participatory-archives.ch/vocab.participatory-archives.ch/brunner/03n01",
		"status": 302
	},
	"info": {
		"scheme": "ark",
		"content": "19156/tkt42/03n01",
		"prefix": "19156",
		"value":"tkt42/03n01",
		"suffix": "/03n01",
		"definition": {
            "uniq": "ark:19156/tkt42",
			"target": "https://vocab.participatory-archives.ch/vocab.participatory-archives.ch/brunner${suffix}",
			"http_code": 302
		}
	}
}
```