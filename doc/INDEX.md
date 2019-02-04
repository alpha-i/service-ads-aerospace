ADS Description
===============


Configure the company
---------------------

This is an example a company configuration. It's contained in the `configuration` JSONB field on the `company_configuration table`

```json
    {
	"upload_manager": "FlightUploadManager",
	"datasource_interpreter": "FlightDatasourceInterpreter",
	"datasource_class": "alphai_watson.datasource.flight.FlightDataSource",
	"model": {
		"class_name": "alphai_rickandmorty_oracle.detective.RickAndMortyDetective",
		"configuration": {
			"model_configuration": {
				"train_iters": 1
			}
		}
	},
	"transformer": {
		"class_name": "alphai_watson.transformer.fft.FourierTransformer",
		"configuration": {
			"do_local_normalisation": false,
			"do_log_power": false,
			"number_of_sensors": 8,
			"number_of_timesteps": 392,
			"perform_pca": false
		}
	}
}
```


**Upload Manager**
The Upload manager define which class implemented in `app.service.upload` will manage the validation and storage of the uploaded data file.

The FlightUploadManager check the hd5 validity and structure and store it in a defined location


**Datasource**
The `datasource_intepreter` defines the class responsibile to read the data and transform it for being loaded in the datasource

The interpreters are inside the package `app.interpreter.datasource`

The two keys `datasource_class` defines the path of the class which will provide data to the Detective in runtime.

**Model**

Model section purpose is to define the location of the _Detective_ class and the runtime configuration.

`class_name` contains the full path of the Detective
`configuration` contains the input parameter for the Detective constructor.


**Transformer**

The transformer section contains the configuration for the Transformer class to be loaded in runtime

`class_name`: contains the full path of the transformer class

`configuration`: contains the parameter for the class constructor.

### Note
Setting up a training task on the frontend changes the parameter configuration for that training. 

The current implementation of the training task creation is coupled with the `alphai_watson.transformer.fft.FourierTransformer`. 

Improvements of the code will make the training task form fields defined by configuration.


Configure the Datasource Type
----------------------------

The `Datasource Type` is a entity used to define some properties of the data uploaded. Around a DatasourceType the developer can builds interpreters, validator etc.

The properties are stored in the `meta` JSONB fields in the `datasource_configuration` table.

Here's an example in which we define the `sample_rate` of the data and the `number_of_sensor` (which is the number of columns of the dataframe contained in the HDFStore)_

```json
    {
      "sample_rate": 1024,
      "number_of_sensors": 8
    }
```
### Note

Datasource Type can be defined only through the api call.
