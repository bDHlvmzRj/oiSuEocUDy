import os
import pandas as pd


def load_parameters_from_directory(directory):
    resource_collections = {}
    for filename in os.listdir(directory):
        if filename.endswith('.xlsx'):
            file_path = os.path.join(directory, filename)
            excel_data = pd.ExcelFile(file_path)
            for sheet_name in excel_data.sheet_names:
                data = pd.read_excel(file_path, sheet_name=sheet_name)
                resource_key = f"{sheet_name}_list"
                if resource_key not in resource_collections:
                    resource_collections[resource_key] = []
                resource_data = {}
                for _, row in data.iterrows():
                    resource = row['resource']
                    argument = row['arguments']
                    value = row['value']

                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass

                    keys = argument.split('.')
                    current = resource_data.setdefault(resource, {})
                    for key in keys[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    current[keys[-1]] = value

                resource_collections[resource_key].append(resource_data)
    return resource_collections

def generate_tfvars_content(resource_collections):
    lines = []
    for collection_name, resources in resource_collections.items():
        lines.append(f"{collection_name} = [")
        for resource_data in resources:
            for resource, arguments in resource_data.items():
                lines.append("  {")
                lines.append(f"    {resource} = {{")
                for key, value in arguments.items():
                    if isinstance(value, dict):
                        lines.append(f"      {key} = {{")
                        for sub_key, sub_value in value.items():
                            lines.append(f"        {sub_key} = \"{sub_value}\"")
                        lines.append("      }")
                    else:  # 単一の引数の場合
                        lines.append(f"      {key} = \"{value}\"")
                lines.append("    }")
                lines.append("  },")
        lines.append("]")
    return "\n".join(lines)

def main():
    parameter_directory = './parameter'
    output_directory = './output_tfvars'

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    resource_collections = load_parameters_from_directory(parameter_directory)
    tfvars_content = generate_tfvars_content(resource_collections)

    output_path = os.path.join(output_directory, 'output.tfvars')
    with open(output_path, 'w') as f:
        f.write(tfvars_content)

    print(f".tfvars file was successfully created: {output_path}")

if __name__ == "__main__":
    main()
