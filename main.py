import os
import pandas as pd
import json
from collections import defaultdict
import subprocess

def read_excel_files(folder_path):
    """
    指定されたフォルダ内のすべてのExcelファイルを読み込み、データフレームとして統合。
    """
    data = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(folder_path, file_name)
            df = pd.read_excel(file_path)
            data.append(df)
    return pd.concat(data, ignore_index=True)

def parse_nested_key(resource_dict, keys, value):
    """
    再帰的にキーを処理し、辞書やリストの構造を構築する。
    """
    key = keys[0]

    if len(keys) == 1:
        # 最後のキーに値を設定
        if key.isdigit():
            index = int(key)
            if not isinstance(resource_dict, list):
                resource_dict[:] = [{} for _ in range(index + 1)]
            while len(resource_dict) <= index:
                resource_dict.append({})
            resource_dict[index] = value
        else:
            resource_dict[key] = value
        return

    # 中間キーの処理
    if key.isdigit():
        index = int(key)
        if not isinstance(resource_dict, list):
            resource_dict[:] = [{} for _ in range(index + 1)]
        while len(resource_dict) <= index:
            resource_dict.append({})
        parse_nested_key(resource_dict[index], keys[1:], value)
    else:
        if key not in resource_dict or not isinstance(resource_dict[key], (dict, list)):
            resource_dict[key] = [] if keys[1].isdigit() else {}
        parse_nested_key(resource_dict[key], keys[1:], value)

def convert_to_hcl_with_proper_list_formatting(data):
    """
    データフレームをHCL形式に変換。リスト内の辞書をHCL形式で整形。
    """
    resources = defaultdict(dict)

    for _, row in data.iterrows():
        if not row['generate_tfvars_flag']:
            continue

        resource = row['resource']
        argument = row['arguments']
        value = row['value']

        # 型変換
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass

        if resource not in resources:
            resources[resource] = {}

        keys = argument.split('.')
        parse_nested_key(resources[resource], keys, value)

    # HCL形式の出力
    def format_value_as_hcl(value):
        if isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                return "[\n" + ",\n".join(
                    "    {\n" + "\n".join(
                        f"      {k} = {json.dumps(v)}" for k, v in item.items()
                    ) + "\n    }" for item in value
                ) + "\n  ]"
            return json.dumps(value)
        elif isinstance(value, dict):
            return "{\n" + "\n".join(
                f"    {k} = {format_value_as_hcl(v)}" for k, v in value.items()
            ) + "\n  }"
        else:
            return json.dumps(value)

    hcl_output = ""
    for resource, attributes in resources.items():
        hcl_output += f"{resource} = {{\n"
        for key, value in attributes.items():
            hcl_output += f"  {key} = {format_value_as_hcl(value)}\n"
        hcl_output += "}\n\n"
    return hcl_output

def debug_main_with_hcl_formatting(file_path):
    """
    デバッグ用HCL形式整形対応版メイン関数。
    """
    output_folder = './output_tfvars'
    output_file = os.path.join(output_folder, 'output.tfvars')

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # データ読み込み
    data = pd.read_excel(file_path)
    hcl_output = convert_to_hcl_with_proper_list_formatting(data)

    # 出力
    with open(output_file, 'w') as file:
        file.write(hcl_output)

    try:
        subprocess.run(['terraform', 'fmt', output_file], check=True)
        print(f"HCL形式の内容が{output_file}に出力され、フォーマットされました。")
    except subprocess.CalledProcessError as e:
        print(f"terraform fmtの実行中にエラーが発生しました: {e}")

    # 結果の確認
    return output_file

# 実行例
if __name__ == "__main__":
    input_file_path = './parameter/ec2.xlsx'
    output_file = debug_main_with_hcl_formatting(input_file_path)
    print(f"HCLファイルが生成されました: {output_file}")
