from jsonschema import validate,ValidationError


def remove_descriptions(data, max_length=None):
    """
    Recursively remove description fields from JSON schema.
    If max_length is set, remove only descriptions longer than max_length.
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():


            if key == "description":
                if max_length is None:  
                    continue
                elif isinstance(value, str) and len(value) > max_length:
                    continue  

            new_dict[key] = remove_descriptions(value, max_length)
        return new_dict

    elif isinstance(data, list):
        return [remove_descriptions(item, max_length) for item in data]

    return data


def validate_arguments(inputs_args, schema):
    try:
        validate(instance=inputs_args, schema=schema)
        print(f"---------Valid Arguments---------")
        return "Valid"
    except ValidationError as e:
        print(f"---------Invalid Arguments-------")
        return f"Invalid as {e}"