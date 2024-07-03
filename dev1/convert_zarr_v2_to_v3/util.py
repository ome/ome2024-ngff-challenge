def update_omezarr_attributes(attributes):
    new_attributes = replace_attributes_value(attributes, search_label='version', new_value='0.5-dev1')
    return new_attributes


def replace_attributes_value(values, search_label, new_value):
    if isinstance(values, dict):
        new_values = {}
        for label, value in values.items():
            if isinstance(label, str) and not label.startswith('_'):
                new_values[label] = replace_attributes_value(value, search_label=search_label, new_value=new_value)
            else:
                new_values[label] = value
        if search_label in values:
            new_values[search_label] = new_value
    elif isinstance(values, list):
        new_values = []
        for item in values:
            new_values.append(replace_attributes_value(item, search_label=search_label, new_value=new_value))
    else:
        new_values = values
    return new_values
